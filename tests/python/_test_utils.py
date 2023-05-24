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

# ==============================================================================


class ExitError(Exception):
    pass


# ==============================================================================


def run_command_default_assertions(
    read_json_db,
    json_db_file_list,
    file_list,
    command,
    all_at_once,
    configure,
    call_process,
    returncode,
    sys_exit,
    exit_success=None,
    do_configure_test=True,
    detect_configured_files=False,
    **kwargs,  # noqa: ARG001
):
    assert set(command.files) == {str(fname) for fname in file_list}

    with contextlib.suppress(ExitError):
        command.run()

    if do_configure_test:
        configure.assert_called_once_with(command.command)

    if exit_success is None:
        exit_success = returncode == 0

    n_files = len(file_list)

    if read_json_db:
        n_files += len(json_db_file_list)
    if detect_configured_files:
        n_files += len(command.cmake.cmake_configured_files)

    assert len(command.files) == n_files

    for fname in file_list:
        assert str(fname) in command.files

    if read_json_db:
        for fname in json_db_file_list:
            assert str(fname) in command.files

    for fname in command.cmake.cmake_configured_files:
        assert str(fname) in command.files

    if all_at_once:
        call_process.assert_called_once()
    else:
        call_process.assert_called()
        assert call_process.call_count == len(command.files)  # NB: CMake call does not occur

    assert all(result.returncode == returncode for result in command.history)

    if exit_success:
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with(1)


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
