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
import platform
from pathlib import Path

import fasteners
import filelock
import pytest

from cmake_pc_hooks._cmake import CMakeCommand, get_cmake_command

# ==============================================================================

_has_cmake = get_cmake_command() is not None

# ==============================================================================


@pytest.fixture(scope='module')
def parser():
    cmake = CMakeCommand()
    parser = argparse.ArgumentParser()
    cmake.add_cmake_arguments_to_parser(parser)
    return parser


# ==============================================================================


def test_cmake_command_init():
    cmake = CMakeCommand()
    assert cmake.command is None or isinstance(cmake.command, list)
    assert cmake.source_dir is None
    assert cmake.build_dir is None
    assert any('CMAKE_EXPORT_COMPILE_COMMANDS' in arg for arg in cmake.cmake_args)


@pytest.mark.parametrize(
    ('args', 'opt_name', 'opt_value'),
    [
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
        (['--linux="-DCMAKE_CXX_COMPILER=g++"'], 'linux', ['"-DCMAKE_CXX_COMPILER=g++"']),
        (['--mac="-DCMAKE_CXX_COMPILER=clang++"'], 'mac', ['"-DCMAKE_CXX_COMPILER=clang++"']),
        (['--win="-DCMAKE_CXX_COMPILER=cl"'], 'win', ['"-DCMAKE_CXX_COMPILER=cl"']),
    ],
)
def test_cmake_parser_setup(parser, args, opt_name, opt_value):
    known_args, _ = parser.parse_known_args(args)
    assert opt_name in known_args
    assert getattr(known_args, opt_name) == opt_value


def test_cmake_parser_unix_platform_setup(parser):
    unix_flag_value = '"-DCMAKE_CXX_COMPILER=g++-10"'
    known_args, _ = parser.parse_known_args([f'--unix={unix_flag_value}'])

    assert known_args.linux == [unix_flag_value]
    assert known_args.mac == [unix_flag_value]
    assert known_args.win is None


@pytest.mark.parametrize(
    ('dir_list', 'build_dir_tree', 'ref_path'),
    [
        (None, ['build'], CMakeCommand.DEFAULT_BUILD_DIR),
        (None, ['build/CMakeCache.txt'], 'build'),
        (None, ['gcc-build/CMakeCache.txt'], 'gcc-build'),
        (None, ['gcc-build/CMakeCache.txt', 'build/CMakeCache.txt'], 'build'),
        (['clang', 'gcc'], ['gcc-build/compile_commands.json'], 'clang'),
        (['clang'], ['gcc-build/CMakeCache.txt'], 'gcc-build'),
        (['clang'], ['gcc-build/CMakeCache.txt', 'clang/CMakeCache.txt', 'build/CMakeCache.txt'], 'clang'),
    ],
)
def test_resolve_build_directory(tmp_path, dir_list, build_dir_tree, ref_path):
    cmake = CMakeCommand()
    cmake.source_dir = tmp_path

    for path_elem in build_dir_tree:
        path = tmp_path / path_elem
        if path.is_file():
            path.parent.mkdir(parents=True)
            path.write_text('')
        else:
            path.mkdir(parents=True)

    assert cmake.build_dir is None
    cmake.resolve_build_directory(None if dir_list is None else [tmp_path / path for path in dir_list])
    assert cmake.build_dir == tmp_path / ref_path


@pytest.mark.parametrize('system', ['Linux', 'Darwin', 'Windows'])
def test_setup_cmake_args(mocker, system):
    def system_stub():
        return system

    mocker.patch('platform.system', system_stub)

    cmake = CMakeCommand()

    args = argparse.Namespace()
    args.source_dir = Path('/path/to/source')
    args.cmake = Path('/path/to/cmake')
    args.defines = ['ONE', 'TWO']
    args.undefines = ['THREE', 'FOUR']
    args.errors = ['dev']
    args.no_errors = ['dev']
    args.generator = 'Ninja'
    args.toolset = 'clang-toolset'
    args.platform = '64'
    args.dev_warnings = True
    args.no_dev_warnings = True
    args.linux = ['LNX_A', 'LNX_B']
    args.mac = ['MAC_A', 'MAC_B']
    args.win = ['WIN_A', 'WIN_B']

    assert cmake.source_dir is None
    assert cmake.build_dir is None
    cmake.setup_cmake_args(args)

    assert cmake.source_dir == args.source_dir
    assert cmake.command == [args.cmake]
    assert cmake.build_dir is None

    assert '-GNinja' in cmake.cmake_args
    assert '-A64' in cmake.cmake_args
    assert '-Tclang-toolset' in cmake.cmake_args

    assert '-Wdev' in cmake.cmake_args
    assert '-Wno_dev' in cmake.cmake_args

    for define in args.defines:
        assert any(define in arg for arg in cmake.cmake_args)
    for undefine in args.undefines:
        assert any(undefine in arg for arg in cmake.cmake_args)
    for error in args.errors:
        assert any(f'-Werror={error}' in arg for arg in cmake.cmake_args)
    for no_error in args.no_errors:
        assert any(f'-Wno-error={no_error}' in arg for arg in cmake.cmake_args)

    if platform.system() == 'Linux':
        for linux in args.linux:
            assert any(linux in arg for arg in cmake.cmake_args)
    elif platform.system() == 'Darwin':
        for mac in args.mac:
            assert any(mac in arg for arg in cmake.cmake_args)
    elif platform.system() == 'Windows':
        for win in args.win:
            assert any(win in arg for arg in cmake.cmake_args)


