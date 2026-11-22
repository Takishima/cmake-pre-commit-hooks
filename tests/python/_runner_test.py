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

from cmake_pc_hooks import _runner
from cmake_pc_hooks._call_process import History
from cmake_pc_hooks._cmake import CMakeCommand
from cmake_pc_hooks._hook import Hook, has_failed, has_failed_quiet_on_success

import click
import pytest
from _test_utils import ExitError, run_command_default_assertions

TOOL = 'test-exec'

# ==============================================================================


def _call_process(mocker, **kwargs):
    result = {'stdout': '', 'stderr': '', 'returncode': 0, **kwargs}
    return mocker.patch('cmake_pc_hooks._call_process.call_process', side_effect=lambda *_: History(**result))


# ==============================================================================


def test_find_executable(mocker):
    which = mocker.patch('shutil.which', side_effect=lambda name: f'/usr/bin/{name}' if name == 'two' else None)

    assert _runner.find_executable(('one', 'two', 'three')) == '/usr/bin/two'
    assert which.call_count == 2
    assert _runner.find_executable(('one', 'three')) is None


def test_read_compile_commands_no_file(tmp_path):
    assert not _runner._read_compile_commands_json(tmp_path / 'compile_commands.json')


def test_read_compile_commands(compile_commands):
    path, file_list = compile_commands
    assert _runner._read_compile_commands_json(path) == [str(fname) for fname in file_list]


@pytest.mark.parametrize('returncode', [0, 1])
def test_has_failed(mocker, returncode):
    result = mocker.Mock(returncode=returncode)
    assert has_failed(result) == bool(returncode)
    result.disable_print_output.assert_not_called()


@pytest.mark.parametrize('returncode', [0, 1])
def test_has_failed_quiet_on_success(mocker, returncode):
    result = mocker.Mock(returncode=returncode)
    assert has_failed_quiet_on_success(result) == bool(returncode)
    assert result.disable_print_output.call_count == (0 if returncode else 1)


# ==============================================================================


def test_runner_init_without_cmake(mocker, tool):
    get_cmake_command = mocker.patch('cmake_pc_hooks._cmake.locate.get_cmake_command')
    file_list = ['/path/to/one.cpp', '/path/to/two.cpp']

    runner = _runner.HookRunner(
        Hook(TOOL, default_args=('--key=1', '-q')), [TOOL, '--all-at-once', '--key=2', *file_list]
    )

    assert runner.command == TOOL
    assert runner.args == ['--key=2', '-q']
    assert runner.files == file_list
    assert not runner.compiler_args
    assert runner.all_at_once
    assert runner.cmake is None
    assert runner.compile_db is None
    get_cmake_command.assert_not_called()


@pytest.mark.parametrize('compile_db_arg', [None, '-p={}'])
def test_runner_init_with_cmake(mocker, tool, tmp_path, compile_db_arg):
    mocker.patch('cmake_pc_hooks._cmake.locate.get_cmake_command', return_value='cmake')
    build_dir = tmp_path / 'build'
    build_dir.mkdir()

    runner = _runner.HookRunner(
        Hook(TOOL, compile_db_arg=compile_db_arg),
        [TOOL, f'-S{tmp_path}', f'-B{build_dir}', '--read-json-db', 'one.cpp'],
    )

    assert isinstance(runner.cmake, CMakeCommand)
    assert runner.cmake.command == 'cmake'
    assert runner.compile_db == build_dir / 'compile_commands.json'
    assert runner.args == ([f'-p={runner.compile_db}'] if compile_db_arg else [])


def test_runner_compile_db_arg_not_overridden(mocker, tool, tmp_path):
    runner = _runner.HookRunner(Hook(TOOL, compile_db_arg='-p={}'), [TOOL, f'-B{tmp_path}', '-p=/other', 'one.cpp'])
    assert runner.args == ['-p=/other']


