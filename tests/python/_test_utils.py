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
    *,
    runner,
    read_json_db,
    json_db_file_list,
    file_list,
    all_at_once,
    create_compilation_db,
    configure,
    call_process,
    returncode,
    sys_exit,
    exit_success=None,
    uses_cmake=True,
    **kwargs,
):
    assert set(runner.files) == {str(fname) for fname in file_list}

    with contextlib.suppress(ExitError):
        runner.run()

    if uses_cmake:
        configure.assert_called_once_with(runner.hook.name, clean_build=False)
    else:
        assert runner.cmake is None
        configure.assert_not_called()

    expected_files = {str(fname) for fname in file_list}
    if read_json_db and create_compilation_db:
        expected_files |= {str(fname) for fname in json_db_file_list}
    if runner.cmake:
        expected_files |= set(runner.cmake.cmake_configured_files)
    assert set(runner.files) == expected_files
    assert len(runner.files) == len(expected_files)

    if all_at_once:
        call_process.assert_called_once()
    else:
        assert call_process.call_count == len(runner.files)

    if exit_success is None:
        exit_success = returncode == 0
    if exit_success:
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with(1)


# ==============================================================================


def command_main_asserts(mocker, module, argv):
    hook_runner = mocker.patch('cmake_pc_hooks._runner.HookRunner')

    module.main(argv)
    hook_runner.assert_called_once_with(module.HOOK, argv)
    hook_runner.return_value.run.assert_called_once_with()

    mocker.patch('sys.argv', argv)
    module.main()
    assert hook_runner.call_count == 2
    assert hook_runner.return_value.run.call_count == 2


# ==============================================================================