@pytest.mark.parametrize('returncode', [0, 1])
@pytest.mark.parametrize('clean_build', [False, True])
def test_configure_cmake(mocker, tmp_path, clean_build, returncode):
    sys_exit = mocker.patch('sys.exit')
    FileLock = mocker.MagicMock(filelock.FileLock)  # noqa: N806
    mocker.patch('filelock.FileLock', FileLock)
    InterProcessReaderWriterLock = mocker.MagicMock(fasteners.InterProcessReaderWriterLock)  # noqa: N806
    mocker.patch('fasteners.InterProcessReaderWriterLock', InterProcessReaderWriterLock)
    _configure = mocker.Mock(return_value=returncode)
    mocker.patch('cmake_pc_hooks._cmake.CMakeCommand._configure', _configure)

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake = CMakeCommand()
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=g++')

    cmake.configure(command='test', clean_build=clean_build)

    # ----------------------------------

    FileLock.assert_called_once_with(build_dir / '_cmake_configure_try_lock')
    InterProcessReaderWriterLock.assert_called_once_with(build_dir / '_cmake_configure_lock')
    _configure.assert_called_once_with(
        lock_files=(InterProcessReaderWriterLock.call_args[0][0], FileLock.call_args[0][0]), clean_build=clean_build
    )
    if returncode != 0:
        sys_exit.assert_called_once_with(returncode)
    else:
        sys_exit.assert_not_called()


@pytest.mark.parametrize('clean_build', [False, True])
def test_configure_cmake_timeout(mocker, tmp_path, clean_build):
    mocker.patch('filelock.Timeout', RuntimeError)

    def timeout(blocking):  # noqa: ARG001
        raise RuntimeError

    args = {'acquire.side_effect': timeout}
    file_lock = mocker.MagicMock(filelock.FileLock, **args)
    FileLock = mocker.MagicMock(filelock.FileLock, return_value=file_lock)  # noqa: N806
    mocker.patch('filelock.FileLock', FileLock)

    interprocess_lock = mocker.MagicMock()
    InterProcessReaderWriterLock = mocker.MagicMock(return_value=interprocess_lock)  # noqa: N806
    mocker.patch('fasteners.InterProcessReaderWriterLock', InterProcessReaderWriterLock)
    _configure = mocker.Mock(return_value=0)
    mocker.patch('cmake_pc_hooks._cmake.CMakeCommand._configure', _configure)

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake = CMakeCommand()
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=g++')

    cmake.configure(command='test', clean_build=clean_build)

    # ----------------------------------

    FileLock.assert_called_once()
    InterProcessReaderWriterLock.assert_called_once()
    interprocess_lock.read_lock.assert_called_once()
    _configure.assert_not_called()


@pytest.mark.parametrize('clean_build', [False, True])
def test_configure_cmake_internal(mocker, tmp_path, clean_build):
    mocker.patch('shutil.rmtree')
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process', return_value=mocker.Mock(stdout='', stderr='', returncode=0)
    )

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    (build_dir / 'CMakeFiles').mkdir()
    (build_dir / 'CMakeCache.txt').write_text('')
    compile_commands = build_dir / 'compile_commands.json'
    compile_commands.write_text('')
    lock_files = [build_dir / '_lock']
    for lock_file in lock_files:
        lock_file.write_text('')

    cmake = CMakeCommand()
    cmake.command = ['cmake']
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=g++')

    returncode = cmake._configure(lock_files=lock_files, clean_build=clean_build)

    # ----------------------------------

    for lock_file in lock_files:
        assert lock_file.exists()

    call_process.assert_called_once_with(
        [*cmake.command, str(cmake.source_dir), *cmake.cmake_args], cwd=str(cmake.build_dir)
    )

    if not clean_build:
        assert compile_commands.exists()
        assert returncode == 0
    else:
        assert not compile_commands.exists()
        assert returncode != 0

    call_process.assert_called_once()
