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

from cmake_pc_hooks import cppcheck
from cmake_pc_hooks._runner import HookRunner

import pytest
from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_cppcheck_command(setup_command):
    path = setup_command.compile_db_path

    runner = HookRunner(cppcheck.HOOK, ['cppcheck', f'-B{path.parent}', *setup_command.cmd_args])
    assert runner.args[:3] == ['-q', '--error-exitcode=1', '--enable=all']
    if not setup_command.no_cmake_configure:
        assert f'--project={path}' in runner.args

    run_command_default_assertions(runner=runner, **setup_command._asdict())

    for call in setup_command.call_process.call_args_list:
        file_args = [arg for arg in call.args[0] if arg.startswith('--file-filter=')]
        assert len(file_args) == (len(runner.files) if setup_command.all_at_once else 1)
        assert not any(arg in runner.files for arg in call.args[0])


def test_cppcheck_file_filter():
    assert cppcheck.file_filter('/path/to/src/file.cpp') == '--file-filter=*src/file.cpp'


@pytest.mark.parametrize('returncode', [0, 1])
def test_cppcheck_hides_useless_error(mocker, returncode):
    result = mocker.Mock(
        stdout='', stderr='aaa\nnofile:0: Cppcheck cannot find all the include files\nbbb\n', returncode=returncode
    )
    assert cppcheck.has_errors(result) == bool(returncode)
    assert result.stderr == 'aaa\nbbb\n'


def test_cppcheck_main(mocker):
    command_main_asserts(mocker, cppcheck, ['cppcheck', 'file.txt'])


# ==============================================================================
