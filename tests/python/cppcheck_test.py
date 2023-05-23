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


from _test_utils import command_main_asserts, run_command_default_assertions

from cmake_pc_hooks import cppcheck

# ==============================================================================


def test_cppcheck_command(mocker, setup_command):
    path = setup_command.compile_db_path
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
    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args]

    command = cppcheck.CppcheckCmd(args=args)
    assert '-q' in command.args
    assert '--error-exitcode=1' in command.args
    assert '--enable=all' in command.args
    assert f'--project={path}' in command.args

    run_command_default_assertions(
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
