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

"""Code shared by all hooks to run their tool."""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from . import _call_process, _cli
from ._cmake import CMakeCommand, CMakeOptions

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import SimpleNamespace

    from ._hook import Hook

_LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=_LOGLEVEL, format='%(levelname)-5s:cmake-pc-hooks:%(message)s')

log = logging.getLogger(__name__)

WEBSITE = 'https://github.com/Takishima/cmake-pre-commit-hooks#using-the-hooks'


class CMakePresetError(click.UsageError):
    """Exception raised if a command line incompatibility with --preset is detected."""

    def __init__(self) -> None:
        """Initialize a CMakePresetError."""
        super().__init__('You *must* specify -B|--build-dir if you pass --preset as a CMake argument!')


def find_executable(names: Sequence[str]) -> str | None:
    """Return the path to the first executable found on the PATH among a list of names."""
    for name in names:
        path = shutil.which(name)
        if path:
            log.debug('found %s at %s', name, path)
            return path
    return None


def _read_compile_commands_json(compile_db: Path) -> list[str]:
    """Read a JSON compile database and return the list of files contained within."""
    if compile_db.exists():
        with compile_db.open(encoding='utf-8') as fd:
            data = json.load(fd)
        return [entry['file'] for entry in data]
    return []


def _resolve_compilation_database(
    cmake_build_dir: Path | None, build_dir_list: list[str], *, will_configure: bool
) -> Path | None:
    """
    Locate the compilation database.

    If CMake is going to run, the result is the file it will create in its build directory. Otherwise, it is the
    first existing file found in the CMake build directory or else in a list of directories.
    """
    if cmake_build_dir and will_configure:
        return cmake_build_dir / CMakeCommand.COMPILE_DB_NAME

    for build_dir in (*([cmake_build_dir] if cmake_build_dir else []), *(Path(path) for path in build_dir_list)):
        path = build_dir / CMakeCommand.COMPILE_DB_NAME
        if path.exists():
            log.debug('Located valid compilation database at: %s', path)
            return path
    log.debug('No valid compilation database located')
    return None


