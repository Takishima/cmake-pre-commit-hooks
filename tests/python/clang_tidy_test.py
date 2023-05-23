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

import pytest
from _test_utils import ExitError, command_main_asserts, default_command_assertions

from cmake_pc_hooks import clang_tidy


# ==============================================================================


@pytest.mark.parametrize('stdout', ['', 'aaa'], ids=['<empty>', 'aaa'])
@pytest.mark.parametrize(
    'error_msg', [None, '1 error generated.', '2 errors generated.'], ids=['<empty>', '1_error', '2_errors']
)
def test_clang_tidy_command(mocker, compile_commands, tmp_path, setup_command, stdout, error_msg):
    path, file_list = compile_commands
    all_at_once, read_json_db, returncode, cmd_args, configure, sys_exit = setup_command

    # ----------------------------------

    def _call_process(*args, **kwargs):  # noqa: ARG001
        return mocker.Mock(
            stdout=stdout, stderr=f'{error_msg if error_msg is not None else ""} aaa\nbbb', returncode=returncode
        )

    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        side_effect=_call_process,
    )

    # ----------------------------------

    command_name = 'clang-tidy'
    other_file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in other_file_list:
        file.write_text('')

    args = [f'{command_name}', f'-B{path.parent}', *cmd_args, *[str(fname) for fname in other_file_list]]

    command = clang_tidy.ClangTidyCmd(args=args)
    assert set(command.files) == {str(fname) for fname in other_file_list}

    with contextlib.suppress(ExitError):
        command.run()

    default_command_assertions(
        read_json_db_settings={
            'value': read_json_db,
            'n_files_true': len(other_file_list) + len(file_list),
            'n_files_false': len(other_file_list),
        },
        all_at_once=all_at_once,
        configure=None,
        call_process=call_process,
        command=command,
    )

    if returncode == 0 and (error_msg is None or not stdout):
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with(1)


# ==============================================================================


def test_clang_tidy_main(mocker):
    argv = ['clang-tidy', 'file.txt']
    command_main_asserts(mocker, 'clang_tidy.ClangTidyCmd', clang_tidy.main, argv)


# ==============================================================================
