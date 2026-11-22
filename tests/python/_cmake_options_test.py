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

import argparse
from pathlib import Path

from cmake_pc_hooks._cmake import CMakeOptions, add_cmake_arguments_to_parser

import pytest

# ==============================================================================


@pytest.fixture(scope='module')
def parser():
    parser = argparse.ArgumentParser()
    add_cmake_arguments_to_parser(parser)
    return parser


# ==============================================================================


@pytest.mark.parametrize(
    ('args', 'opt_name', 'opt_value'),
    [
        ([], 'automatic_discovery', True),
        (['--no-automatic-discovery'], 'automatic_discovery', False),
        (['--detect-configured-files'], 'detect_configured_files', True),
        ([], 'build_targets', []),
        (['--cmake-build-target=one'], 'build_targets', ['one']),
        (['--cmake-build-target=one', '--cmake-build-target', 'two'], 'build_targets', ['one', 'two']),
        ([], 'codegen', False),
        (['--codegen'], 'codegen', True),
        (['--linux="-DCMAKE_CXX_COMPILER=g++"'], 'linux', ['"-DCMAKE_CXX_COMPILER=g++"']),
        (['--mac="-DCMAKE_CXX_COMPILER=clang++"'], 'mac', ['"-DCMAKE_CXX_COMPILER=clang++"']),
        (['--win="-DCMAKE_CXX_COMPILER=cl"'], 'win', ['"-DCMAKE_CXX_COMPILER=cl"']),
        (['-S/path/to/source'], 'source_dir', '/path/to/source'),
        (['-B/path/to/build'], 'build_dir', ['/path/to/build']),
        (['-B/path/to/build', '-B/other'], 'build_dir', ['/path/to/build', '/other']),
        (['-DONE'], 'defines', ['ONE']),
        (['-DONE', '-DTWO'], 'defines', ['ONE', 'TWO']),
        (['-UONE'], 'undefines', ['ONE']),
        (['-UONE', '-UTWO'], 'undefines', ['ONE', 'TWO']),
        (['-GMakefiles'], 'generator', 'Makefiles'),
        (['-Tclang'], 'toolset', 'clang'),
        (['-A64'], 'platform', '64'),
        (['-Werror=dev'], 'errors', 'dev'),
        (['-Wno-error=dev'], 'no_errors', 'dev'),
        (['--preset=/path/to/file.cmake'], 'preset', '/path/to/file.cmake'),
        (['-Wdev'], 'dev_warnings', True),
        (['-Wno-dev'], 'no_dev_warnings', True),
    ],
)
def test_parser(parser, args, opt_name, opt_value):
    assert getattr(parser.parse_args(args), opt_name) == opt_value


def test_parser_unix_applies_to_linux_and_mac(parser):
    known_args = parser.parse_args(['--unix="-DCMAKE_CXX_COMPILER=clang++"'])

    assert known_args.unix == ['"-DCMAKE_CXX_COMPILER=clang++"']
    assert known_args.linux == known_args.unix
    assert known_args.mac == known_args.unix
    assert known_args.win is None


# ==============================================================================


def test_options_defaults(parser):
    assert CMakeOptions.from_namespace(parser.parse_args([])) == CMakeOptions(source_dir=Path())
    assert CMakeOptions() == CMakeOptions(source_dir=Path())


def test_options_from_namespace(parser, tmp_path):
    cmake = tmp_path / 'cmake'
    cmake.write_bytes(b'')
    cmake.chmod(0o755)

    options = CMakeOptions.from_namespace(
        parser.parse_args(
            [
                '-S/path/to/source',
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
        source_dir=Path('/path/to/source'),
        build_dirs=['one', 'two'],
        cmake=cmake,
        no_cmake_configure=True,
        automatic_discovery=False,
        detect_configured_files=True,
        build_targets=['target'],
        codegen=True,
    )


def test_options_cmake_args(parser):
    args = parser.parse_args(
        ['-DONE', '-DTWO=2', '-UTHREE', '-Werror=dev', '-Wno-error=dev', '-GNinja', '-Tclang', '-Ax64']
    )
    args.preset = 'default'
    args.dev_warnings = args.no_dev_warnings = True

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


def test_options_cmake_args_from_toml_lists(parser):
    args = parser.parse_args([])
    args.errors = ['dev']
    args.linux = None

    assert CMakeOptions.from_namespace(args).cmake_args == ['-Werror=dev']


@pytest.mark.parametrize(
    ('system', 'expected'),
    [
        ('Linux', ['-DUNIX=1', '-DLINUX=1']),
        ('Darwin', ['-DUNIX=1', '-DMAC=1']),
        ('Windows', ['-DWIN=1', '-DQUOTED=1']),
        ('Other', []),
    ],
)
def test_options_platform_specific_cmake_args(mocker, parser, system, expected):
    mocker.patch('platform.system', return_value=system)
    args = parser.parse_args(['--unix=-DUNIX=1', '--linux=-DLINUX=1', '--mac=-DMAC=1', '--win=-DWIN=1'])
    args.win.append('"-DQUOTED=1"')

    assert CMakeOptions.from_namespace(args).cmake_args == expected


# ==============================================================================
