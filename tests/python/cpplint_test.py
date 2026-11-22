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

from cmake_pc_hooks import cpplint

import pytest
from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_cpplint_command_passes_options_before_files(setup_command):
    path = setup_command.compile_db_path

    args = ['cpplint', f'-B{path.parent}', '--filter=-legal/copyright', *setup_command.cmd_args]
    command = cpplint.CpplintCmd(args=args)
    assert command.args == ['--filter=-legal/copyright', '--verbose=0']

    run_command_default_assertions(
        command=command,
        do_configure_test=setup_command.read_json_db,
        **setup_command._asdict(),
    )

    for call in setup_command.call_process.call_args_list:
        assert call.args[0][:3] == ['cpplint', '--filter=-legal/copyright', '--verbose=0']
        assert set(call.args[0][3:]) <= set(command.files)


def test_cpplint_verbose_not_overridden(mocker):
    mocker.patch('cmake_pc_hooks._utils.Command.check_installed', return_value=True)

    command = cpplint.CpplintCmd(args=['cpplint', '--verbose=3', 'file.cpp'])
    assert command.args == ['--verbose=3']
    assert command.files == ['file.cpp']


@pytest.mark.parametrize('returncodes', [(1, 0), (0, 1), (1, 1)], ids=['first_fails', 'last_fails', 'all_fail'])
def test_cpplint_any_failing_file_is_an_error(mocker, capsys, tmp_path, returncodes):
    mocker.patch('cmake_pc_hooks._utils.Command.check_installed', return_value=True)
    sys_exit = mocker.patch('sys.exit')
    mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        side_effect=[
            mocker.Mock(stdout='', stderr=f'error {index}\n' if returncode else '', returncode=returncode)
            for index, returncode in enumerate(returncodes)
        ],
    )

    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    command = cpplint.CpplintCmd(args=['cpplint', *[str(fname) for fname in file_list]])
    command.run()

    sys_exit.assert_called_once_with(1)
    stderr = capsys.readouterr().err
    for index, returncode in enumerate(returncodes):
        assert (f'error {index}' in stderr) == bool(returncode)


# ==============================================================================


def test_cpplint_main(mocker):
    argv = ['cpplint', 'file.txt']
    command_main_asserts(mocker, 'cpplint.CpplintCmd', cpplint.main, argv)


# ==============================================================================