def test_runner_no_compile_db(tool, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    runner = _runner.HookRunner(
        Hook(TOOL, compile_db_arg='-p={}'), [TOOL, f'-B{tmp_path / "build"}', '--no-cmake-configure', 'one.cpp']
    )

    assert runner.cmake.build_dir is None
    assert runner.compile_db is None
    assert not runner.args


def test_runner_compile_db_from_build_dir_list(tool, monkeypatch, compile_commands, tmp_path):
    path, _ = compile_commands
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    monkeypatch.chdir(source_dir)

    runner = _runner.HookRunner(
        Hook(TOOL, compile_db_arg='-p={}'), [TOOL, f'-B{path.parent}', '--no-cmake-configure', 'one.cpp']
    )

    assert runner.cmake.build_dir is None
    assert runner.compile_db == path
    assert runner.args == [f'-p={path}']


def test_runner_preset_requires_build_dir(tool, tmp_path):
    with pytest.raises(_runner.CMakePresetError, match='pass --preset as a CMake argument'):
        _runner.HookRunner(Hook(TOOL), [TOOL, f'-S{tmp_path}', '--preset=default', 'one.cpp'])


def test_runner_invalid_source_dir(tool, tmp_path):
    with pytest.raises(click.UsageError, match='does not exist'):
        _runner.HookRunner(Hook(TOOL), [TOOL, f'-S{tmp_path / "other"}', 'one.cpp'])


def test_runner_tool_not_found(mocker, capsys):
    mocker.patch('shutil.which', return_value=None)
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)

    with pytest.raises(ExitError):
        _runner.HookRunner(Hook(TOOL), [TOOL, 'one.cpp'])

    sys_exit.assert_called_once_with(1)
    stderr = capsys.readouterr().err
    assert f'Problem with {TOOL}: {TOOL} not found' in stderr
    assert 'cmake-pre-commit-hooks' in stderr


def test_runner_double_dash(tool, tmp_path):
    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')
    argv = [TOOL, '--checks=*', '--', '-std=c++17', *[str(fname) for fname in file_list]]

    runner = _runner.HookRunner(Hook(TOOL), argv)
    assert runner.files == argv[3:]
    assert not runner.compiler_args

    runner = _runner.HookRunner(Hook(TOOL, double_dash=True), argv)
    assert runner.files == [str(fname) for fname in file_list]
    assert runner.compiler_args == ['--', '-std=c++17']
    assert runner.args == ['--checks=*']

    runner = _runner.HookRunner(Hook(TOOL, double_dash=True), [TOOL, str(file_list[0])])
    assert runner.files == [str(file_list[0])]
    assert not runner.compiler_args


# ==============================================================================


@pytest.mark.parametrize(
    ('version_prefix', 'stdout', 'expected', 'returncode'),
    [
        ('clang-format version ', 'Ubuntu clang-format version 18.1.3 (1ubuntu1)', '18.1.3', 0),
        ('LLVM version ', 'LLVM (http://llvm.org/):\n  LLVM version 14.0.0\n', '14', 0),
        ('Cppcheck ', 'Cppcheck 2.13.0', '2.13', 0),
        ('cpplint ', 'Cpplint fork (https://github.com/cpplint/cpplint)\ncpplint 2.0.0\nPython 3.12', '2.0.0', 0),
        ('', '1.17.10', '1.17', 0),
        ('', '1.17.10', '1.18', 1),
        ('', '1.17.10', '7.10', 1),
    ],
    ids=['clang-format', 'clang-tidy', 'cppcheck', 'cpplint', 'lizard', 'wrong', 'not_a_prefix'],
)
def test_runner_version_check(mocker, tool, capsys, version_prefix, stdout, expected, returncode):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    call_process = _call_process(mocker, stdout=stdout)

    with pytest.raises(ExitError):
        _runner.HookRunner(Hook(TOOL, version_prefix=version_prefix), [TOOL, f'--version={expected}', 'one.cpp'])

    call_process.assert_called_once_with([TOOL, '--version'])
    sys_exit.assert_called_once_with(returncode)
    stderr = capsys.readouterr().err
    if returncode:
        assert f'Version of {TOOL} is wrong\nExpected version: {expected}\nFound version: 1.17.10' in stderr
    else:
        assert not stderr


