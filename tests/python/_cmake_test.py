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
from textwrap import dedent

import fasteners
import filelock
import pytest
from _test_utils import ExitError

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


# ------------------------------------------------------------------------------

filelock_module_name = 'filelock.FileLock'
interprocess_rw_lock_module_name = 'fasteners.InterProcessReaderWriterLock'
internal_cmake_configure_name = 'cmake_pc_hooks._cmake.CMakeCommand._configure'


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
        # Custom options
        ([], 'automatic_discovery', True),
        (['--no-automatic-discovery'], 'automatic_discovery', False),
        (['--detect-configured-files'], 'detect_configured_files', True),
        (['--linux="-DCMAKE_CXX_COMPILER=g++"'], 'linux', ['"-DCMAKE_CXX_COMPILER=g++"']),
        (['--mac="-DCMAKE_CXX_COMPILER=clang++"'], 'mac', ['"-DCMAKE_CXX_COMPILER=clang++"']),
        (['--win="-DCMAKE_CXX_COMPILER=cl"'], 'win', ['"-DCMAKE_CXX_COMPILER=cl"']),
        # CMake-like options
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
    cmake.resolve_build_directory(
        None if dir_list is None else [tmp_path / path for path in dir_list], automatic_discovery=True
    )
    assert cmake.build_dir == tmp_path / ref_path

    cmake.build_dir = None
    cmake.resolve_build_directory(
        None if dir_list is None else [tmp_path / path for path in dir_list], automatic_discovery=False
    )
    assert cmake.build_dir == tmp_path / cmake.DEFAULT_BUILD_DIR if dir_list is None else dir_list[0]


@pytest.mark.parametrize('system', ['Linux', 'Darwin', 'Windows'])
def test_setup_cmake_args(mocker, system):  # noqa: PLR0915
    original_system = platform.system()

    def system_stub():
        return system

    mocker.patch('platform.system', system_stub)

    cmake = CMakeCommand()

    args = argparse.Namespace()
    args.detect_configured_files = True
    if original_system == 'Windows':
        args.source_dir = 'C:/path/to/source'
        args.build_dir = ['C:/path/to/build', 'C:/path/to/other_build']
        args.cmake = Path('C:/path/to/cmake')
    else:
        args.source_dir = '/path/to/source'
        args.build_dir = ['/path/to/build', '/path/to/other_build']
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
    args.automatic_discovery = True
    args.linux = ['LNX_A', 'LNX_B']
    args.mac = ['MAC_A', 'MAC_B']
    args.win = ['WIN_A', 'WIN_B']

    assert cmake.source_dir is None
    assert cmake.build_dir is None
    assert not cmake.cmake_trace_log
    cmake.setup_cmake_args(args)

    assert cmake.source_dir == Path(args.source_dir)
    assert cmake.command == [args.cmake]
    assert cmake.build_dir is not None
    assert cmake.cmake_trace_log == cmake.build_dir / cmake.DEFAULT_TRACE_LOG

    assert '-GNinja' in cmake.cmake_args
    assert '-A64' in cmake.cmake_args
    assert '-Tclang-toolset' in cmake.cmake_args

    assert '-Wdev' in cmake.cmake_args
    assert '-Wno_dev' in cmake.cmake_args

    # The arguments are not added to cmake.cmake_args since we only want to add them during a CMake configure call
    assert '--trace-expand' not in cmake.cmake_args
    assert '--trace-format=json-v1' not in cmake.cmake_args

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


