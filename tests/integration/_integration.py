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

"""Helpers shared by the integration tests."""

from __future__ import annotations

import shutil
import subprocess as sp
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT / 'tests'

# CMake arguments needed on Windows to get a compilation database (not supported by Visual Studio generators). They
# are passed on all platforms since they are no-ops everywhere but on Windows.
WIN_CMAKE_ARGS = ('--win=-GNinja', '--win=-DCMAKE_C_COMPILER=cl.exe', '--win=-DCMAKE_CXX_COMPILER=cl.exe')

# Executables required for each tool; each entry is a group of alternative names of which one must be found
TOOL_EXECUTABLES = {
    'clang-format': [('clang-format',)],
    'clang-tidy': [('clang-tidy',)],
    'cppcheck': [('cppcheck',)],
    'cpplint': [('cpplint',)],
    'include-what-you-use': [('include-what-you-use',), ('iwyu_tool.py', 'iwyu-tool', 'iwyu_tool')],
    'lizard': [('lizard',)],
    'cmake': [('cmake', 'cmake3')],
    'git': [('git',)],
    'pre-commit': [('pre-commit',)],
}


@dataclass(frozen=True)
class Hook:
    """Description of one of the hooks and of how it is expected to behave on the test projects."""

    name: str  # hook id (as in .pre-commit-hooks.yaml), also the name of the underlying tool
    uses_cmake: bool  # whether the hook needs a compilation database
    args: tuple[str, ...]  # extra arguments used when linting the test projects
    diagnostic: str  # text expected in the output when linting tests/cmake_bad/bad.cpp

    @property
    def script(self) -> str:
        """Name of the console script for this hook."""
        return f'cmake-pc-{self.name}-hook'


HOOKS = {
    hook.name: hook
    for hook in (
        Hook('clang-format', uses_cmake=False, args=(), diagnostic='+++ formatted'),
        Hook(
            'clang-tidy',
            uses_cmake=True,
            args=('--checks=-*,readability-magic-numbers', '--warnings-as-errors=*'),
            diagnostic='10 is a magic number',
        ),
        Hook('cppcheck', uses_cmake=True, args=(), diagnostic='[unusedVariable]'),
        Hook('cpplint', uses_cmake=False, args=(), diagnostic='[legal/copyright]'),
        Hook('include-what-you-use', uses_cmake=True, args=(), diagnostic='should remove these lines'),
        Hook('lizard', uses_cmake=False, args=('-C4',), diagnostic='factorial@'),
    )
}
CMAKE_HOOKS = [name for name, hook in HOOKS.items() if hook.uses_cmake]

# ==============================================================================


def is_installed(tool: str) -> bool:
    return all(any(shutil.which(name) for name in names) for names in TOOL_EXECUTABLES[tool])


@dataclass(frozen=True)
class HookResult:
    """Outcome of running a command."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """Standard output and standard error combined."""
        return self.stdout + self.stderr

    def __str__(self) -> str:
        return f'exit code: {self.returncode}\n--- stdout ---\n{self.stdout}\n--- stderr ---\n{self.stderr}'


def run_process(args: list, cwd: Path, env: dict | None = None, timeout: int = 600) -> HookResult:
    """Run a command and capture its output."""
    child = sp.run(  # ruff: ignore[subprocess-run-without-check]
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=timeout,
    )
    return HookResult(child.returncode, child.stdout, child.stderr)


def hook_command(hook_name: str) -> list[str]:
    """Locate the console script of a hook, preferring the one installed alongside the running Python interpreter."""
    script = HOOKS[hook_name].script
    path = shutil.which(script, path=sysconfig.get_path('scripts')) or shutil.which(script)
    if path is None:
        pytest.fail(
            f'Unable to locate {script}: install the package first (e.g. `python -m pip install -e .[test]`)',
            pytrace=False,
        )
    return [path]


def copy_project(name: str, destination: Path) -> Path:
    """Copy one of the test projects (tests/cmake_<name>) to some destination."""
    shutil.copytree(PROJECTS_DIR / f'cmake_{name}', destination)
    return destination


def cmake_configure(source_dir: Path, build_dir: Path) -> None:
    """Configure a project by calling CMake directly (ie. not through one of the hooks)."""
    cmake = shutil.which('cmake') or shutil.which('cmake3')
    args = ['-GNinja', '-DCMAKE_C_COMPILER=cl.exe', '-DCMAKE_CXX_COMPILER=cl.exe'] if sys.platform == 'win32' else []
    result = run_process(
        [cmake, '-S', source_dir, '-B', build_dir, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', *args], cwd=source_dir
    )
    assert result.returncode == 0, result
