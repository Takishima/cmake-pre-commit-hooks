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

"""Test the way the hooks drive CMake: build directory selection, options forwarding, configuration files, etc."""

from __future__ import annotations

import json
import os
import platform
import subprocess as sp
from pathlib import Path

import pytest
from _integration import HOOKS, WIN_CMAKE_ARGS, cmake_configure, hook_command, is_installed

DEFAULT_BUILD_DIR = '.cmake_build'
MAGIC_NUMBER = HOOKS['clang-tidy'].diagnostic


@pytest.fixture
def run_tidy(run_hook):
    """
    Run the clang-tidy hook, which is the one used to exercise all the CMake related functionalities.

    The checks are set up so that the hook fails if (and only if) a magic number is found in the files being linted.
    """

    def _run_tidy(project: Path, *args: str | Path, env: dict | None = None):
        return run_hook('clang-tidy', project, *WIN_CMAKE_ARGS, *HOOKS['clang-tidy'].args, *args, env=env)

    return _run_tidy


def has_compile_db(build_dir: Path) -> bool:
    return (build_dir / 'compile_commands.json').is_file()


def cmake_cache(build_dir: Path) -> dict[str, str]:
    """Read the variables stored in the CMake cache of some build directory."""
    cache = {}
    for line in (build_dir / 'CMakeCache.txt').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith(('#', '//')):
            name, _, value = line.partition('=')
            cache[name.partition(':')[0]] = value
    return cache


# ==============================================================================
# Build directory selection


def test_default_build_dir(run_tidy, good_project):
    result = run_tidy(good_project, 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / DEFAULT_BUILD_DIR)


@pytest.mark.parametrize('absolute', [False, True], ids=['relative', 'absolute'])
def test_explicit_build_dir(run_tidy, good_project, tmp_path, absolute):
    build_dir = tmp_path / 'out_of_tree' if absolute else Path('my_build')
    result = run_tidy(good_project, '-B', build_dir, 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / build_dir)
    assert not (good_project / DEFAULT_BUILD_DIR).exists()


