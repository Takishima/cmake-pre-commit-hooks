# Copyright 2023 Damien Nguyen <ngn.damien@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import contextlib
import platform
from textwrap import dedent

import pytest
from _test_utils import ExitError

from cmake_pc_hooks import _argparse

# ==============================================================================


def _add_simple_args(parser):
    parser.add_argument('--flag', action='store_true')
    parser.add_argument('--no-flag', action='store_false')
    parser.add_argument('--int', type=int)
    parser.add_argument('--string', type=str)


# ------------------------------------------------------------------------------


@pytest.fixture()
def simple_toml_content():
    return dedent(
        '''
        flag = false
        no_flag = true
        int = 1
        string = 'one'

        [tool.my-name]
        flag = true
        no_flag = false
        int = 2
        string = 'two'
        '''
    )


# ------------------------------------------------------------------------------


@pytest.fixture(scope='module')
def parser():
    parser = _argparse.ArgumentParser()
    _add_simple_args(parser)
    parser.add_argument('-f', '--files', type=str, action='append')
    parser.add_argument('--extra', type=str)
    parser.add_argument('--default', type=str, default='default')
    parser.add_argument('--non-overridable', type=str, default='no')

    tmp, _ = super(_argparse.ArgumentParser, parser).parse_known_args([])
    parser._default_args = vars(tmp)
    return parser


@pytest.fixture(params=[(False, ''), (True, ''), (True, 'tool.section.my-section')], ids=lambda x: f'{x[0]}-"{x[1]}"')
def toml_generate(tmp_path, request):
    with_content, toml_section = request.param
    path = tmp_path / 'config.toml'
    ref_values = {}

    if with_content:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not toml_section:
            ref_values = {
                'flag': True,
                'no_flag': False,
                'string': 'one',
                'int': 1,
                'files': ['1.txt', '2.txt'],
                'non_overridable': 'none',
            }
        else:
            ref_values = {
                'flag': True,
                'no_flag': False,
                'string': 'three',
                'int': 3,
                'files': ['100.txt', '200.txt'],
                'non_overridable': 'none',
            }
        content = dedent(
            '''
            flag = true
            no_flag = false
            string = 'one'
            int = 1
            files = ['1.txt', '2.txt']
            non_overridable = 'none'

            [tool.my-section]
            flag = true
            no_flag = false
            string = 'two'
            int = 2
            files = ['10.txt', '20.txt']
            non_overridable = 'none'

            [tool.section.my-section]
            flag = true
            no_flag = false
            string = 'three'
            int = 3
            files = ['100.txt', '200.txt']
            non_overridable = 'none'
        '''
        )
        path.write_text(content)

    return path, with_content, toml_section, ref_values


# ==============================================================================


@pytest.mark.parametrize(('field_name', 'field_value'), [('one', 1), ('string', 'Hello')])
def test_append_in_namespace(field_name, field_value):
    namespace = argparse.Namespace()

    assert not hasattr(namespace, field_name)

    _argparse._append_in_namespace(namespace, field_name, field_value)
    assert hasattr(namespace, field_name)
    assert getattr(namespace, field_name) == [field_value]

    _argparse._append_in_namespace(namespace, field_name, field_value)
    assert getattr(namespace, field_name) == [field_value, field_value]


def test_executable_path(tmp_path):
    executable = tmp_path / 'my-exec'
    executable.write_text('')
    executable.chmod(755)

    a_file = tmp_path / 'file.txt'
    a_file.write_text('')
    assert a_file.is_file()

    assert _argparse.executable_path(executable) == executable

    with pytest.raises(argparse.ArgumentTypeError):
        _argparse.executable_path(tmp_path)

    if platform.system() != 'Windows':
        with pytest.raises(argparse.ArgumentTypeError):
            _argparse.executable_path(a_file)


# ==============================================================================


def test_argument_parser_init():
    parser = _argparse.ArgumentParser()

    assert parser._default_config_name is None
    assert parser._pyproject_section_name is None
    assert parser._default_args == {}

    args = parser.parse_args([])
    assert hasattr(args, 'config')


def test_argument_parser_load_from_toml_unknown_key(mocker, toml_generate):
    def exit_raise(status):
        raise RuntimeError(f'{status}')

    mocker.patch('sys.exit', exit_raise)
    path, with_content, toml_section, _ = toml_generate

    if not with_content:
        return

    parser = _argparse.ArgumentParser()
    parser._default_args = {'config': ''}
    namespace = argparse.Namespace()

    with pytest.raises(RuntimeError, match='2'):
        parser._load_from_toml(namespace=namespace, path=path, section=toml_section)


def test_argument_parser_load_from_toml_invalid(toml_generate):
    path, with_content, toml_section, _ = toml_generate

    if not with_content:
        return

    content = dedent(
        '''
        other = 'one'
    '''
    )
    if toml_section:
        content += dedent(
            f'''
            [{toml_section}]
            other = 'ten'
        '''
        )
    path.write_text(content)

    parser = _argparse.ArgumentParser()
    parser.add_argument('--other', type=str)
    parser._default_args = {'config': '', 'other': 0}
    namespace = argparse.Namespace()

    with pytest.raises(KeyError):
        parser._load_from_toml(namespace=namespace, path=path, section='aaa')

    with pytest.raises(argparse.ArgumentTypeError):
        parser._load_from_toml(namespace=namespace, path=path, section=toml_section)


