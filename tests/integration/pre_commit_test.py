# Copyright 2026 Damien Nguyen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
End-to-end tests: install the hooks using pre-commit and run them on a Git repository.

This validates what the unit tests cannot: the content of ``.pre-commit-hooks.yaml`` (hook ids, entry points, file
patterns), the packaging of the hooks and the way pre-commit passes the arguments and the file names to them.
"""

from __future__ import annotations

import json
import os
import re
import shutil

import pytest
from _integration import HOOKS, REPO_ROOT, WIN_CMAKE_ARGS, copy_project, is_installed, run_process

# Arguments for each of the hooks. NB: pre-commit appends the file names *after* those
HOOK_ARGS = {
    'clang-format': [],
    'clang-tidy': [*WIN_CMAKE_ARGS, *HOOKS['clang-tidy'].args, '--', '-std=c++11'],
    'cppcheck': [*WIN_CMAKE_ARGS],
    'cpplint': [],
    'include-what-you-use': [*WIN_CMAKE_ARGS],
    'lizard': ['-lcpp', '-w', *HOOKS['lizard'].args],
}


def git(*args: str, cwd) -> str:
    result = run_process(
        ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', '-c', 'commit.gpgsign=false', *args],
        cwd=cwd,
    )
    assert result.returncode == 0, result
    return result.stdout.strip()


@pytest.fixture(scope='session')
def hooks_repository(require_tools, tmp_path_factory):
    """
    Snapshot of the current state of the hooks repository, as a Git repository pre-commit can install from.

    Using a snapshot (instead of the repository itself) makes sure that the changes that have not yet been committed
    are being tested too.

    Returns:
        Tuple made of the path to the repository and of the revision to use.
    """
    require_tools('git', 'pre-commit')

    snapshot = tmp_path_factory.mktemp('hooks_repository')
    filenames = git('ls-files', '--cached', '--others', '--exclude-standard', '-z', cwd=REPO_ROOT).split('\0')
    for filename in filter(None, filenames):
        source = REPO_ROOT / filename
        if source.is_file():  # NB: files deleted but not yet committed are still listed
            destination = snapshot / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, destination)

    git('init', '--quiet', cwd=snapshot)
    git('add', '--all', cwd=snapshot)
    git('commit', '--quiet', '--no-verify', '-m', 'Snapshot', cwd=snapshot)
    return snapshot, git('rev-parse', 'HEAD', cwd=snapshot)


@pytest.fixture(scope='session')
def pre_commit_env(tmp_path_factory):
    """Environment variables for pre-commit: use a dedicated cache, so that the hooks are always freshly installed."""
    return {**os.environ, 'PRE_COMMIT_HOME': str(tmp_path_factory.mktemp('pre_commit_home'))}


def parse_pre_commit_output(output: str) -> dict[str, str]:
    """Extract the outcome (Passed, Failed, Skipped) of each of the hooks from the output of pre-commit."""
    return {
        match.group(1).strip(): match.group(2)
        for match in re.finditer(r'^(.+?)\.{3,}(?:\(.*\))?(Passed|Failed|Skipped)\s*$', output, flags=re.MULTILINE)
    }


@pytest.mark.parametrize(('project_name', 'expected'), [('good', 'Passed'), ('bad', 'Failed')])
def test_pre_commit_run(
    require_tools, required_tools, hooks_repository, pre_commit_env, tmp_path, project_name, expected
):
    require_tools('cmake')
    repo_path, revision = hooks_repository

    # NB: these must match the names found in .pre-commit-hooks.yaml
    hook_names = {
        'clang-format': 'clang-format',
        'clang-tidy': 'clang-tidy',
        'cppcheck': 'cppcheck (system)',
        'cpplint': 'cpplint',
        'include-what-you-use': 'include-what-you-use (system)',
        'lizard': 'lizard',
    }
    hook_ids = []
    for hook_id in hook_names:
        if is_installed(hook_id):
            hook_ids.append(hook_id)
        elif hook_id in required_tools:
            require_tools(hook_id)  # fails the test
        # else: simply leave that hook out, the other ones are still worth testing
    assert hook_ids

    project = copy_project(project_name, tmp_path / project_name)
    config = {
        'repos': [
            {
                'repo': str(repo_path),
                'rev': revision,
                'hooks': [{'id': hook_id, 'args': HOOK_ARGS[hook_id]} for hook_id in hook_ids],
            }
        ]
    }
    # NB: JSON is valid YAML
    (project / '.pre-commit-config.yaml').write_text(json.dumps(config, indent=2), encoding='utf-8')
    git('init', '--quiet', cwd=project)
    git('add', '--all', cwd=project)
    git('commit', '--quiet', '--no-verify', '-m', 'Initial commit', cwd=project)

    result = run_process(
        ['pre-commit', 'run', '--all-files', '--color=never'], cwd=project, env=pre_commit_env, timeout=1800
    )

    outcomes = parse_pre_commit_output(result.output)
    assert outcomes == {hook_names[hook_id]: expected for hook_id in hook_ids}, result
    assert result.returncode == (0 if expected == 'Passed' else 1), result
    # Linting must leave the working tree untouched (apart from the build directory)
    assert git('status', '--porcelain', '--untracked-files=no', cwd=project) == ''  # ruff: ignore[compare-to-empty-string]
