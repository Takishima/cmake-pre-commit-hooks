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

"""Run each of the hooks on real source files, using the real linters."""

from __future__ import annotations

import json

import pytest
from _integration import CMAKE_HOOKS, HOOKS, PROJECTS_DIR, WIN_CMAKE_ARGS

BUILD_DIR = 'build'


def hook_args(hook_name: str) -> list[str]:
    """Arguments to pass to a hook in order to lint one of the test projects."""
    hook = HOOKS[hook_name]
    cmake_args = ['-B', BUILD_DIR, *WIN_CMAKE_ARGS] if hook.uses_cmake else []
    return [*cmake_args, *hook.args]


def assert_no_crash(result) -> None:
    """Make sure a hook failure is a linting failure and not the hook itself blowing up."""
    assert 'Traceback (most recent call last)' not in result.output, result


def assert_compile_db(build_dir, *filenames: str) -> None:
    """Make sure a compilation database listing the given files was generated."""
    compile_db = build_dir / 'compile_commands.json'
    assert compile_db.is_file()
    entries = json.loads(compile_db.read_text(encoding='utf-8'))
    assert sorted(entry['file'].replace('\\', '/').rsplit('/', 1)[-1] for entry in entries) == sorted(filenames)


# ==============================================================================


@pytest.mark.parametrize('hook_name', HOOKS)
def test_hook_passes_on_good_code(run_hook, good_project, hook_name):
    result = run_hook(hook_name, good_project, *hook_args(hook_name), 'good.cpp')

    assert result.returncode == 0, result
    if HOOKS[hook_name].uses_cmake:
        assert_compile_db(good_project / BUILD_DIR, 'good.cpp')
    else:
        assert not (good_project / BUILD_DIR).exists()


@pytest.mark.parametrize('hook_name', HOOKS)
def test_hook_fails_on_bad_code(run_hook, bad_project, hook_name):
    result = run_hook(hook_name, bad_project, *hook_args(hook_name), 'bad.cpp')

    assert result.returncode == 1, result
    assert_no_crash(result)
    assert HOOKS[hook_name].diagnostic in result.output, result
    if HOOKS[hook_name].uses_cmake:
        assert_compile_db(bad_project / BUILD_DIR, 'bad.cpp')
    # None of the hooks may modify the files unless explicitly asked to
    assert (bad_project / 'bad.cpp').read_bytes() == (PROJECTS_DIR / 'cmake_bad' / 'bad.cpp').read_bytes()


@pytest.mark.parametrize('filenames', [('good.cpp', 'bad.cpp'), ('bad.cpp', 'good.cpp')], ids=['bad_last', 'bad_first'])
@pytest.mark.parametrize('all_at_once', [False, True], ids=['one_by_one', 'all_at_once'])
@pytest.mark.parametrize('hook_name', HOOKS)
def test_hook_with_multiple_files(run_hook, mixed_project, hook_name, all_at_once, filenames):
    """A single bad file must make the hook fail, wherever it is in the list of files."""
    if all_at_once and hook_name == 'cpplint':
        pytest.skip('the cpplint hook does not support --all-at-once')

    extra_args = ['--all-at-once'] if all_at_once else []
    result = run_hook(hook_name, mixed_project, *hook_args(hook_name), *extra_args, *filenames)

    assert result.returncode == 1, result
    assert_no_crash(result)
    assert HOOKS[hook_name].diagnostic in result.output, result


@pytest.mark.parametrize('hook_name', CMAKE_HOOKS)
def test_hook_only_reports_requested_files(run_hook, mixed_project, hook_name):
    # bad.cpp is part of the project (and of the compilation database) but we are not asking for it to be linted
    result = run_hook(hook_name, mixed_project, *hook_args(hook_name), 'good.cpp')

    assert result.returncode == 0, result
    assert_compile_db(mixed_project / BUILD_DIR, 'good.cpp', 'bad.cpp')
    assert HOOKS[hook_name].diagnostic not in result.output, result


@pytest.mark.parametrize('hook_name', ['clang-tidy', 'cppcheck', 'lizard'])
def test_read_json_db(run_hook, mixed_project, hook_name):
    """Files listed in the compilation database are linted in addition to those passed on the command line."""
    # lizard never runs CMake unless --read-json-db is passed, which is why -B is passed explicitly here
    args = ['-B', BUILD_DIR, *WIN_CMAKE_ARGS, *HOOKS[hook_name].args, 'good.cpp']

    if HOOKS[hook_name].uses_cmake:
        result = run_hook(hook_name, mixed_project, *args)
        assert result.returncode == 0, result

    result = run_hook(hook_name, mixed_project, '--read-json-db', *args)
    assert result.returncode == 1, result
    assert_no_crash(result)
    assert HOOKS[hook_name].diagnostic in result.output, result


