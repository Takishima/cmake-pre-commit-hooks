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

from cmake_pc_hooks import lizard

# ==============================================================================


def test_lizard_command(compile_commands, tmp_path, setup_command):
    path, file_list = compile_commands

    # ----------------------------------

    command_name = 'lizard'
    other_file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in other_file_list:
        file.write_text('')

    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args, *[str(fname) for fname in other_file_list]]

    command = lizard.LizardCmd(args=args)
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
        do_configure_test=setup_command.read_json_db,
        **setup_command._asdict(),
    )


# ==============================================================================


def test_lizard_main(mocker):
    argv = ['lizard', 'file.txt']
    command_main_asserts(mocker, 'lizard.LizardCmd', lizard.main, argv)


# ==============================================================================