@pytest.mark.parametrize('detect_configured_files', [False, True], ids=['no_trace', 'w_trace'])
@pytest.mark.parametrize('returncode', [0, 1])
@pytest.mark.parametrize('clean_build', [False, True])
def test_configure_cmake(mocker, tmp_path, clean_build, returncode, detect_configured_files):
    sys_exit = mocker.patch('sys.exit')
    FileLock = mocker.MagicMock(filelock.FileLock)  # noqa: N806
    mocker.patch(filelock_module_name, FileLock)
    InterProcessReaderWriterLock = mocker.MagicMock(fasteners.InterProcessReaderWriterLock)  # noqa: N806
    mocker.patch(interprocess_rw_lock_module_name, InterProcessReaderWriterLock)
    _configure = mocker.Mock(return_value=returncode)
    mocker.patch(internal_cmake_configure_name, _configure)
    parse_log = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand._parse_cmake_trace_log')

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake = CMakeCommand()
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=g++')
    if detect_configured_files:
        cmake.cmake_trace_log = tmp_path / 'log.json'

    cmake.configure(command='test', clean_build=clean_build)

    # ----------------------------------

    FileLock.assert_called_once_with(build_dir / '_cmake_configure_try_lock')
    InterProcessReaderWriterLock.assert_called_once_with(build_dir / '_cmake_configure_lock')
    _configure.assert_called_once_with(
        lock_files=(InterProcessReaderWriterLock.call_args[0][0], FileLock.call_args[0][0]), clean_build=clean_build
    )

    if detect_configured_files:
        parse_log.assert_called_once_with()
    else:
        parse_log.assert_not_called()

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
    mocker.patch(filelock_module_name, FileLock)

    interprocess_lock = mocker.MagicMock()
    InterProcessReaderWriterLock = mocker.MagicMock(return_value=interprocess_lock)  # noqa: N806
    mocker.patch(interprocess_rw_lock_module_name, InterProcessReaderWriterLock)
    _configure = mocker.Mock(return_value=0)
    mocker.patch(internal_cmake_configure_name, _configure)

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake = CMakeCommand()
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_C_COMPILER=gcc')

    cmake.configure(command='test', clean_build=clean_build)

    # ----------------------------------

    FileLock.assert_called_once()
    InterProcessReaderWriterLock.assert_called_once()
    interprocess_lock.read_lock.assert_called_once()
    _configure.assert_not_called()


def test_configure_invalid(mocker):
    mocker.patch('sys.exit', side_effect=ExitError)

    FileLock = mocker.MagicMock(filelock.FileLock)  # noqa: N806
    mocker.patch(filelock_module_name, FileLock)
    InterProcessReaderWriterLock = mocker.MagicMock(fasteners.InterProcessReaderWriterLock)  # noqa: N806
    mocker.patch(interprocess_rw_lock_module_name, InterProcessReaderWriterLock)
    _configure = mocker.Mock(return_value=1)
    mocker.patch(internal_cmake_configure_name, _configure)

    # ----------------------------------

    cmake = CMakeCommand()
    assert cmake.source_dir is None
    with pytest.raises(ExitError):
        cmake.configure(command='test')


@pytest.mark.parametrize('detect_configured_files', [False, True], ids=['no_trace', 'w_trace'])
@pytest.mark.parametrize('clean_build', [False, True], ids=['no_clean_build', 'clean_build'])
def test_configure_cmake_internal(mocker, tmp_path, clean_build, detect_configured_files):
    mocker.patch('shutil.rmtree')
    call_cmake = mocker.patch(
        'cmake_pc_hooks._cmake.CMakeCommand._call_cmake', return_value=mocker.Mock(stdout='', stderr='', returncode=0)
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
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=clang++')
    if detect_configured_files:
        cmake.cmake_trace_log = tmp_path / 'log.json'

    returncode = cmake._configure(lock_files=lock_files, clean_build=clean_build)

    # ----------------------------------

    for lock_file in lock_files:
        assert lock_file.exists()

    if detect_configured_files:
        call_cmake.assert_called_once()
        extra_args = call_cmake.call_args.kwargs['extra_args']
        assert '--trace-expand' in extra_args
        assert '--trace-format=json-v1' in extra_args
        assert f'--trace-redirect={cmake.cmake_trace_log}' in extra_args
    else:
        call_cmake.assert_called_once_with(extra_args=[])

    if not clean_build:
        assert compile_commands.exists()
        assert returncode == 0
    else:
        assert not compile_commands.exists()
        assert returncode != 0


# ==============================================================================


def test_call_cmake(mocker, tmp_path):
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process', return_value=mocker.Mock(stdout='', stderr='', returncode=0)
    )

    # ----------------------------------

    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake = CMakeCommand()
    cmake.command = ['cmake']
    cmake.source_dir = tmp_path
    cmake.build_dir = build_dir
    cmake.cmake_args.append('-DCMAKE_CXX_COMPILER=clang++')

    cmake._call_cmake()
    call_process.assert_called_once_with(
        [*cmake.command, str(cmake.source_dir), *cmake.cmake_args], cwd=str(cmake.build_dir)
    )

    extra_args = ['-N', '-LA']
    cmake._call_cmake(extra_args=extra_args)
    call_process.assert_called_with(
        [*cmake.command, str(cmake.source_dir), *cmake.cmake_args, *extra_args], cwd=str(cmake.build_dir)
    )


# ==============================================================================


