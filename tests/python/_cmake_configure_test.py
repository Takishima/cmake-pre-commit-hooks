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

from cmake_pc_hooks._call_process import History
from cmake_pc_hooks._cmake import CMakeCommand, CMakeOptions

import fasteners
import pytest
from _test_utils import ExitError

EXPORT_ARG = '-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON'

# ==============================================================================


@pytest.fixture(autouse=True)
def cmake_command(mocker):
    return mocker.patch('cmake_pc_hooks._cmake.locate.get_cmake_command', return_value=['cmake'])


def _fake_cmake(mocker, *, configure=0, build=0, cache=0, version='3.31.0', create_db=True):
    """Mock call_process() with a CMake that only creates the compilation database."""

    def _call_process(args, cwd=None):
        if '--version' in args:
            return History(stdout=f'cmake version {version}\n', stderr='', returncode=0)
        if '--build' in args:
            return History(stdout='build output\n', stderr='build error\n', returncode=build)
        if '-N' in args:
            return History(stdout='FETCHCONTENT_BASE_DIR:PATH=/deps\n', stderr='', returncode=cache)
        if create_db:
            Path(cwd, CMakeCommand.COMPILE_DB_NAME).write_bytes(b'[]')
        return History(stdout='configure output\n', stderr='configure error\n', returncode=configure)

    return mocker.patch('cmake_pc_hooks._call_process.call_process', side_effect=_call_process)


def _make_cmake(tmp_path, **kwargs):
    return CMakeCommand(CMakeOptions(source_dir=tmp_path, build_dirs=[str(tmp_path / 'build')], **kwargs))


# ==============================================================================


def test_init(cmake_command, tmp_path):
    cmake = CMakeCommand(CMakeOptions(source_dir=tmp_path, cmake_args=['-DONE']))

    cmake_command.assert_called_once_with()
    assert cmake.command == ['cmake']
    assert cmake.source_dir == tmp_path
    assert cmake.build_dir == tmp_path / CMakeCommand.DEFAULT_BUILD_DIR
    assert cmake.cmake_args == [EXPORT_ARG, '-DONE']
    assert cmake.cmake_trace_log is None
    assert not cmake.cmake_configured_files
    assert not cmake.build_targets


def test_init_with_cmake_path(cmake_command, tmp_path):
    cmake = _make_cmake(tmp_path, cmake=tmp_path / 'bin' / '..' / 'cmake')

    cmake_command.assert_not_called()
    assert cmake.command == [tmp_path / 'cmake']


@pytest.mark.parametrize('no_cmake_configure', [False, True])
def test_init_trace_log_requires_build_directory(tmp_path, no_cmake_configure):
    cmake = _make_cmake(tmp_path, detect_configured_files=True, no_cmake_configure=no_cmake_configure)

    if no_cmake_configure:
        assert cmake.build_dir is None
        assert cmake.cmake_trace_log is None
    else:
        assert cmake.cmake_trace_log == tmp_path / 'build' / CMakeCommand.DEFAULT_TRACE_LOG


@pytest.mark.parametrize(
    ('build_targets', 'codegen', 'expected'),
    [
        ([], False, []),
        (['one', 'two'], False, ['one', 'two']),
        ([], True, ['codegen']),
        (['one'], True, ['one', 'codegen']),
        (['codegen'], True, ['codegen']),
    ],
)
def test_init_build_targets(tmp_path, build_targets, codegen, expected):
    options = CMakeOptions(source_dir=tmp_path, build_targets=build_targets, codegen=codegen)

    assert CMakeCommand(options).build_targets == expected
    assert options.build_targets == build_targets


# ==============================================================================


def test_configure(mocker, capsys, tmp_path):
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_cmake(mocker)
    cmake = _make_cmake(tmp_path, cmake_args=['-DONE'])

    cmake.configure('test')

    call_process.assert_called_once_with(['cmake', str(tmp_path), EXPORT_ARG, '-DONE'], cwd=str(tmp_path / 'build'))
    sys_exit.assert_not_called()
    assert (tmp_path / 'build' / CMakeCommand.COMPILE_DB_NAME).exists()
    assert not cmake.cmake_configured_files
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


