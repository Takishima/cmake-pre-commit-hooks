#   Copyright 2023 Damien Nguyen <ngn.damien@gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from cmake_pc_hooks import _config, clang_format, clang_tidy, cppcheck, cpplint, include_what_you_use, lizard
from cmake_pc_hooks._hook import HOOK_NAMES

import pytest

OPTION_TYPES = {'build_dir': list, 'all_at_once': bool, 'generator': str}

# ==============================================================================


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def load(hook_name='clang-tidy', config_file=None):
    return _config.load_settings(hook_name, config_file, OPTION_TYPES)


# ==============================================================================


def test_hook_names_match_the_hooks():
    modules = (clang_format, clang_tidy, cppcheck, cpplint, include_what_you_use, lizard)
    assert tuple(module.HOOK.name for module in modules) == HOOK_NAMES


def test_load_settings_without_any_file(project):
    assert load() == {}


@pytest.mark.parametrize(
    ('filename', 'header'),
    [('pyproject.toml', '[tool.cmake_pc_hooks]\n'), ('cmake_pc_hooks.toml', '')],
)
def test_load_settings_from_default_files(project, filename, header):
    (project / filename).write_text(f'{header}build_dir = ["build"]\nall_at_once = true\n', encoding='utf-8')

    assert load() == {'build_dir': ['build'], 'all_at_once': True}


@pytest.mark.parametrize('content', ['', '[tool.other]\nkey = 1\n', '[project]\nname = "test"\n'])
def test_load_settings_pyproject_without_our_section(project, content):
    (project / 'pyproject.toml').write_text(content, encoding='utf-8')

    assert load() == {}


def test_load_settings_precedence(project):
    (project / 'pyproject.toml').write_text(
        '[tool.cmake_pc_hooks]\nbuild_dir = ["pyproject"]\ngenerator = "pyproject"\nall_at_once = true\n',
        encoding='utf-8',
    )
    (project / 'cmake_pc_hooks.toml').write_text('build_dir = ["default"]\ngenerator = "default"\n', encoding='utf-8')
    (project / 'custom.toml').write_text('build_dir = ["custom"]\n', encoding='utf-8')

    assert load() == {'build_dir': ['default'], 'generator': 'default', 'all_at_once': True}
    assert load(config_file='custom.toml') == {'build_dir': ['custom'], 'generator': 'default', 'all_at_once': True}


def test_load_settings_missing_config_file(project):
    with pytest.raises(_config.ConfigError, match=r'Unable to locate TOML file missing\.toml'):
        load(config_file='missing.toml')


def test_load_settings_invalid_toml(project):
    (project / 'cmake_pc_hooks.toml').write_text('build_dir = [', encoding='utf-8')

    with pytest.raises(_config.ConfigError, match=r'cmake_pc_hooks\.toml is not a valid TOML file'):
        load()


# ==============================================================================


@pytest.mark.parametrize(
    ('filename', 'prefix'),
    [('pyproject.toml', 'tool.cmake_pc_hooks.'), ('cmake_pc_hooks.toml', '')],
)
def test_load_settings_hook_table_overrides_common_settings(project, filename, prefix):
    common = '[tool.cmake_pc_hooks]\n' if prefix else ''
    (project / filename).write_text(
        f'{common}build_dir = ["common"]\ngenerator = "Ninja"\n'
        f'[{prefix}clang-tidy]\nbuild_dir = ["tidy"]\nall_at_once = true\n'
        f'[{prefix}cppcheck]\nbuild_dir = ["cppcheck"]\n',
        encoding='utf-8',
    )

    assert load('clang-tidy') == {'build_dir': ['tidy'], 'generator': 'Ninja', 'all_at_once': True}
    assert load('cppcheck') == {'build_dir': ['cppcheck'], 'generator': 'Ninja'}
    assert load('lizard') == {'build_dir': ['common'], 'generator': 'Ninja'}


def test_load_settings_common_settings_of_later_file_override_hook_table(project):
    (project / 'pyproject.toml').write_text(
        '[tool.cmake_pc_hooks.clang-tidy]\nbuild_dir = ["pyproject"]\n', encoding='utf-8'
    )
    (project / 'cmake_pc_hooks.toml').write_text('build_dir = ["default"]\n', encoding='utf-8')

    assert load('clang-tidy') == {'build_dir': ['default']}


@pytest.mark.parametrize(
    ('content', 'message'),
    [
        ('not_an_option = true\n', 'unknown option "not_an_option" in cmake_pc_hooks.toml'),
        ('[other]\nbuild_dir = ["build"]\n', 'unknown option "other" in cmake_pc_hooks.toml'),
        (
            '[cppcheck]\nnot_an_option = true\n',
            'unknown option "not_an_option" in table "cppcheck" of cmake_pc_hooks.toml',
        ),
        ('lizard = true\n', '"lizard" in cmake_pc_hooks.toml must be a table'),
        ('build_dir = "build"\n', 'option "build_dir" in cmake_pc_hooks.toml must be of type list'),
        ('all_at_once = "yes"\n', 'option "all_at_once" in cmake_pc_hooks.toml must be of type bool'),
        (
            '[cppcheck]\ngenerator = ["Ninja"]\n',
            'option "generator" in table "cppcheck" of cmake_pc_hooks.toml must be of type str',
        ),
    ],
    ids=['unknown', 'unknown_table', 'unknown_in_table', 'not_a_table', 'not_a_list', 'not_a_bool', 'not_a_str'],
)
def test_load_settings_invalid_settings(project, content, message):
    (project / 'cmake_pc_hooks.toml').write_text(content, encoding='utf-8')

    with pytest.raises(_config.ConfigError) as excinfo:
        load('clang-tidy')
    assert str(excinfo.value) == message


# ==============================================================================


def test_dump_toml(tmp_path):
    settings = {
        'all_at_once': True,
        'clean': False,
        'generator': 'Unix "Makefiles"',
        'source_dir': tmp_path,
        'build_dir': ('one', 'two'),
        'defines': [],
    }

    output = _config.dump_toml(settings)

    assert output.splitlines()[:3] == ['all_at_once = true', 'clean = false', 'generator = "Unix \\"Makefiles\\""']
    assert output.splitlines()[4:] == ['build_dir = ["one", "two"]', 'defines = []']
    assert _config.tomllib.loads(output) == {**settings, 'source_dir': str(tmp_path), 'build_dir': ['one', 'two']}
    assert not _config.dump_toml({})


# ==============================================================================
