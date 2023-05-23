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

from cmake_pc_hooks import include_what_you_use

# ==============================================================================


def test_get_iwyu_tool_command(mocker):
    iwyu_tool_fname = 'iwyu_tool'
    shutil_which = mocker.patch('shutil.which', return_value=iwyu_tool_fname)
    assert include_what_you_use.get_iwyu_tool_command() == iwyu_tool_fname
    assert include_what_you_use.get_iwyu_tool_command([iwyu_tool_fname]) == iwyu_tool_fname

    shutil_which.configure_mock(return_value=None)
    assert include_what_you_use.get_iwyu_tool_command() is None


def test_get_iwyu_command(mocker):
    iwyu_fname = 'include-what-you-use'
    shutil_which = mocker.patch('shutil.which', return_value=iwyu_fname)
    assert include_what_you_use.get_iwyu_command() == iwyu_fname
    assert include_what_you_use.get_iwyu_command([iwyu_fname]) == iwyu_fname

    shutil_which.configure_mock(return_value=None)
    assert include_what_you_use.get_iwyu_command() is None


# ==============================================================================


def test_get_iwyu_invalid_init(mocker):
    get_iwyu_tool_command = mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_tool_command', return_value=None)
    mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_command', return_value=None)

    with pytest.raises(FileNotFoundError, match='path to iwyu-tool'):
        include_what_you_use.IWYUToolCmd(args=[])

    get_iwyu_tool_command.configure_mock(return_value='iwyu-tool')

    with pytest.raises(FileNotFoundError, match='path to include-what-you-use'):
        include_what_you_use.IWYUToolCmd(args=[])


def test_iwyu_command(mocker, setup_command):
    path = setup_command.compile_db_path
    call_process = setup_command.call_process
    returncode = setup_command.returncode

    # ----------------------------------

    mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_tool_command', return_value='iwyu-tool')
    mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_command', return_value='iwyu')
    mocker.patch('cmake_pc_hooks.include_what_you_use.IWYUToolCmd.get_version_str', return_value='0.19')

    call_process.configure_mock(
        return_value=mocker.Mock(
            stdout='has correct #includes/fwd-decls' if returncode == 0 else 'aaa', stderr='', returncode=returncode
        ),
    )

    command_name = 'iwyu-tool'
    args = [f'{command_name}', f'-B{path.parent}', *setup_command.cmd_args]

    command = include_what_you_use.IWYUToolCmd(args=args)
    assert f'-p={path}' in command.args

    run_command_default_assertions(
        command=command,
        **setup_command._asdict(),
    )


# ==============================================================================


def test_iwyu_main(mocker):
    argv = ['iwyu-tool', 'file.txt']
    mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_tool_command', return_value='iwyu-tool')
    mocker.patch('cmake_pc_hooks.include_what_you_use.get_iwyu_command', return_value='iwyu')
    command_main_asserts(mocker, 'include_what_you_use.IWYUToolCmd', include_what_you_use.main, argv)


# ==============================================================================