@pytest.mark.parametrize(('returncode', 'create_db'), [(2, True), (0, False)], ids=['cmake_fails', 'no_compile_db'])
def test_configure_failure(mocker, capsys, tmp_path, returncode, create_db):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    _fake_cmake(mocker, configure=returncode, create_db=create_db)
    cmake = _make_cmake(tmp_path, build_targets=['one'])

    with pytest.raises(ExitError):
        cmake.configure('test')

    sys_exit.assert_called_once_with(returncode or 1)
    captured = capsys.readouterr()
    assert 'Running CMake with:' in captured.out
    assert f'from within {tmp_path / "build"}' in captured.out
    assert 'configure output' in captured.out
    assert 'configure error' in captured.err
    assert ('Unable to locate' in captured.err) == (not create_db)


@pytest.mark.parametrize('clean_build', [False, True])
def test_configure_clean_build(mocker, tmp_path, clean_build):
    _fake_cmake(mocker)
    cmake = _make_cmake(tmp_path)
    stale_file = tmp_path / 'build' / 'stale.txt'
    stale_dir_file = tmp_path / 'build' / 'stale' / 'file.txt'
    stale_dir_file.parent.mkdir(parents=True)
    stale_file.write_bytes(b'')
    stale_dir_file.write_bytes(b'')

    cmake.configure('test', clean_build=clean_build)

    assert stale_file.exists() == (not clean_build)
    assert stale_dir_file.exists() == (not clean_build)
    assert (tmp_path / 'build' / '_cmake_configure_lock').exists()
    assert (tmp_path / 'build' / CMakeCommand.COMPILE_DB_NAME).exists()


def test_configure_skipped(mocker, caplog, tmp_path):
    call_process = _fake_cmake(mocker)

    _make_cmake(tmp_path, no_cmake_configure=True).configure('test')
    call_process.assert_not_called()
    assert 'Not building CMake target(s)' not in caplog.text

    _make_cmake(tmp_path, no_cmake_configure=True, codegen=True, build_targets=['one']).configure('test')
    call_process.assert_not_called()
    assert 'Not building CMake target(s) one, codegen' in caplog.text


def test_configure_waits_for_other_process(mocker, tmp_path):
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_cmake(mocker)
    cmake = _make_cmake(tmp_path, detect_configured_files=True)
    detect = mocker.patch.object(cmake, '_detect_configured_files')
    (tmp_path / 'build').mkdir()

    other_process = fasteners.InterProcessReaderWriterLock(tmp_path / 'build' / '_cmake_configure_lock')
    mocker.patch.object(fasteners.InterProcessReaderWriterLock, 'acquire_write_lock', return_value=False)
    read_lock = mocker.spy(fasteners.InterProcessReaderWriterLock, 'read_lock')

    cmake.configure('test')

    assert other_process is not None
    read_lock.assert_called_once()
    call_process.assert_not_called()
    sys_exit.assert_not_called()
    detect.assert_called_once_with()


# ==============================================================================


