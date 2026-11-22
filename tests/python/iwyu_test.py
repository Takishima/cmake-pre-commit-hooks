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

from cmake_pc_hooks import include_what_you_use
from cmake_pc_hooks._runner import HookRunner

import pytest
from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


def test_iwyu_command(mocker, setup_command):
    path = setup_command.compile_db_path
    returncode = setup_command.returncode
    setup_command.call_process.configure_mock(
        return_value=mocker.Mock(
            stdout='has correct #includes/fwd-decls' if returncode == 0 else 'aaa', stderr='', returncode=returncode
        ),
    )

    runner = HookRunner(include_what_you_use.HOOK, ['iwyu-tool', f'-B{path.parent}', *setup_command.cmd_args])
    assert runner.command == 'iwyu_tool.py'
    if not setup_command.no_cmake_configure:
        assert f'-p={path}' in runner.args

    run_command_default_assertions(runner=runner, **setup_command._asdict())


@pytest.mark.parametrize(
    ('stdout', 'has_errors'),
    [
        ('', False),
        ('(good.cpp has correct #includes/fwd-decls)', False),
        ('bad.cpp should add these lines:\n\nbad.cpp should remove these lines:\n- #include <string>\n', True),
        (
            (
                '(good.cpp has correct #includes/fwd-decls)\n'
                'bad.cpp should add these lines:\n\nbad.cpp should remove these lines:\n- #include <string>\n'
            ),
            True,
        ),
        ('some unexpected output', True),
    ],
    ids=['empty', 'correct', 'incorrect', 'correct_and_incorrect', 'other'],
)
def test_iwyu_has_errors(mocker, stdout, has_errors):
    assert include_what_you_use.has_errors(mocker.Mock(stdout=stdout, stderr='', returncode=1)) == has_errors


def test_iwyu_version_is_read_from_iwyu(mocker, tool):
    mocker.patch('cmake_pc_hooks._cmake.locate.get_cmake_command', return_value=['cmake'])
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        return_value=mocker.Mock(stdout='include-what-you-use 0.21 based on clang', stderr='', returncode=0),
    )

    HookRunner(include_what_you_use.HOOK, ['iwyu-tool', '--require-version=0.21', 'file.cpp'])

    call_process.assert_called_once_with(['include-what-you-use', '--version'])


def test_iwyu_main(mocker):
    command_main_asserts(mocker, include_what_you_use, ['iwyu-tool', 'file.txt'])


# ==============================================================================
