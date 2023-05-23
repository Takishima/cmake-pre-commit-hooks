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

from cmake_pc_hooks import cppcheck

# ==============================================================================


@pytest.mark.parametrize('all_at_once', [False, True])
@pytest.mark.parametrize('read_json_db', [False, True])
@pytest.mark.parametrize('returncode', [0, 1])
def test_cppcheck_command(mocker, compile_commands, tmp_path, read_json_db, all_at_once, returncode):
    mocker.patch('hooks.utils.Command.check_installed', return_value=True)

    cppcheck_useless_error_msg = 'Cppcheck cannot find all the include files'

    def _call_process(*args, **kwargs):  # noqa: ARG001
        return mocker.Mock(stdout='aaa\nbbb', stderr=f'{cppcheck_useless_error_msg} aaa\nbbb', returncode=returncode)

    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        side_effect=_call_process,
    )
    sys_exit = mocker.patch('sys.exit')

    _, file_list = compile_commands
    command_name = 'cppcheck'
    build_dir = tmp_path / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    other_file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in other_file_list:
        file.write_text('')

    args = [f'{command_name}', f'-B{build_dir}', *[str(fname) for fname in other_file_list]]

    if read_json_db:
        args.append('--read-json-db')

    if all_at_once:
        args.append('--all-at-once')

    command = cppcheck.CppcheckCmd(args=args)
    assert '-q' in command.args
    assert '--error-exitcode=1' in command.args
    assert '--enable=all' in command.args
    assert command.files == [str(fname) for fname in other_file_list]

    command.run()

    if read_json_db:
        assert len(command.files) == len(other_file_list) + len(file_list)
    else:
        assert len(command.files) == len(other_file_list)

    configure.assert_called_once_with(command_name)
    if all_at_once:
        call_process.assert_called()
        assert call_process.call_count == 1  # NB: CMake call does not occur
    else:
        call_process.assert_called()
        assert call_process.call_count == len(command.files)  # NB: CMake call does not occur

    assert not any(
        f'{cppcheck_useless_error_msg}'.encode() in line for line in command.stderr.splitlines(keepends=True)
    )

    if returncode == 0:
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with(1)


# ==============================================================================


def test_cppcheck_main(mocker):
    run = mocker.patch('cmake_pc_hooks.cppcheck.CppcheckCmd.run')

    argv = ['cppcheck', 'file.txt']

    cppcheck.main(argv)
    run.assert_called_once_with()

    mocker.patch('sys.argv', return_value=argv)

    cppcheck.main()
    assert run.call_count == 2
    run.assert_called_with()


# ==============================================================================