@pytest.mark.parametrize('cache_returncode', [0, 1])
def test_configure_detects_configured_files(mocker, tmp_path, cache_returncode):
    call_process = _fake_cmake(mocker, cache=cache_returncode)
    find_configured_files = mocker.patch(
        'cmake_pc_hooks._cmake.trace.find_configured_files', return_value=['configured.cpp']
    )
    cmake = _make_cmake(tmp_path, detect_configured_files=True)
    build_dir = tmp_path / 'build'

    cmake.configure('test')

    assert call_process.call_args_list == [
        mocker.call(
            [
                'cmake',
                str(tmp_path),
                EXPORT_ARG,
                '--trace-expand',
                '--trace-format=json-v1',
                f'--trace-redirect={build_dir / CMakeCommand.DEFAULT_TRACE_LOG}',
            ],
            cwd=str(build_dir),
        ),
        mocker.call(['cmake', str(tmp_path), EXPORT_ARG, '-N', '-LA'], cwd=str(build_dir)),
    ]
    if cache_returncode:
        find_configured_files.assert_not_called()
        assert not cmake.cmake_configured_files
    else:
        find_configured_files.assert_called_once_with(
            build_dir / CMakeCommand.DEFAULT_TRACE_LOG, tmp_path, build_dir, {'FETCHCONTENT_BASE_DIR': '/deps'}
        )
        assert cmake.cmake_configured_files == ['configured.cpp']


# ==============================================================================


@pytest.mark.parametrize('build_returncode', [0, 2])
@pytest.mark.parametrize('build_targets', [['one', 'two'], ['one', 'codegen']])
def test_configure_builds_targets(mocker, capsys, tmp_path, build_targets, build_returncode):
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_cmake(mocker, build=build_returncode)
    cmake = _make_cmake(tmp_path, build_targets=build_targets)

    cmake.configure('test')

    assert call_process.call_count == 2
    assert call_process.call_args == mocker.call(
        ['cmake', '--build', str(tmp_path / 'build'), '--target', *build_targets]
    )
    captured = capsys.readouterr()
    if build_returncode:
        sys_exit.assert_called_once_with(build_returncode)
        assert 'build output' in captured.out
        assert 'build error' in captured.err
        assert ('CMP0171' in captured.err) == ('codegen' in build_targets)
    else:
        sys_exit.assert_not_called()
        assert not captured.out
        assert not captured.err


def test_configure_does_not_build_after_failure(mocker, tmp_path):
    mocker.patch('sys.exit')
    call_process = _fake_cmake(mocker, configure=1)

    _make_cmake(tmp_path, build_targets=['one']).configure('test')

    call_process.assert_called_once()


@pytest.mark.parametrize(
    ('version', 'is_valid'),
    [('garbage', True), ('3.30.9', False), ('3.31.0', True), ('4.0.0', True)],
)
def test_configure_codegen_version_check(mocker, tmp_path, version, is_valid):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    call_process = _fake_cmake(mocker, version=version if version != 'garbage' else 'unknown')
    cmake = _make_cmake(tmp_path, codegen=True)

    if is_valid:
        cmake.configure('test')
        assert call_process.call_count == 3
        sys_exit.assert_not_called()
    else:
        with pytest.raises(ExitError):
            cmake.configure('test')
        call_process.assert_called_once_with(['cmake', '--version'])
        sys_exit.assert_called_once_with(1)


@pytest.mark.parametrize(
    ('cache_content', 'is_supported'),
    [
        (None, True),
        ('FOO:STRING=bar\n', True),
        ('CMAKE_GENERATOR:INTERNAL=Ninja\n', True),
        ('CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config\n', True),
        ('FOO:STRING=bar\nCMAKE_GENERATOR:INTERNAL=Unix Makefiles\nBAR:BOOL=ON\n', True),
        ('CMAKE_GENERATOR:INTERNAL=Xcode\n', False),
        ('CMAKE_GENERATOR:INTERNAL=Visual Studio 17 2022\n', False),
    ],
)
def test_configure_codegen_generator_check(mocker, tmp_path, cache_content, is_supported):
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_cmake(mocker)
    cmake = _make_cmake(tmp_path, codegen=True, automatic_discovery=False)
    if cache_content is not None:
        (tmp_path / 'build').mkdir()
        (tmp_path / 'build' / 'CMakeCache.txt').write_text(cache_content, encoding='utf-8')

    cmake.configure('test')

    if is_supported:
        assert call_process.call_count == 3
        sys_exit.assert_not_called()
    else:
        assert call_process.call_count == 2
        sys_exit.assert_called_once_with(1)


# ==============================================================================