def test_runner_version_check_no_version_found(mocker, tool, capsys):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    _call_process(mocker, stdout='no version here')

    with pytest.raises(ExitError):
        _runner.HookRunner(Hook(TOOL, version_prefix='test-exec '), [TOOL, '--version=1', 'one.cpp'])

    sys_exit.assert_called_once_with(1)
    assert f'Problem with {TOOL}: getting version' in capsys.readouterr().err


def test_runner_version_check_other_executable(mocker, tool, capsys):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    call_process = _call_process(mocker, stdout='other 0.21 based on clang')
    hook = Hook(TOOL, version_prefix='other ', version_executables=('other',))

    with pytest.raises(ExitError):
        _runner.HookRunner(hook, [TOOL, '--version=0.21', 'one.cpp'])
    call_process.assert_called_once_with(['other', '--version'])
    sys_exit.assert_called_once_with(0)

    tool.side_effect = lambda names: None if names == ('other',) else names[0]
    sys_exit.reset_mock()
    with pytest.raises(ExitError):
        _runner.HookRunner(hook, [TOOL, '--version=0.21', 'one.cpp'])
    sys_exit.assert_called_once_with(1)
    assert 'Unable to locate any of: other' in capsys.readouterr().err


# ==============================================================================


@pytest.mark.parametrize('detect_configured_files', [False, True], ids=['no_file_detect', 'w_file_detect'])
@pytest.mark.parametrize('check_failed', [False, True])
def test_runner_run(mocker, check_failed, setup_command, detect_configured_files):
    path = setup_command.compile_db_path
    check = mocker.Mock(return_value=check_failed)

    runner = _runner.HookRunner(
        Hook(TOOL, compile_db_arg='-p={}', check=check), [TOOL, f'-B{path.parent}', *setup_command.cmd_args]
    )
    if detect_configured_files:
        runner.cmake.cmake_configured_files = ['configured.cpp']

    run_command_default_assertions(runner=runner, exit_success=not check_failed, **setup_command._asdict())

    assert ('configured.cpp' in runner.files) == detect_configured_files
    assert check.call_count == setup_command.call_process.call_count
    for call in setup_command.call_process.return_value.to_stdout_and_stderr.call_args_list:
        assert call == mocker.call()


@pytest.mark.parametrize('uses_compile_db', [False, True])
def test_runner_run_cmake_on_demand(setup_command, uses_compile_db):
    path = setup_command.compile_db_path
    hook = Hook(TOOL, compile_db_arg='-p={}' if uses_compile_db else None)

    runner = _runner.HookRunner(hook, [TOOL, f'-B{path.parent}', *setup_command.cmd_args])

    run_command_default_assertions(
        runner=runner, uses_cmake=uses_compile_db or setup_command.read_json_db, **setup_command._asdict()
    )


def test_runner_run_clean_build(mocker, tool, tmp_path):
    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)
    _call_process(mocker)

    runner = _runner.HookRunner(Hook(TOOL), [TOOL, f'-B{tmp_path}', '--read-json-db', '--clean', 'one.cpp'])
    runner.run()

    configure.assert_called_once_with(TOOL, clean_build=True)


@pytest.mark.parametrize('all_at_once', [False, True])
def test_runner_run_no_files(mocker, tool, all_at_once):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    call_process = _call_process(mocker)

    runner = _runner.HookRunner(Hook(TOOL), [TOOL, *(['--all-at-once'] if all_at_once else [])])
    if all_at_once:
        runner.run()
        call_process.assert_called_once_with([TOOL])
        sys_exit.assert_not_called()
    else:
        with pytest.raises(ExitError):
            runner.run()
        call_process.assert_not_called()
        sys_exit.assert_called_once_with(1)