def test_argument_parser_load_from_toml(parser, toml_generate):
    path, with_content, toml_section, ref_values = toml_generate
    namespace = argparse.Namespace()

    if not with_content:
        with pytest.raises(FileNotFoundError):
            parser._load_from_toml(namespace=namespace, path=path)
        parser._load_from_toml(namespace=namespace, path=path, path_must_exist=False)
        return

    parser._load_from_toml(namespace=namespace, path=path, section=toml_section)

    assert not hasattr(namespace, 'extra')
    assert not hasattr(namespace, 'default')  # NB: not present in file => not set

    for attr_name, ref_value in ref_values.items():
        attr_type = type(ref_value)
        assert hasattr(namespace, attr_name)
        attr_value = getattr(namespace, attr_name)
        assert isinstance(attr_value, attr_type)
        assert attr_value == ref_value


def test_argument_parser_load_from_toml_overrides(parser, toml_generate):
    path, with_content, toml_section, ref_values = toml_generate
    namespace = argparse.Namespace()

    if not with_content:
        return

    overridable_keys = set(parser._default_args)
    overridable_keys.remove('non_overridable')

    parser._load_from_toml(namespace=namespace, path=path, section=toml_section, overridable_keys=overridable_keys)

    assert not hasattr(namespace, 'extra')
    assert not hasattr(namespace, 'default')  # NB: not present in file => not set

    del ref_values['non_overridable']
    assert not hasattr(namespace, 'non_overridable')

    for attr_name, ref_value in ref_values.items():
        attr_type = type(ref_value)
        assert hasattr(namespace, attr_name)
        attr_value = getattr(namespace, attr_name)
        assert isinstance(attr_value, attr_type)
        assert attr_value == ref_value


# ==============================================================================


def test_argument_parser_pyproject_toml_missing_section(tmp_path, monkeypatch):
    parser = _argparse.ArgumentParser(pyproject_section_name='tool.my-name')
    _add_simple_args(parser)

    pyproject_file = tmp_path / 'pyproject.toml'
    pyproject_file.parent.mkdir(parents=True, exist_ok=True)
    pyproject_file.write_text(
        dedent(
            '''
            flag = true
            int = 1
            string = 'one'
            '''
        )
    )

    monkeypatch.chdir(str(tmp_path))
    known_args, args = parser.parse_known_args([])

    assert not args
    assert not known_args.flag
    assert known_args.int is None
    assert known_args.string is None


def test_argument_parser_pyproject_toml(tmp_path, monkeypatch, simple_toml_content):
    parser = _argparse.ArgumentParser(pyproject_section_name='tool.my-name')
    _add_simple_args(parser)

    pyproject_file = tmp_path / 'pyproject.toml'
    pyproject_file.parent.mkdir(parents=True, exist_ok=True)
    pyproject_file.write_text(simple_toml_content)

    monkeypatch.chdir(str(tmp_path))
    known_args, args = parser.parse_known_args([])

    assert not args
    assert known_args.flag
    assert known_args.int == 2
    assert known_args.string == 'two'


def test_argument_parser_default_config_file(tmp_path, monkeypatch, simple_toml_content):
    default_config_name = 'default_config.toml'

    parser = _argparse.ArgumentParser(default_config_name=default_config_name)
    _add_simple_args(parser)

    default_config_file = tmp_path / default_config_name
    default_config_file.parent.mkdir(parents=True, exist_ok=True)
    default_config_file.write_text(simple_toml_content)

    monkeypatch.chdir(str(tmp_path))
    namespace = argparse.Namespace()
    namespace.sentinel = None
    known_args, args = parser.parse_known_args(args=[], namespace=namespace)

    assert not args
    assert hasattr(known_args, 'sentinel')
    assert not known_args.flag
    assert known_args.int == 1
    assert known_args.string == 'one'


def test_argument_parser_config_file(tmp_path, simple_toml_content):
    default_config_name = 'myconfig.toml'

    parser = _argparse.ArgumentParser()
    _add_simple_args(parser)

    config_file = tmp_path / default_config_name
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(simple_toml_content)

    known_args, args = parser.parse_known_args([f'--config={config_file}', '--flag', '--string=aaa'])

    assert not args
    assert known_args.flag
    assert known_args.int == 1
    assert known_args.string == 'aaa'


# ==============================================================================


def test_argument_parser_dump_toml(mocker):
    toml_dumps = mocker.patch('toml.dumps')
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)

    # ----------------------------------

    parser = _argparse.ArgumentParser()
    _add_simple_args(parser)

    with contextlib.suppress(ExitError):
        parser.parse_known_args(['--flag', '--string=aaa', '--int', '10', '--dump-toml', 'file.txt'])

    sys_exit.assert_called_once_with(0)

    toml_dumps.assert_called_once()
    toml_dict = toml_dumps.call_args.args[0]
    assert 'dump_toml' not in toml_dict
    assert toml_dict['flag']
    assert toml_dict['int'] == 10
    assert toml_dict['string'] == 'aaa'


# ==============================================================================