def test_source_dir(run_tidy, good_project, tmp_path):
    """Run the hook from a directory that is not the one containing the top-level CMakeLists.txt."""
    result = run_tidy(tmp_path, '-S', 'good', '-B', 'build', 'good/good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(tmp_path / 'build')
    assert Path(cmake_cache(tmp_path / 'build')['CMAKE_HOME_DIRECTORY']).samefile(good_project)


def test_first_build_dir_is_used_if_none_configured(run_tidy, good_project):
    result = run_tidy(good_project, '-B', 'first', '-B', 'second', 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'first')
    assert not (good_project / 'second').exists()


def test_already_configured_build_dir_is_preferred(run_tidy, require_tools, good_project):
    require_tools('cmake')
    cmake_configure(good_project, good_project / 'second')

    result = run_tidy(good_project, '-B', 'first', '-B', 'second', 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'second')
    assert not (good_project / 'first').exists()


def test_automatic_build_dir_discovery(run_tidy, require_tools, good_project):
    require_tools('cmake')
    cmake_configure(good_project, good_project / 'existing_build')

    result = run_tidy(good_project, 'good.cpp')
    assert result.returncode == 0, result
    assert not (good_project / DEFAULT_BUILD_DIR).exists()

    result = run_tidy(good_project, '--no-automatic-discovery', 'good.cpp')
    assert result.returncode == 0, result
    assert has_compile_db(good_project / DEFAULT_BUILD_DIR)


def test_no_cmake_configure(run_tidy, require_tools, good_project):
    require_tools('cmake')

    # No build directory to be found: CMake must not be called, but the linter still runs
    result = run_tidy(good_project, '--no-cmake-configure', '-B', 'build', 'good.cpp')
    assert result.returncode == 0, result
    assert not (good_project / 'build').exists()
    assert not (good_project / DEFAULT_BUILD_DIR).exists()

    # Existing build directory: it must be used as-is
    cmake_configure(good_project, good_project / 'build')
    cache = (good_project / 'build' / 'CMakeCache.txt').read_bytes()
    result = run_tidy(good_project, '--no-cmake-configure', '-B', 'build', '-DNEVER_SEEN_BY_CMAKE=1', 'good.cpp')
    assert result.returncode == 0, result
    assert (good_project / 'build' / 'CMakeCache.txt').read_bytes() == cache


@pytest.mark.parametrize('clean', [False, True], ids=['no_clean', 'clean'])
def test_clean(run_tidy, good_project, clean):
    build_dir = good_project / 'build'
    stale_file = build_dir / 'stale.txt'
    stale_dir_file = build_dir / 'stale_dir' / 'stale.txt'
    stale_dir_file.parent.mkdir(parents=True)
    stale_file.write_text('stale', encoding='utf-8')
    stale_dir_file.write_text('stale', encoding='utf-8')

    result = run_tidy(good_project, '-B', 'build', *(['--clean'] if clean else []), 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(build_dir)
    assert stale_file.exists() != clean
    assert stale_dir_file.exists() != clean


# ==============================================================================
# CMake options


def test_cmake_options_are_forwarded(run_tidy, good_project):
    result = run_tidy(
        good_project,
        '-B',
        'build',
        '-DFIRST_OPTION=one',
        '-DSECOND_OPTION:STRING=two',
        'good.cpp',
    )

    assert result.returncode == 0, result
    cache = cmake_cache(good_project / 'build')
    assert cache['FIRST_OPTION'] == 'one'
    assert cache['SECOND_OPTION'] == 'two'
    assert cache['CMAKE_EXPORT_COMPILE_COMMANDS'] == 'ON'


def test_developer_warnings_can_be_suppressed(run_tidy, good_project):
    (good_project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.15)\n'
        'project(cmake_dev_warning LANGUAGES CXX)\n'
        'message(AUTHOR_WARNING "This is a developer warning")\n'
        'add_library(mylib STATIC good.cpp)\n',
        encoding='utf-8',
    )
    # The output of CMake is only shown if the configure step fails or when debugging
    env = {'LOGLEVEL': 'DEBUG'}

    result = run_tidy(good_project, '-B', 'build_with_warnings', 'good.cpp', env=env)
    assert result.returncode == 0, result
    assert 'This is a developer warning' in result.output, result

    # NB: recent versions of CMake reject unknown warning categories while older ones silently ignore them, hence
    #     the need to look at the output
    result = run_tidy(good_project, '-B', 'build_without_warnings', '-Wno-dev', 'good.cpp', env=env)
    assert result.returncode == 0, result
    assert 'This is a developer warning' not in result.output, result


def test_cmake_defines_reach_the_linter(run_tidy, good_project):
    """Make sure the linter really uses the compilation database generated by CMake."""
    (good_project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.15)\n'
        'project(cmake_defines LANGUAGES CXX)\n'
        'add_library(mylib STATIC good.cpp)\n'
        'if(WITH_MAGIC)\n'
        '  target_compile_definitions(mylib PRIVATE WITH_MAGIC=1)\n'
        'endif()\n',
        encoding='utf-8',
    )
    (good_project / 'good.cpp').write_text(
        '#ifdef WITH_MAGIC\nint magic() { return 10; }\n#endif\nint main() { return 0; }\n', encoding='utf-8'
    )

    result = run_tidy(good_project, '-B', 'build_without', 'good.cpp')
    assert result.returncode == 0, result

    result = run_tidy(good_project, '-B', 'build_with', '-DWITH_MAGIC=ON', 'good.cpp')
    assert result.returncode == 1, result
    assert MAGIC_NUMBER in result.output, result


