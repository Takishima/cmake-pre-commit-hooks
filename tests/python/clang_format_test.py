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

from cmake_pc_hooks import clang_format
from cmake_pc_hooks._runner import HookRunner

from _test_utils import command_main_asserts

# ==============================================================================


def test_clang_format_hook(mocker, tool, tmp_path):
    sys_exit = mocker.patch('sys.exit')
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process', return_value=mocker.Mock(stdout='a\n', stderr='', returncode=0)
    )
    file = tmp_path / 'file.cpp'
    file.write_bytes(b'b\n')

    runner = HookRunner(clang_format.HOOK, ['clang-format', '--no-diff', str(file)])
    assert runner.cmake is None
    runner.run()

    call_process.assert_called_once_with(['clang-format', str(file)])
    sys_exit.assert_called_once_with(1)


def test_clang_format_main(mocker):
    command_main_asserts(mocker, clang_format, ['clang-format', '-i', 'file.txt'])


# ==============================================================================
