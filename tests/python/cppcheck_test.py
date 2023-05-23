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

import contextlib

from _test_utils import ExitError, command_main_asserts, default_command_assertions

from cmake_pc_hooks import cppcheck

# ==============================================================================


def test_cppcheck_command(mocker, compile_commands, tmp_path, setup_command):
    path, file_list = compile_commands
    call_process = setup_command.call_process
    returncode = setup_command.returncode

    cppcheck_useless_error_msg = 'Cppcheck cannot find all the include files'

    def _call_process(*args, **kwargs):  # noqa: ARG001
        return mocker.Mock(stdout='aaa\nbbb', stderr=f'{cppcheck_useless_error_msg} aaa\nbbb', returncode=returncode)

    call_process.reset_mock(return_value=True, side_effect=True)
    call_process.configure_mock(
        side_effect=_call_process,
    )

    command_name = 'cppcheck'
    other_file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in other_file_list:
        file.write_text('')

    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args, *[str(fname) for fname in other_file_list]]

    command = cppcheck.CppcheckCmd(args=args)
    assert '-q' in command.args
    assert '--error-exitcode=1' in command.args
    assert '--enable=all' in command.args
    assert command.files == [str(fname) for fname in other_file_list]

    with contextlib.suppress(ExitError):
        command.run()

    default_command_assertions(
        read_json_db_settings={
            'value': setup_command.read_json_db,
            'n_files_true': len(other_file_list) + len(file_list),
            'n_files_false': len(other_file_list),
        },
        command=command,
        **setup_command._asdict(),
    )

    assert not any(
        f'{cppcheck_useless_error_msg}'.encode() in line for line in command.stderr.splitlines(keepends=True)
    )


# ==============================================================================


def test_cppcheck_main(mocker):
    argv = ['cppcheck', 'file.txt']
    command_main_asserts(mocker, 'cppcheck.CppcheckCmd', cppcheck.main, argv)


# ==============================================================================