def test_platform_specific_options(run_tidy, good_project):
    result = run_tidy(
        good_project,
        '-B',
        'build',
        '--unix=-DFROM_UNIX=1',
        '--linux=-DFROM_LINUX=1',
        '--mac=-DFROM_MAC=1',
        '--win=-DFROM_WIN=1',
        'good.cpp',
    )

    assert result.returncode == 0, result
    expected = {
        'Linux': {'FROM_UNIX', 'FROM_LINUX'},
        'Darwin': {'FROM_UNIX', 'FROM_MAC'},
        'Windows': {'FROM_WIN'},
    }[platform.system()]
    assert {name for name in cmake_cache(good_project / 'build') if name.startswith('FROM_')} == expected


def test_preset(run_tidy, good_project):
    presets = {
        'version': 3,
        'configurePresets': [{'name': 'my-preset', 'cacheVariables': {'FROM_PRESET': 'yes'}}],
    }
    (good_project / 'CMakePresets.json').write_text(json.dumps(presets), encoding='utf-8')

    result = run_tidy(good_project, '-B', 'build', '--preset=my-preset', 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'build')
    assert cmake_cache(good_project / 'build')['FROM_PRESET'] == 'yes'


def test_preset_requires_build_dir(run_tidy, good_project):
    result = run_tidy(good_project, '--preset=my-preset', 'good.cpp')

    assert result.returncode != 0, result
    assert 'You *must* specify -B|--build-dir if you pass --preset' in result.output, result


def test_detect_configured_files(run_tidy, good_project):
    """Files generated by configure_file() are linted too if --detect-configured-files is passed."""
    (good_project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.15)\n'
        'project(cmake_configured LANGUAGES CXX)\n'
        'set(ANSWER 10)\n'
        'configure_file(answer.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/answer.cpp @ONLY)\n'
        'add_library(mylib STATIC good.cpp ${CMAKE_CURRENT_BINARY_DIR}/answer.cpp)\n',
        encoding='utf-8',
    )
    (good_project / 'answer.cpp.in').write_text('int answer() { return @ANSWER@; }\n', encoding='utf-8')

    result = run_tidy(good_project, '-B', 'build', 'good.cpp')
    assert result.returncode == 0, result

    result = run_tidy(good_project, '-B', 'build', '--detect-configured-files', 'good.cpp')
    assert result.returncode == 1, result
    assert MAGIC_NUMBER in result.output, result
    assert 'answer.cpp' in result.output, result


# ==============================================================================
# Error handling


def test_invalid_source_dir(run_tidy, good_project):
    result = run_tidy(good_project, '-S', 'does_not_exist', 'good.cpp')

    assert result.returncode == 2, result
    assert "Directory 'does_not_exist' does not exist" in result.output, result
    assert 'Traceback (most recent call last)' not in result.output, result
    assert not (good_project / 'does_not_exist').exists()


def test_cmake_configure_failure(run_tidy, good_project):
    (good_project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.15)\n'
        'project(cmake_broken LANGUAGES CXX)\n'
        'message(FATAL_ERROR "This project is broken")\n',
        encoding='utf-8',
    )

    result = run_tidy(good_project, '-B', 'build', 'good.cpp')

    assert result.returncode != 0, result
    assert 'This project is broken' in result.output, result
    assert 'CMake configure step failed' in result.output, result
    assert 'Traceback (most recent call last)' not in result.output, result


# ==============================================================================
# TOML configuration


def test_dump_toml(run_tidy, good_project):
    result = run_tidy(good_project, '-B', 'build', '-DOPTION=1', '--all-at-once', '--dump-toml', 'good.cpp')

    assert result.returncode == 0, result
    assert 'build_dir = ["build"]' in result.stdout
    assert 'defines = ["OPTION=1"]' in result.stdout
    assert 'all_at_once = true' in result.stdout
    # Dumping the configuration must not run anything
    assert not (good_project / 'build').exists()


