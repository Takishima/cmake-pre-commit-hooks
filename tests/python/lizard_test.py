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


from cmake_pc_hooks import lizard

import pytest
from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_lizard_command(tmp_path, setup_command):
    path = setup_command.compile_db_path

    # ----------------------------------

    command_name = 'lizard'
    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')

    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args]
    command = lizard.LizardCmd(args=args)

    run_command_default_assertions(
        command=command,
        do_configure_test=setup_command.read_json_db,
        **setup_command._asdict(),
    )


# ==============================================================================


@pytest.mark.parametrize('returncodes', [(1, 0), (0, 1), (1, 1)], ids=['first_fails', 'last_fails', 'all_fail'])
def test_lizard_any_failing_file_is_an_error(mocker, tmp_path, returncodes):
    mocker.patch('cmake_pc_hooks._utils.Command.check_installed', return_value=True)
    sys_exit = mocker.patch('sys.exit')
    mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        side_effect=[mocker.Mock(stdout='', stderr='', returncode=returncode) for returncode in returncodes],
    )

    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')

    command = lizard.LizardCmd(args=['lizard', *[str(fname) for fname in file_list]])
    command.run()

    sys_exit.assert_called_once_with(1)


def test_lizard_clean_build(mocker, tmp_path):
    mocker.patch('cmake_pc_hooks._utils.Command.check_installed', return_value=True)
    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)
    mocker.patch(
        'cmake_pc_hooks._call_process.call_process', return_value=mocker.Mock(stdout='', stderr='', returncode=0)
    )
    (tmp_path / 'file1.cpp').write_text('')

    command = lizard.LizardCmd(
        args=['lizard', f'-B{tmp_path}', '--read-json-db', '--clean', str(tmp_path / 'file1.cpp')]
    )
    command.run()

    configure.assert_called_once_with(command.command, clean_build=True)


# ==============================================================================


def test_lizard_main(mocker):
    argv = ['lizard', 'file.txt']
    command_main_asserts(mocker, 'lizard.LizardCmd', lizard.main, argv)


# ==============================================================================