@pytest.mark.parametrize('with_cache_variables', [False, True], ids=['w/o_cache_vars', 'w_cache_vars'])
@pytest.mark.parametrize('detect_configured_files', [False, True], ids=['no_trace', 'w_trace'])
@pytest.mark.parametrize('returncode', [0, 1])
def test_parse_cmake_trace_log(mocker, tmp_path, with_cache_variables, detect_configured_files, returncode):
    cmake_cache_output = (
        ''
        if not with_cache_variables
        else dedent(
            f'''
CMAKE_ADDR2LINE:FILEPATH=/usr/bin/addr2line
CMAKE_CXX_FLAGS:STRING=
CMAKE_CXX_FLAGS_DEBUG:STRING=-g
CMAKE_CXX_FLAGS_MINSIZEREL:STRING=-Os -DNDEBUG
CMAKE_CXX_FLAGS_RELEASE:STRING=-O3 -DNDEBUG
CMAKE_CXX_FLAGS_RELWITHDEBINFO:STRING=-O2 -g -DNDEBUG
wCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=
CMAKE_INSTALL_BINDIR:PATH=bin
CMAKE_INSTALL_DATADIR:PATH=
CMAKE_LINKER:FILEPATH=/usr/bin/ld
CMAKE_VERBOSE_MAKEFILE:BOOL=FALSE
FETCHCONTENT_BASE_DIR:PATH={tmp_path.as_posix()}/build/_deps
    '''
        )
    )

    call_cmake = mocker.patch(
        'cmake_pc_hooks._cmake.CMakeCommand._call_cmake',
        return_value=mocker.Mock(stdout=cmake_cache_output, stderr='', returncode=returncode),
    )

    # ----------------------------------

    cmake_trace_log = tmp_path / 'log.json'
    cmake_trace_log.write_text(
        dedent(
            f'''{{"version":{{"major":1,"minor":2}}}}
{{"args":["VERSION","3.20"],"cmd":"cmake_minimum_required","file":"{tmp_path.as_posix()}/CMakeLists.txt","frame":1,"global_frame":1,"line":1,"time":1684940081.6217611}}
{{"args":["test","LANGUAGES","CXX"],"cmd":"project","file":"{tmp_path.as_posix()}/CMakeLists.txt","frame":1,"global_frame":1,"line":3,"time":1684940081.6219001}}
{{"args":["/usr/share/cmake/Modules/FetchContent/CMakeLists.cmake.in","{tmp_path.as_posix()}/build/_deps/catch2-subbuild/CMakeLists.txt"],"cmd":"configure_file","file":"/usr/share/cmake/Modules/FetchContent.cmake","frame":5,"global_frame":5,"line":1598,"line_end":1599,"time":1684940081.7072489}}
{{"args":["{tmp_path.as_posix()}/build/_deps/catch2-src/src/catch2/catch_user_config.hpp.in","{tmp_path.as_posix()}/build/generated-includes/catch2/catch_user_config.hpp"],"cmd":"configure_file","file":"{tmp_path.as_posix()}/build/_deps/catch2-src/src/CMakeLists.txt","frame":1,"global_frame":4,"line":308,"line_end":311,"time":1684940082.2564831}}
{{"args":["test.cpp.in","test.cpp"],"cmd":"configure_file","file":"{tmp_path.as_posix()}/CMakeLists.txt","frame":1,"global_frame":1,"line":17,"time":1684940082.260792}}
{{"args":["test.cpp.in","{tmp_path.as_posix()}/other.cpp"],"cmd":"configure_file","file":"{tmp_path.as_posix()}/CMakeLists.txt","frame":1,"global_frame":1,"line":18,"time":1684940082.2613621}}
            '''
        )
    )

    cmake = CMakeCommand()
    cmake.source_dir = tmp_path
    cmake.build_dir = tmp_path / 'build'
    if detect_configured_files:
        cmake.cmake_trace_log = cmake_trace_log

    cmake._parse_cmake_trace_log()

    if not detect_configured_files:
        call_cmake.assert_not_called()
    else:
        call_cmake.assert_called_once_with(extra_args=['-N', '-LA'])

    if returncode != 0 or not detect_configured_files:
        assert not cmake.cmake_configured_files
    else:
        configured_files = {
            str(cmake.source_dir / 'other.cpp'),
            str(cmake.build_dir / 'test.cpp'),
        }
        if with_cache_variables:
            assert set(cmake.cmake_configured_files) == configured_files
        else:
            # NB: the remaining file is the one configured within FETCHCONTENT_BASE_DIR
            assert len(set(cmake.cmake_configured_files) ^ configured_files) == 1
