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

from cmake_pc_hooks import clang_tidy
from cmake_pc_hooks._runner import HookRunner

import pytest
from _test_utils import command_main_asserts, run_command_default_assertions

# ==============================================================================


@pytest.mark.parametrize('stdout', ['', 'aaa'], ids=['<empty>', 'aaa'])
@pytest.mark.parametrize(
    'error_msg', [None, '1 error generated.', '2 errors generated.'], ids=['<empty>', '1_error', '2_errors']
)
def test_clang_tidy_command(mocker, setup_command, stdout, error_msg):
    path = setup_command.compile_db_path
    returncode = setup_command.returncode
    setup_command.call_process.configure_mock(
        return_value=mocker.Mock(stdout=stdout, stderr=f'{error_msg or ""} aaa\nbbb', returncode=returncode)
    )

    runner = HookRunner(clang_tidy.HOOK, ['clang-tidy', f'-B{path.parent}', *setup_command.cmd_args])

    if not setup_command.no_cmake_configure:
        assert f'-p={path}' in runner.args

    run_command_default_assertions(
        runner=runner,
        exit_success=returncode == 0 and (error_msg is None or not stdout),
        **setup_command._asdict(),
    )


@pytest.mark.parametrize(
    ('stdout', 'stderr', 'shown_stderr'),
    [
        ('', '10 warnings generated.', ''),
        ('warning: foo', 'Suppressed 3 warnings (3 in non-user code).', ''),
        ('warning: foo', '10 warnings generated.', '10 warnings generated.'),
    ],
    ids=['no_stdout', 'non_user_code', 'user_code'],
)
def test_clang_tidy_hides_stderr_about_system_files(mocker, stdout, stderr, shown_stderr):
    result = mocker.Mock(stdout=stdout, stderr=stderr, returncode=0)
    assert not clang_tidy.has_errors(result)
    assert result.stderr == shown_stderr


def test_clang_tidy_main(mocker):
    command_main_asserts(mocker, clang_tidy, ['clang-tidy', 'file.txt'])


# ==============================================================================
