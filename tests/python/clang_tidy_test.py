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
from _test_utils import command_main_asserts, run_command_default_assertions

from cmake_pc_hooks import clang_tidy

# ==============================================================================


@pytest.mark.parametrize('stdout', ['', 'aaa'], ids=['<empty>', 'aaa'])
@pytest.mark.parametrize(
    'error_msg', [None, '1 error generated.', '2 errors generated.'], ids=['<empty>', '1_error', '2_errors']
)
def test_clang_tidy_command(mocker, setup_command, stdout, error_msg):
    path = setup_command.compile_db_path
    call_process = setup_command.call_process
    returncode = setup_command.returncode

    # ----------------------------------

    def _call_process(*args, **kwargs):  # noqa: ARG001
        return mocker.Mock(
            stdout=stdout, stderr=f'{error_msg if error_msg is not None else ""} aaa\nbbb', returncode=returncode
        )

    call_process.reset_mock(return_value=True, side_effect=True)
    call_process.configure_mock(
        side_effect=_call_process,
    )

    # ----------------------------------

    command_name = 'clang-tidy'
    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args]
    command = clang_tidy.ClangTidyCmd(args=args)

    assert f'-p={path}' in command.args

    run_command_default_assertions(
        command=command,
        exit_success=returncode == 0 and (error_msg is None or not stdout),
        **setup_command._asdict(),
    )


# ==============================================================================


def test_clang_tidy_main(mocker):
    argv = ['clang-tidy', 'file.txt']
    command_main_asserts(mocker, 'clang_tidy.ClangTidyCmd', clang_tidy.main, argv)


# ==============================================================================
