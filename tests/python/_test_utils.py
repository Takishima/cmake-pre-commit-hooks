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

# ==============================================================================


class ExitError(Exception):
    pass


# ==============================================================================


def default_command_assertions(read_json_db_settings, all_at_once, configure, call_process, command):
    if configure is not None:
        configure.assert_called_once_with(command.command)

    if read_json_db_settings['value']:
        assert len(command.files) == read_json_db_settings['n_files_true']
    else:
        assert len(command.files) == read_json_db_settings['n_files_false']

    if all_at_once:
        call_process.assert_called_once()
    else:
        call_process.assert_called()
        assert call_process.call_count == len(command.files)  # NB: CMake call does not occur


# ==============================================================================


def command_main_asserts(mocker, submodule, main, argv):
    mocker.patch('hooks.utils.Command.check_installed', return_value=True)
    run = mocker.patch(f'cmake_pc_hooks.{submodule}.run')

    main(argv)
    run.assert_called_once_with()

    mocker.patch('sys.argv', return_value=argv)

    main()
    assert run.call_count == 2
    run.assert_called_with()


# ==============================================================================
