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

from pathlib import Path
from types import SimpleNamespace

from cmake_pc_hooks._cmake import CMAKE_OPTIONS, CMakeOptions

import click
import pytest

# ==============================================================================


def parse(args):
    command = click.Command('test', params=CMAKE_OPTIONS)
    return SimpleNamespace(**command.make_context('test', list(args)).params)


# ==============================================================================


@pytest.mark.parametrize(
    ('args', 'opt_name', 'opt_value'),
    [
        ([], 'automatic_discovery', True),
        (['--no-automatic-discovery'], 'automatic_discovery', False),
        ([], 'detect_configured_files', False),
        (['--detect-configured-files'], 'detect_configured_files', True),
        ([], 'build_targets', ()),
        (['--cmake-build-target=one'], 'build_targets', ('one',)),
        (['--cmake-build-target=one', '--cmake-build-target', 'two'], 'build_targets', ('one', 'two')),
        ([], 'codegen', False),
        (['--codegen'], 'codegen', True),
        (['--clean'], 'clean', True),
        (['--no-cmake-configure'], 'no_cmake_configure', True),
        (['--unix="-DCMAKE_CXX_COMPILER=clang++"'], 'unix', ('"-DCMAKE_CXX_COMPILER=clang++"',)),
        (['--linux="-DCMAKE_CXX_COMPILER=g++"'], 'linux', ('"-DCMAKE_CXX_COMPILER=g++"',)),
        (['--mac="-DCMAKE_CXX_COMPILER=clang++"'], 'mac', ('"-DCMAKE_CXX_COMPILER=clang++"',)),
        (['--win="-DCMAKE_CXX_COMPILER=cl"'], 'win', ('"-DCMAKE_CXX_COMPILER=cl"',)),
        ([], 'source_dir', Path()),
        ([], 'build_dir', ()),
        (['-B/path/to/build'], 'build_dir', ('/path/to/build',)),
        (['-B', '/path/to/build', '--build-dir=/other'], 'build_dir', ('/path/to/build', '/other')),
        (['-DONE'], 'defines', ('ONE',)),
        (['-DONE', '-D', 'TWO=2'], 'defines', ('ONE', 'TWO=2')),
        (['-UONE', '-UTWO'], 'undefines', ('ONE', 'TWO')),
        (['-GMakefiles'], 'generator', 'Makefiles'),
        (['-Tclang'], 'toolset', 'clang'),
        (['-A64'], 'platform', '64'),
        (['-Werror=dev'], 'errors', ('dev',)),
        (['-Wno-error=dev'], 'no_errors', ('dev',)),
        (['--preset=/path/to/file.cmake'], 'preset', '/path/to/file.cmake'),
        (['-Wdev'], 'dev_warnings', True),
        (['-Wno-dev'], 'no_dev_warnings', True),
        ([], 'cmake', None),
    ],
)
def test_parser(args, opt_name, opt_value):
    assert getattr(parse(args), opt_name) == opt_value


def test_parser_source_dir_must_be_a_directory(tmp_path):
    file = tmp_path / 'file.txt'
    file.write_bytes(b'')

    assert parse([f'-S{tmp_path}']).source_dir == tmp_path
    with pytest.raises(click.BadParameter, match='is a file'):
        parse([f'-S{file}'])
    with pytest.raises(click.BadParameter, match='does not exist'):
        parse([f'-S{tmp_path / "missing"}'])


def test_parser_cmake_must_be_an_executable_file(tmp_path):
    cmake = tmp_path / 'cmake'
    cmake.write_bytes(b'')

    cmake.chmod(0o644)
    with pytest.raises(click.BadParameter):
        parse([f'--cmake={cmake}'])
    with pytest.raises(click.BadParameter):
        parse([f'--cmake={tmp_path}'])

    cmake.chmod(0o755)
    assert parse([f'--cmake={cmake}']).cmake == cmake


@pytest.mark.parametrize('args', [['-Werror=other'], ['-Wno-error=other']])
def test_parser_invalid_choice(args):
    with pytest.raises(click.BadParameter):
        parse(args)


# ==============================================================================


def test_options_defaults():
    assert CMakeOptions.from_namespace(parse([])) == CMakeOptions(source_dir=Path())
    assert CMakeOptions() == CMakeOptions(source_dir=Path())


def test_options_from_namespace(tmp_path):
    cmake = tmp_path / 'cmake'
    cmake.write_bytes(b'')
    cmake.chmod(0o755)

    options = CMakeOptions.from_namespace(
        parse(
            [
                f'-S{tmp_path}',
                '-Bone',
                '-Btwo',
                f'--cmake={cmake}',
                '--no-cmake-configure',
                '--no-automatic-discovery',
                '--detect-configured-files',
                '--cmake-build-target=target',
                '--codegen',
            ]
        )
    )

    assert options == CMakeOptions(
        source_dir=tmp_path,
        build_dirs=['one', 'two'],
        cmake=cmake,
        no_cmake_configure=True,
        automatic_discovery=False,
        detect_configured_files=True,
        build_targets=['target'],
        codegen=True,
    )


def test_options_cmake_args():
    args = parse(
        [
            '-DONE',
            '-DTWO=2',
            '-UTHREE',
            '-Werror=dev',
            '-Wno-error=dev',
            '-GNinja',
            '-Tclang',
            '-Ax64',
            '--preset=default',
            '-Wdev',
            '-Wno-dev',
        ]
    )

    assert CMakeOptions.from_namespace(args).cmake_args == [
        '-DONE',
        '-DTWO=2',
        '-UTHREE',
        '-Werror=dev',
        '-Wno-error=dev',
        '-GNinja',
        '-Tclang',
        '-Ax64',
        '--preset=default',
        '-Wdev',
        '-Wno-dev',
    ]


@pytest.mark.parametrize(
    ('system', 'expected'),
    [
        ('Linux', ['-DUNIX=1', '-DLINUX=1']),
        ('Darwin', ['-DUNIX=1', '-DMAC=1']),
        ('Windows', ['-DWIN=1', '-DQUOTED=1']),
        ('Other', []),
    ],
)
def test_options_platform_specific_cmake_args(mocker, system, expected):
    mocker.patch('platform.system', return_value=system)
    args = parse(['--unix=-DUNIX=1', '--linux=-DLINUX=1', '--mac=-DMAC=1', '--win=-DWIN=1', '--win="-DQUOTED=1"'])

    assert CMakeOptions.from_namespace(args).cmake_args == expected


# ==============================================================================
