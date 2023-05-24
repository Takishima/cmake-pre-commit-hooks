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

from cmake_pc_hooks import lizard

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


def test_lizard_main(mocker):
    argv = ['lizard', 'file.txt']
    command_main_asserts(mocker, 'lizard.LizardCmd', lizard.main, argv)


# ==============================================================================