def test_runner_command_line(mocker, tool, tmp_path):
    call_process = _call_process(mocker)
    file_list = [str(tmp_path / 'file1.cpp'), str(tmp_path / 'file2.cpp')]
    for file in file_list:
        Path(file).write_bytes(b'')
    argv = [TOOL, '--opt', '--', '-std=c++17', *file_list]

    _runner.HookRunner(Hook(TOOL, double_dash=True, file_arg=lambda name: f'--file={name}'), argv).run()
    assert call_process.call_args_list == [
        mocker.call([TOOL, f'--file={name}', '--opt', '--', '-std=c++17']) for name in file_list
    ]

    call_process.reset_mock()
    _runner.HookRunner(Hook(TOOL, options_first=True), [TOOL, '--opt', '--all-at-once', *file_list]).run()
    call_process.assert_called_once_with([TOOL, '--opt', *file_list])


@pytest.mark.parametrize('returncodes', [(1, 0), (0, 1), (1, 1)], ids=['first_fails', 'last_fails', 'all_fail'])
def test_runner_any_failing_file_is_an_error(mocker, tool, capsys, returncodes):
    sys_exit = mocker.patch('sys.exit')
    mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        side_effect=[
            History(stdout=f'stdout {index}\n', stderr=f'stderr {index}\n', returncode=returncode)
            for index, returncode in enumerate(returncodes)
        ],
    )

    _runner.HookRunner(Hook(TOOL, check=has_failed_quiet_on_success), [TOOL, 'file1.cpp', 'file2.cpp']).run()

    sys_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    for index, returncode in enumerate(returncodes):
        assert (f'stdout {index}' in captured.out) == bool(returncode)
        assert (f'stderr {index}' in captured.err) == bool(returncode)


# ==============================================================================

UNFORMATTED = 'int  main( ){\n  return 0;}\n'
FORMATTED = 'int main() {\n  return 0;\n}\n'
FORMATTER = Hook(TOOL, formatter=True)


def _fake_formatter(mocker, *, stderr='', returncode=0):
    """Mock call_process() with a formatter that always produces FORMATTED (and writes it to the file with -i)."""

    def _format(args):
        if '-i' in args:
            Path(args[-1]).write_bytes(FORMATTED.encode())
            return History(stdout='', stderr=stderr, returncode=returncode)
        if '-n' in args or '--dry-run' in args:
            return History(stdout='', stderr=stderr, returncode=returncode)
        return History(stdout=FORMATTED, stderr=stderr, returncode=returncode)

    return mocker.patch('cmake_pc_hooks._call_process.call_process', side_effect=_format)


@pytest.fixture
def source_files(tool, tmp_path):
    good, bad = tmp_path / 'good.cpp', tmp_path / 'bad.cpp'
    good.write_bytes(FORMATTED.encode())
    bad.write_bytes(UNFORMATTED.encode())
    return str(good), str(bad)


def test_formatter_formatted_file(mocker, capsys, source_files):
    good, _ = source_files
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_formatter(mocker)

    _runner.HookRunner(FORMATTER, [TOOL, '--style=Google', good]).run()

    call_process.assert_called_once_with([TOOL, '--style=Google', good])
    sys_exit.assert_not_called()
    assert not capsys.readouterr().out


def test_formatter_unformatted_files(mocker, capsys, source_files):
    good, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_formatter(mocker)

    _runner.HookRunner(FORMATTER, [TOOL, good, bad]).run()

    sys_exit.assert_called_once_with(1)
    stdout = capsys.readouterr().out
    assert stdout.startswith(f'{bad}\n{"=" * 20}\n--- original\n+++ formatted\n')
    assert '-int  main( ){' in stdout
    assert '+int main() {' in stdout
    assert good not in stdout
    assert Path(bad).read_bytes().decode() == UNFORMATTED