@pytest.mark.parametrize(
    ('filename', 'header', 'extra_args'),
    [
        ('pyproject.toml', '[tool.cmake_pc_hooks]\n', []),
        ('cmake_pc_hooks.toml', '', []),
        ('custom.toml', '', ['--hooks-config=custom.toml']),
    ],
    ids=['pyproject', 'default_config', 'explicit_config'],
)
def test_toml_config(run_tidy, good_project, filename, header, extra_args):
    (good_project / filename).write_text(
        f'{header}build_dir = ["from_toml"]\ndefines = ["FROM_TOML=1"]\n', encoding='utf-8'
    )

    result = run_tidy(good_project, *extra_args, 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'from_toml')
    assert cmake_cache(good_project / 'from_toml')['FROM_TOML'] == '1'
    assert not (good_project / DEFAULT_BUILD_DIR).exists()


def test_cli_overrides_explicit_toml_config(run_tidy, good_project):
    (good_project / 'custom.toml').write_text('build_dir = ["from_toml"]\n', encoding='utf-8')

    result = run_tidy(good_project, '--hooks-config=custom.toml', '-B', 'from_cli', 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'from_cli')
    assert not (good_project / 'from_toml').exists()


def test_invalid_toml_config(run_tidy, good_project):
    (good_project / 'cmake_pc_hooks.toml').write_text('not_an_option = true\n', encoding='utf-8')

    result = run_tidy(good_project, 'good.cpp')

    assert result.returncode != 0, result
    assert 'unknown option "not_an_option" in cmake_pc_hooks.toml' in result.output, result
    assert 'Traceback (most recent call last)' not in result.output, result


def test_toml_config_for_one_hook(run_tidy, good_project):
    (good_project / 'cmake_pc_hooks.toml').write_text(
        'build_dir = ["common"]\n[clang-tidy]\nbuild_dir = ["tidy"]\n[cppcheck]\nbuild_dir = ["cppcheck"]\n',
        encoding='utf-8',
    )

    result = run_tidy(good_project, 'good.cpp')

    assert result.returncode == 0, result
    assert has_compile_db(good_project / 'tidy')
    assert not (good_project / 'common').exists()
    assert not (good_project / 'cppcheck').exists()


def test_config_option_is_passed_to_the_tool(run_hook, bad_project):
    config = '{Checks: "-*,readability-magic-numbers", WarningsAsErrors: "*"}'

    result = run_hook('clang-tidy', bad_project, *WIN_CMAKE_ARGS, '-B', 'build', f'--config={config}', 'bad.cpp')

    assert result.returncode == 1, result
    assert '10 is a magic number' in result.output, result


# ==============================================================================
# Concurrency


def test_concurrent_hooks_share_build_dir(require_tools, mixed_project):
    """
    Run several hooks at once on a pristine build directory, as pre-commit does when given many files.

    Only one of the processes may run CMake, with all the others waiting for the compilation database to be ready.
    """
    require_tools('cmake')
    hook_names = [name for name in ('clang-tidy', 'cppcheck', 'include-what-you-use') if is_installed(name)]
    if not hook_names:
        pytest.skip('none of the hooks relying on CMake can be run')

    n_processes = 6
    children = []
    for idx in range(n_processes):
        hook = HOOKS[hook_names[idx % len(hook_names)]]
        children.append(
            (
                hook,
                sp.Popen(
                    [*hook_command(hook.name), '-B', 'build', *WIN_CMAKE_ARGS, *hook.args, 'good.cpp'],
                    cwd=mixed_project,
                    env={**os.environ, 'LOGLEVEL': 'DEBUG'},
                    stdout=sp.PIPE,
                    stderr=sp.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                ),
            )
        )

    outputs = []
    try:
        for hook, child in children:
            output, _ = child.communicate(timeout=600)
            outputs.append(output)
            assert child.returncode == 0, f'{hook.name} failed:\n{output}'
    finally:
        for _, child in children:
            if child.poll() is None:
                child.kill()

    assert has_compile_db(mixed_project / 'build')
    assert sum('is running CMake configure' in output for output in outputs) >= 1
