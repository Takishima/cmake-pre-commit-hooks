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

from cmake_pc_hooks import cpplint
from cmake_pc_hooks._runner import HookRunner

from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_cpplint_command_passes_options_before_files(setup_command):
    path = setup_command.compile_db_path

    argv = ['cpplint', f'-B{path.parent}', '--filter=-legal/copyright', *setup_command.cmd_args]
    runner = HookRunner(cpplint.HOOK, argv)
    assert runner.args == ['--filter=-legal/copyright', '--verbose=0']

    run_command_default_assertions(runner=runner, uses_cmake=setup_command.read_json_db, **setup_command._asdict())

    for call in setup_command.call_process.call_args_list:
        assert call.args[0][:3] == ['cpplint', '--filter=-legal/copyright', '--verbose=0']
        assert set(call.args[0][3:]) <= set(runner.files)


def test_cpplint_verbose_not_overridden(mocker, tool):

    runner = HookRunner(cpplint.HOOK, ['cpplint', '--verbose=3', 'file.cpp'])
    assert runner.args == ['--verbose=3']
    assert runner.files == ['file.cpp']


def test_cpplint_main(mocker):
    command_main_asserts(mocker, cpplint, ['cpplint', 'file.txt'])


# ==============================================================================