def test_formatter_no_diff(mocker, capsys, source_files):
    _, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_formatter(mocker)

    _runner.HookRunner(FORMATTER, [TOOL, '--no-diff', bad]).run()

    call_process.assert_called_once_with([TOOL, bad])
    sys_exit.assert_called_once_with(1)
    assert not capsys.readouterr().out


def test_formatter_edit_in_place_fails_if_file_modified(mocker, capsys, source_files):
    good, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_formatter(mocker)

    _runner.HookRunner(FORMATTER, [TOOL, '-i', good, bad]).run()

    sys_exit.assert_called_once_with(1)
    assert Path(bad).read_bytes().decode() == FORMATTED
    stdout = capsys.readouterr().out
    assert bad in stdout
    assert good not in stdout


@pytest.mark.parametrize(('stderr', 'returncode'), [('some warning', 0), ('', 1)], ids=['stderr', 'returncode'])
def test_formatter_failure(mocker, capsys, source_files, stderr, returncode):
    _, bad = source_files
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    _fake_formatter(mocker, stderr=stderr, returncode=returncode)

    with pytest.raises(ExitError):
        _runner.HookRunner(FORMATTER, [TOOL, '-n', bad]).run()

    sys_exit.assert_called_once_with(1)
    assert 'Unexpected Stderr/return code received' in capsys.readouterr().err


@pytest.mark.parametrize('option', ['-n', '--dry-run'])
def test_formatter_dry_run_success(mocker, capsys, source_files, option):
    good, _ = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_formatter(mocker)

    _runner.HookRunner(FORMATTER, [TOOL, option, good]).run()

    sys_exit.assert_not_called()
    assert not capsys.readouterr().out


def test_formatter_empty_file(mocker, capsys, tool, tmp_path):
    sys_exit = mocker.patch('sys.exit')
    _call_process(mocker)
    empty = tmp_path / 'empty.cpp'
    empty.write_bytes(b'')

    _runner.HookRunner(FORMATTER, [TOOL, str(empty)]).run()

    sys_exit.assert_not_called()
    assert not capsys.readouterr().out


def test_formatter_missing_file(mocker, capsys, tool, tmp_path):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    missing = str(tmp_path / 'missing.cpp')

    with pytest.raises(ExitError):
        _runner.HookRunner(FORMATTER, [TOOL, missing]).run()

    sys_exit.assert_called_once_with(1)
    assert f'File {missing} not found' in capsys.readouterr().err


# ==============================================================================


def test_make_main(mocker):
    hook = Hook(TOOL)
    hook_runner = mocker.patch('cmake_pc_hooks._runner.HookRunner')
    main = _runner.make_main(hook)

    main([TOOL, 'one.cpp'])
    hook_runner.assert_called_once_with(hook, [TOOL, 'one.cpp'])
    hook_runner.return_value.run.assert_called_once_with()

    mocker.patch('sys.argv', [TOOL, 'two.cpp'])
    main()
    hook_runner.assert_called_with(hook, [TOOL, 'two.cpp'])


@pytest.mark.parametrize(
    ('args', 'returncode', 'stdout', 'stderr'),
    [
        (['--help'], 0, 'Usage: cmake-pc-test-exec-hook', ''),
        (['--dump-toml', '--all-at-once'], 0, 'all_at_once = true', ''),
        (['-S', 'missing'], 2, '', "Error: Invalid value for '-S' / '--source-dir'"),
        (['--preset=default'], 2, '', 'Error: You *must* specify -B|--build-dir'),
    ],
    ids=['help', 'dump_toml', 'invalid_option', 'preset_without_build_dir'],
)
def test_make_main_command_line_errors(mocker, tool, capsys, monkeypatch, tmp_path, args, returncode, stdout, stderr):
    monkeypatch.chdir(tmp_path)
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)

    main = _runner.make_main(Hook(TOOL))

    with pytest.raises(ExitError):
        main([TOOL, *args, 'one.cpp'])

    sys_exit.assert_called_once_with(returncode)
    captured = capsys.readouterr()
    assert stdout in captured.out
    assert stderr in captured.err


# ==============================================================================
