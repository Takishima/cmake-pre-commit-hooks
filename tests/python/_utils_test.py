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


import pytest
from _test_utils import run_command_default_assertions

from cmake_pc_hooks import _utils
from cmake_pc_hooks._cmake import CMakeCommand

# ==============================================================================


def test_read_compile_commands_no_file(tmp_path):
    assert not _utils._read_compile_commands_json(tmp_path)


def test_read_compile_commands(compile_commands):
    path, file_list = compile_commands
    files = _utils._read_compile_commands_json(path.parent)
    assert files == [str(fname) for fname in file_list]


# ==============================================================================


@pytest.mark.parametrize('look_behind', [False, True])
def test_command_init_parse(mocker, look_behind, tmp_path):
    mocker.patch('cmake_pc_hooks._cmake.get_cmake_command', return_value='cmake')

    source_dir = tmp_path
    build_dir = tmp_path / 'build'

    build_dir.mkdir(exist_ok=True)

    command_name = 'test-exec'
    file_list = ['/path/to/one.cpp', '/path/to/two.cpp']
    args = [
        f'{command_name}',
        '--all-at-once',
        f'-S{source_dir}',
        f'-B{build_dir}',
        '--arg',
        *file_list,
    ]

    command = _utils.Command(command_name, look_behind, args)
    assert isinstance(command.cmake, CMakeCommand)
    assert command.cmake.command == 'cmake'
    assert command.command == command_name
    assert command.look_behind == look_behind
    assert command.args == args

    command.parse_args(args)
    assert command.args == ['--arg']
    assert command.files == file_list


@pytest.mark.parametrize('look_behind', [False, True])
def test_command_parse_args_invalid(mocker, tmp_path, look_behind):
    version_str = '0.1'
    mocker.patch('cmake_pc_hooks._cmake.get_cmake_command', return_value='cmake')
    mocker.patch('hooks.utils.Command.get_version_str', return_value=version_str)
    sys_exit = mocker.patch('sys.exit')

    # ----------------------------------

    source_dir = tmp_path
    build_dir = tmp_path / 'build'

    build_dir.mkdir(exist_ok=True)

    command_name = 'test-exec'
    file_list = ['/path/to/one.cpp', '/path/to/two.cpp']
    args = [
        f'{command_name}',
        *file_list,
    ]

    command = _utils.Command(command_name, look_behind, args)

    # ----------------------------------

    with pytest.raises(RuntimeError, match='pass --preset as a CMake argument'):
        command.parse_args([*args, f'-S{source_dir}', '--preset=/path/to/CMakePreset.json'])

    command.parse_args([*args, f'-S{tmp_path / "other"}'])
    sys_exit.assert_called_with(1)

    command.parse_args([*args, f'--version="{version_str}"'])
    sys_exit.assert_called_with(0)


@pytest.mark.parametrize('detect_configured_files', [False, True], ids=['no_file_detect', 'w_file_detect'])
@pytest.mark.parametrize('parsing_failed', [False, True])
def test_command_run(mocker, parsing_failed, setup_command, detect_configured_files):
    path = setup_command.compile_db_path

    # ----------------------------------

    parse_output = mocker.patch('cmake_pc_hooks._utils.Command._parse_output', return_value=parsing_failed)

    # ----------------------------------

    command_name = 'test-exec'
    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args]

    command = _utils.Command(command_name, look_behind=False, args=args)
    command.parse_args(args)

    if detect_configured_files:
        command.cmake.cmake_configured_files = ['configured.cpp']

    run_command_default_assertions(
        command=command,
        detect_configured_files=detect_configured_files,
        exit_success=not parsing_failed,
        **setup_command._asdict(),
    )

    if setup_command.all_at_once:
        parse_output.assert_called_once()
    else:
        assert parse_output.call_count == len(command.files)

    assert command.stdout.decode() == command.history[-1].stdout
    assert command.stderr.decode() == command.history[-1].stderr
    assert command.returncode == command.history[-1].returncode


def test_command_run_invalid(mocker, tmp_path):
    sys_exit = mocker.patch('sys.exit')
    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)

    command_name = 'test-exec'
    args = [
        f'{command_name}',
        f'-B{tmp_path}',
    ]

    command = _utils.Command(command_name, look_behind=False, args=args)
    command.parse_args(args)
    command.run()

    configure.assert_called_once_with(command.command)
    sys_exit.assert_called_once_with(1)


# ==============================================================================


def test_command_parse_output_invalid():
    command = _utils.Command('test', look_behind=False, args=[])
    assert command._parse_output(None) == NotImplemented


# ==============================================================================


def test_clang_analyzer_command(tmp_path):
    command_name = 'test-exec'
    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')

    rest_args = ['-std=c++17', *file_list]
    args = [f'{command_name}', '--checks=*', '--', *rest_args]
    command = _utils.ClangAnalyzerCmd(command_name, look_behind=False, args=args)
    command.parse_args(args)

    assert command.files == rest_args
    assert not command.ddash_args
    command.handle_ddash_args()
    assert set(command.files) == set(file_list)
    assert command.ddash_args == ['--', rest_args[0]]


# ==============================================================================