class HookRunner:
    """Run the tool of a hook."""

    def __init__(self, hook: Hook, argv: list[str]) -> None:
        """Parse the command line `argv` (which starts with the program name) and prepare the call to the tool."""
        self.hook = hook
        options, self.args, self.files = _cli.parse_args(hook.name, argv[1:])
        if options.preset and not options.build_dir:
            raise CMakePresetError

        self.compiler_args = []
        self.all_at_once = options.all_at_once
        self.read_json_db = options.read_json_db
        self.clean_build = options.clean

        self.command = find_executable(hook.executables or (hook.name,))
        if self.command is None:
            self._fail(
                f'{hook.name} not found',
                f'Make sure {hook.name} is installed and on your PATH.\nFor more info: {WEBSITE}',
            )
        if options.version:
            self._check_version(options.version)

        if hook.double_dash:
            self._split_compiler_args()
        for arg in hook.default_args:
            self._add_if_missing(arg)

        self.cmake = None
        self.compile_db = None
        if hook.compile_db_arg or self.read_json_db:
            self._setup_cmake(options)

    def run(self) -> None:
        """Run the tool on the files and exit with an error if it failed on any of them."""
        if self.cmake:
            self.cmake.configure(self.hook.name, clean_build=self.clean_build)
            self.files.extend(self.cmake.cmake_configured_files)
            if self.read_json_db and self.compile_db:
                self.files.extend(set(_read_compile_commands_json(self.compile_db)) - set(self.files))

        if not self.files and not self.all_at_once:
            log.error('No files to process!')
            sys.exit(1)

        if self._format() if self.hook.formatter else self._analyze():
            sys.exit(1)

    def _setup_cmake(self, options: SimpleNamespace) -> None:
        """Set up CMake and tell the tool where the compilation database is."""
        self.cmake = CMakeCommand(CMakeOptions.from_namespace(options))
        self.compile_db = _resolve_compilation_database(
            self.cmake.build_dir,
            ['.', CMakeCommand.DEFAULT_BUILD_DIR, *options.build_dir],
            will_configure=not options.no_cmake_configure,
        )
        if self.hook.compile_db_arg and self.compile_db:
            self._add_if_missing(self.hook.compile_db_arg.format(self.compile_db))

    def _analyze(self) -> bool:
        """Run the tool once per file (or once for all files) and return whether any call failed."""
        failed = False
        for filenames in [self.files] if self.all_at_once else [[filename] for filename in self.files]:
            file_args = [self.hook.file_arg(filename) for filename in filenames]
            if self.hook.options_first:
                command = [self.command, *self.args, *file_args]
            else:
                command = [self.command, *file_args, *self.args, *self.compiler_args]
            result = _call_process.call_process(command)
            failed |= self.hook.check(result)
            result.to_stdout_and_stderr()
        return failed

    def _format(self) -> bool:
        """
        Run the formatter on each file and return whether any file differs from its formatted version.

        A diff is printed for each of those files unless `--no-diff` was passed. When the formatter does not print
        the formatted code (in place or dry run mode), the file is compared before and after instead.
        """
        args = [arg for arg in self.args if arg != '--no-diff']
        show_diff = len(args) == len(self.args)
        reread_file = any(arg in args for arg in ('-i', '-n', '--dry-run'))

        failed = False
        for filename in self.files:
            original = self._read_lines(filename)
            command = [self.command, *args, filename]
            result = _call_process.call_process(command)
            if result.stderr or result.returncode != 0:
                self._fail(
                    f'Unexpected Stderr/return code received when analyzing {filename}.\nArgs: {command}',
                    result.stdout + result.stderr,
                )
            formatted = self._read_lines(filename) if reread_file else result.stdout.split('\n')
            diff = list(difflib.unified_diff(original, formatted, fromfile='original', tofile='formatted', lineterm=''))
            if diff:
                failed = True
                if show_diff:
                    sys.stdout.write('\n'.join([filename, 20 * '=', *diff, '']))
        return failed

    def _read_lines(self, filename: str) -> list[str]:
        """Get the lines in a file."""
        path = Path(filename)
        if not path.exists():
            self._fail(f'File {filename} not found', 'Check your path to the file.')
        return path.read_bytes().decode().split('\n')

    def _split_compiler_args(self) -> None:
        """
        Separate the filenames from the compiler options that were passed after `--`.

        Pre-commit adds the filenames at the very end of the command line, so they end up after the `--`:
            clang-tidy --checks=* -- -std=c++17 file1.cpp file2.cpp
        needs to be turned into:
            clang-tidy file1.cpp file2.cpp --checks=* -- -std=c++17
        """
        compiler_args = [arg for arg in self.files if not Path(arg).is_file()]
        if compiler_args:
            self.compiler_args = ['--', *compiler_args]
        self.files = [arg for arg in self.files if Path(arg).is_file()]

    def _add_if_missing(self, new_arg: str) -> None:
        """Add an option such as `--key=value` unless the user already passed that option (with any value)."""
        key = new_arg.split('=', maxsplit=1)[0]
        if all(arg.split('=')[0] != key for arg in self.args):
            self.args.append(new_arg)

    def _check_version(self, expected: str) -> None:
        """Check the version of the tool and exit: with 0 if it starts with the expected one, with 1 otherwise."""
        executable = self.command
        if self.hook.version_executables:
            executable = find_executable(self.hook.version_executables)
            if executable is None:
                self._fail('getting version', f'Unable to locate any of: {", ".join(self.hook.version_executables)}')

        result = _call_process.call_process([executable, '--version'])
        version = re.search(self.hook.version_prefix + r'((?:\d+\.)+[\d+_\+\-a-z]+)', result.stdout)
        if not version:
            self._fail('getting version', f'Unable to find a version number in the output of `{executable} --version`.')
        if not version.group(1).startswith(expected):
            self._fail(
                f'Version of {self.hook.name} is wrong',
                f'Expected version: {expected}\nFound version: {version.group(1)}\n'
                f'Edit your pre-commit config or use a different version of {self.hook.name}.',
            )
        sys.exit(0)

    def _fail(self, problem: str, details: str) -> None:
        """Write a formatted error message to the standard error stream and exit."""
        sys.stderr.write(f'Problem with {self.hook.name}: {problem}\n{details}\n')
        sys.exit(1)


def make_main(hook: Hook) -> Callable[[list[str] | None], None]:
    """Create the entry point of a hook."""

    def main(argv: list[str] | None = None) -> None:
        """Run the hook with the given list of arguments (sys.argv by default)."""
        try:
            HookRunner(hook, sys.argv if argv is None else argv).run()
        except click.exceptions.Exit as err:
            sys.exit(err.exit_code)
        except click.ClickException as err:
            err.show()
            sys.exit(err.exit_code)

    return main
