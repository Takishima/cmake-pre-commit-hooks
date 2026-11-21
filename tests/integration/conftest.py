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
Shared fixtures for the integration tests.

These tests run the real hooks (and the real linters, CMake and pre-commit) as sub-processes on throw-away copies of
the projects found in ``tests/cmake_good`` and ``tests/cmake_bad``. Nothing is ever written inside the repository.

Tests that need a tool that is not installed are skipped, unless that tool is listed in ``--required-tools`` in which
case they fail (this is what the CI does, so that a broken CI environment cannot silently skip everything).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from _integration import (
    HOOKS,
    PROJECTS_DIR,
    TOOL_EXECUTABLES,
    HookResult,
    copy_project,
    hook_command,
    is_installed,
    run_process,
)

_required_tools_key = pytest.StashKey[set]()


def pytest_addoption(parser):
    parser.addoption(
        '--required-tools',
        default='',
        help=(
            'Comma-separated list of tools that must be installed (or "all"). Tests needing a missing tool fail if it '
            f'is listed here and are skipped otherwise. Known tools: {", ".join(TOOL_EXECUTABLES)}'
        ),
    )


def pytest_configure(config):
    required = {name.strip() for name in config.getoption('--required-tools').split(',') if name.strip()}
    if 'all' in required:
        required = set(TOOL_EXECUTABLES)
    unknown = required - set(TOOL_EXECUTABLES)
    if unknown:
        msg = f'Unknown tool(s) passed to --required-tools: {", ".join(sorted(unknown))}'
        raise pytest.UsageError(msg)
    config.stash[_required_tools_key] = required


@pytest.fixture(scope='session')
def required_tools(pytestconfig) -> set[str]:
    """Tools listed in --required-tools."""
    return pytestconfig.stash[_required_tools_key]


@pytest.fixture(scope='session')
def require_tools(required_tools):
    """Return a function that skips (or fails, see --required-tools) the calling test if some tools are missing."""

    def _require_tools(*tools: str) -> None:
        for tool in tools:
            if is_installed(tool):
                continue
            msg = f'{tool} is not installed'
            if tool in required_tools:
                pytest.fail(f'{msg} but is listed in --required-tools', pytrace=False)
            pytest.skip(msg)

    return _require_tools


# ==============================================================================


@pytest.fixture
def run_hook(require_tools):
    """
    Return a function running a hook as pre-commit would: from the root of a project, with relative file names.

    The hook's default arguments for the test projects (see `HOOKS`) are *not* added automatically.
    """

    def _run_hook(hook_name: str, project: Path, *args: str | Path, env: dict | None = None) -> HookResult:
        hook = HOOKS[hook_name]
        require_tools(hook.name, *(['cmake'] if hook.uses_cmake else []))
        return run_process([*hook_command(hook_name), *args], cwd=project, env={**os.environ, **(env or {})})

    return _run_hook


# ==============================================================================


@pytest.fixture
def good_project(tmp_path) -> Path:
    """Copy of tests/cmake_good: all hooks are expected to pass on good.cpp."""
    return copy_project('good', tmp_path / 'good')


@pytest.fixture
def bad_project(tmp_path) -> Path:
    """Copy of tests/cmake_bad: all hooks are expected to fail on bad.cpp."""
    return copy_project('bad', tmp_path / 'bad')


@pytest.fixture
def mixed_project(tmp_path) -> Path:
    """Project made of both good.cpp and bad.cpp."""
    project = copy_project('good', tmp_path / 'mixed')
    shutil.copy(PROJECTS_DIR / 'cmake_bad' / 'bad.cpp', project)
    (project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.15)\n'
        'project(cmake_mixed LANGUAGES CXX)\n'
        'add_library(mylib STATIC good.cpp bad.cpp)\n',
        encoding='utf-8',
    )
    return project
