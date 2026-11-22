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

from cmake_pc_hooks import lizard
from cmake_pc_hooks._runner import HookRunner

from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_lizard_command(setup_command):
    path = setup_command.compile_db_path

    runner = HookRunner(lizard.HOOK, ['lizard', f'-B{path.parent}', *setup_command.cmd_args])
    assert not runner.args

    run_command_default_assertions(runner=runner, uses_cmake=setup_command.read_json_db, **setup_command._asdict())


def test_lizard_main(mocker):
    command_main_asserts(mocker, lizard, ['lizard', 'file.txt'])


# ==============================================================================