# ==============================================================================


def test_clang_format_fix_in_place(run_hook, bad_project):
    source = bad_project / 'bad.cpp'
    original = source.read_text(encoding='utf-8')

    # Like most fixers, the hook reports a failure when it modifies a file...
    result = run_hook('clang-format', bad_project, '-i', 'bad.cpp')
    assert result.returncode == 1, result
    assert source.read_text(encoding='utf-8') != original

    # ... and succeeds on the next run
    fixed = source.read_text(encoding='utf-8')
    result = run_hook('clang-format', bad_project, '-i', 'bad.cpp')
    assert result.returncode == 0, result
    assert source.read_text(encoding='utf-8') == fixed


def test_clang_format_style_from_file(run_hook, bad_project):
    """Arguments unknown to the hook are forwarded to the tool, which then picks up its own configuration file."""
    result = run_hook('clang-format', bad_project, '-i', '--style=file', 'bad.cpp')
    assert result.returncode == 1, result
    default_style = (bad_project / 'bad.cpp').read_text(encoding='utf-8')

    (bad_project / 'bad.cpp').write_bytes((PROJECTS_DIR / 'cmake_bad' / 'bad.cpp').read_bytes())
    (bad_project / '.clang-format').write_text('BasedOnStyle: LLVM\nIndentWidth: 8\n', encoding='utf-8')
    result = run_hook('clang-format', bad_project, '-i', '--style=file', 'bad.cpp')
    assert result.returncode == 1, result
    assert (bad_project / 'bad.cpp').read_text(encoding='utf-8') != default_style
    assert '\n        int i;\n' in (bad_project / 'bad.cpp').read_text(encoding='utf-8')


def test_clang_tidy_compiler_args_after_double_dash(run_hook, bad_project):
    """Pre-commit appends the file names after everything else, including after the compiler arguments."""
    args = [*hook_args('clang-tidy'), '--', '-std=c++11', '-DSOME_MACRO=1']
    result = run_hook('clang-tidy', bad_project, *args, 'bad.cpp')

    assert result.returncode == 1, result
    assert_no_crash(result)
    assert HOOKS['clang-tidy'].diagnostic in result.output, result


def test_clang_tidy_warnings_are_not_errors(run_hook, bad_project):
    result = run_hook(
        'clang-tidy', bad_project, '-B', BUILD_DIR, *WIN_CMAKE_ARGS, '--checks=-*,readability-*', 'bad.cpp'
    )

    assert result.returncode == 0, result
    assert HOOKS['clang-tidy'].diagnostic in result.output, result


def test_cppcheck_arguments_are_forwarded(run_hook, bad_project):
    result = run_hook(
        'cppcheck',
        bad_project,
        *hook_args('cppcheck'),
        '--suppress=unusedVariable',
        '--suppress=unusedFunction',
        '--suppress=missingIncludeSystem',
        'bad.cpp',
    )

    assert result.returncode == 0, result
    assert HOOKS['cppcheck'].diagnostic not in result.output, result


def test_cpplint_arguments_are_forwarded(run_hook, bad_project):
    result = run_hook('cpplint', bad_project, '--filter=-legal,-whitespace,-readability,-runtime', 'bad.cpp')

    assert result.returncode == 0, result


def test_lizard_threshold(run_hook, bad_project):
    # factorial() has a cyclomatic complexity of 5, which is fine with lizard's default threshold (15)...
    assert run_hook('lizard', bad_project, 'bad.cpp').returncode == 0
    assert run_hook('lizard', bad_project, '-C5', 'bad.cpp').returncode == 0
    # ... but not with a lower one
    result = run_hook('lizard', bad_project, '-C4', 'bad.cpp')
    assert result.returncode == 1, result
    assert HOOKS['lizard'].diagnostic in result.output, result


# ==============================================================================


@pytest.mark.parametrize('hook_name', ['clang-format', 'clang-tidy', 'cppcheck', 'include-what-you-use'])
def test_version_mismatch(run_hook, good_project, hook_name):
    result = run_hook(hook_name, good_project, *hook_args(hook_name), '--version=0.0.1', 'good.cpp')

    assert result.returncode == 1, result
    assert 'Expected version: 0.0.1' in result.output, result
