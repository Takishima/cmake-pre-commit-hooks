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
from _test_utils import command_main_asserts

from cmake_pc_hooks import clang_format

# ==============================================================================


@pytest.mark.parametrize('format_success', [False, True])
def test_clang_format_command(mocker, tmp_path, format_success):
    mocker.patch('hooks.utils.Command.check_installed', return_value=True)

    return_values = []
    for char in (chr(n) for n in range(ord('a'), ord('z') + 1)):
        return_values.append(f'{char*3}'.encode())

    def _get_filelines(filename_str):  # noqa: ARG001
        if format_success:
            return [return_values[-1]]
        return [return_values.pop()]

    def _get_formatted_lines(filename_str):  # noqa: ARG001
        if format_success:
            return [return_values[-1]]
        return [return_values.pop()]

    mocker.patch('hooks.utils.FormatterCmd.get_filelines', side_effect=_get_filelines)
    mocker.patch('hooks.utils.FormatterCmd.get_formatted_lines', side_effect=_get_formatted_lines)
    mocker.patch('cmake_pc_hooks._utils.FormatterCmd.get_formatted_lines', side_effect=_get_formatted_lines)
    sys_exit = mocker.patch('sys.exit')

    command_name = 'clang-format'
    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')

    args = [f'{command_name}', '--no-diff', '-i', *[str(fname) for fname in file_list]]
    command = clang_format.ClangFormatCmd(args=args)
    assert command.no_diff_flag
    assert '--no-diff' not in command.args
    assert command.edit_in_place
    assert command.files == [str(fname) for fname in file_list]

    command.run()

    if format_success:
        sys_exit.assert_not_called()
    else:
        sys_exit.assert_called_once_with(1)


# ==============================================================================


def test_clang_format_main(mocker):
    argv = ['clang-format', '-i', 'file.txt']
    command_main_asserts(mocker, 'clang_format.ClangFormatCmd', clang_format.main, argv)


# ==============================================================================
