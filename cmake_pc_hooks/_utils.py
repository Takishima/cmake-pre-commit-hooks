# Copyright 2021 Damien Nguyen
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

"""Base classes and functions for C/C++ linters and formatters."""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

from . import _argparse, _call_process
from ._cmake import CMakeCommand

_LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=_LOGLEVEL, format='%(levelname)-5s:cmake-pc-hooks:%(message)s')

log = logging.getLogger(__name__)


class CMakePresetError(Exception):
    """Exception raised if a command line incompatibility with --preset is detected."""

    def __init__(self) -> None:
        super().__init__('You *must* specify -B|--build-dir if you pass --preset as a CMake argument!')


def _read_compile_commands_json(compile_db: Path) -> list[str]:
    """Read a JSON compile database and return the list of files contained within."""
    if compile_db.exists():
        with compile_db.open(encoding='utf-8') as fd:
            data = json.load(fd)
        return [entry['file'] for entry in data]
    return []


class Command:
    """Super class that all commands inherit."""

    setup_cmake = True
    website = 'https://github.com/Takishima/cmake-pre-commit-hooks#using-the-hooks'

    def __init__(self, command, look_behind, args):
        """
        Initialize a Command object.

        Args:
            command (str): Name of (or path to) the executable to run
            look_behind (str): Text that immediately precedes the version number in the output of `command --version`
            args (:obj:`list` of :obj:`str`): list of arguments
        """
        self.command = command
        self.version_command = command
        self.look_behind = look_behind
        self.args = args
        self.files = []
        self.edit_in_place = False
        self.ddash_args = []
        self.cmake = CMakeCommand()
        self.clean_build = False
        self.all_at_once = False
        self.read_json_db = False
        self.build_dir_list = ['.', CMakeCommand.DEFAULT_BUILD_DIR]

        self.history = []

    def parse_args(self, args):
        """
        Parse some arguments into some usable variables.

        Args:
            args (:obj:`list` of :obj:`str`): list of arguments
        """
        parser = _argparse.ArgumentParser(
            default_config_name='cmake_pc_hooks.toml',
            pyproject_section_name='tool.cmake_pc_hooks',
            args_groups=[{'title': 'Hook options'}],
        )
        self.cmake.add_cmake_arguments_to_parser(parser)
        hook_options = parser.groups[0]
        hook_options.add_argument(
            '--all-at-once',
            action='store_true',
            help='Pass all filenames at once to the linter/formatter instead of calling the command once for each file',
        )
        hook_options.add_argument(
            '--read-json-db',
            action='store_true',
            help=(
                'Run hooks on files found in compile_commands.json (if found and in addition to files specified on CLI)'
            ),
        )

        # Other options
        hook_options.add_argument('--version', type=str, help='Perform a version check')
        hook_options.add_argument('positionals', metavar='filenames', nargs='*', help='Filenames to check')

        known_args, self.args = parser.parse_known_args(args[1:])

        self.all_at_once = known_args.all_at_once
        self.read_json_db = known_args.read_json_db
        self.clean_build = known_args.clean
        self.build_dir_list.extend(known_args.build_dir or [])

        if not known_args.build_dir and known_args.preset:
            raise CMakePresetError

        if self.setup_cmake:
            self.cmake.setup_cmake_args(known_args)

            if not self.cmake.source_dir.exists() and not self.cmake.source_dir.is_dir():
                sys.stderr.write(f'{self.cmake.source_dir} is not a valid source directory\n')
                sys.exit(1)

        if known_args.version:
            actual_version = self.get_version_str()
            self.assert_version(actual_version, known_args.version)

        # NB: if '--' may be present on the command line, the command class for that particular command needs to call
        #     handle_ddash_args() in order to properly handle the filenames in those cases.
        self.files = known_args.positionals

    def check_installed(self):
        """Make sure that the command is installed and exit with an error if not."""
        if shutil.which(self.command) is None:
            self.raise_error(
                f'{self.command} not found',
                f'Make sure {self.command} is installed and on your PATH.\nFor more info: {self.website}',
            )

    def add_if_missing(self, new_args):
        """
        Add a default argument unless the user already passed that option (with any value).

        Args:
            new_args (:obj:`list` of :obj:`str`): option to add, e.g. ['--key=value']
        """
        new_arg_key = new_args[0].split('=')[0]
        if all(arg.split('=')[0] != new_arg_key for arg in self.args):
            self.args += new_args

    def get_version_str(self):
        """Get the version string (e.g. 8.0.0) of the command."""
        result = _call_process.call_process([self.version_command, '--version'])
        version = re.search(self.look_behind + r'((?:\d+\.)+[\d+_\+\-a-z]+)', result.stdout)
        if not version:
            self.raise_error(
                'getting version',
                f'Unable to find a version number in the output of `{self.version_command} --version`.',
            )
        return version.group(1)

    def assert_version(self, actual_ver, expected_ver):
        """
        Check the version of the command and exit.

        The exit code is 0 if the actual version starts with the expected one, 1 otherwise.
        """
        if expected_ver not in actual_ver[: len(expected_ver)]:
            self.raise_error(
                f'Version of {self.command} is wrong',
                f'Expected version: {expected_ver}\nFound version: {actual_ver}\n'
                f'Edit your pre-commit config or use a different version of {self.command}.',
            )
        sys.exit(0)

    def raise_error(self, problem, details):
        """Write a formatted error message to the standard error stream and exit."""
        sys.stderr.write(f'Problem with {self.command}: {problem}\n{details}\n')
        sys.exit(1)

    def run(self):
        """Run the command."""
        self.cmake.configure(self.command, clean_build=self.clean_build)
        self.files.extend(self.cmake.cmake_configured_files)

        compile_db = self._resolve_compilation_database(self.cmake.build_dir, self.build_dir_list)
        if self.read_json_db and compile_db:
            self.files.extend(set(_read_compile_commands_json(compile_db)) - set(self.files))

        if self.all_at_once:
            self.run_command(self.files)
        elif self.files:
            for filename in self.files:
                self.run_command([filename])
        else:
            log.error('No files to process!')
            sys.exit(1)

        has_errors = False
        for res in self.history:
            has_errors |= self._parse_output(res)
            res.to_stdout_and_stderr()

        if has_errors:
            sys.exit(1)

    def run_command(self, filenames):
        """Run the command and check for errors."""
        self.history.append(_call_process.call_process([self.command, *filenames, *self.args, *self.ddash_args]))

    def _parse_output(self, result):  # ruff: ignore[unused-method-argument, no-self-use]
        return NotImplemented

    @staticmethod
    def _resolve_compilation_database(cmake_build_dir: Path, build_dir_list: list[Path]) -> Path | None:
        """Locate a compilation database based on internal list of directories."""
        if cmake_build_dir and cmake_build_dir / 'compile_commands.json':
            return cmake_build_dir / 'compile_commands.json'

        build_dir_list = [] if build_dir_list is None else [Path(path) for path in build_dir_list]
        for build_dir in build_dir_list:
            path = Path(build_dir, 'compile_commands.json')
            if build_dir.exists() and path.exists():
                log.debug('Located valid compilation database at: %s', path)
                return path
        log.debug('No valid compilation database located')
        return None


class ClangAnalyzerCmd(Command):
    """Commands that statically analyze code: clang-tidy, oclint."""

    def handle_ddash_args(self):
        """
        Handle arguments after a '--'.

        Pre-commit sends a list of files as the last argument which may cause problems with -- and some programs such as
        clang-tidy. This function converts the filename arguments in order to make everything work as expected.

        Example:
            clang-tidy --checks=* -- -std=c++17 file1.cpp file2.cpp
            will be turned into:
            clang-tidy file1.cpp file2.cpp --checks=* -- -std=c++17

            In the case above, the content of self.files would be: ['-std=c++17', 'file1.cpp', 'file2.cpp'] which needs
            to be converted to: ['file1.cpp', 'file2.cpp'] while ['--', '-std=c++17'] should be added to `self.args`.
        """
        files = []
        other_args = []
        for _, fname in enumerate(reversed(self.files)):
            if Path(fname).is_file():
                files.append(fname)
            else:
                other_args.append(fname)

        if other_args:
            self.ddash_args.extend(['--', *other_args])
        self.files = list(reversed(files))


class FormatterCmd(Command):
    """Commands that format code: clang-format, uncrustify."""

    setup_cmake = False

    def __init__(self, command: str, look_behind: str, args: list[str]):
        super().__init__(command, look_behind, args)
        self.dry_run = '-n' in self.args or '--dry-run' in self.args
        self.no_diff_flag = False
        self.diff = ''
        self.returncode = 0

    def set_diff_flag(self) -> None:
        """Handle the --no-diff option (which is not an option of the underlying command)."""
        self.no_diff_flag = '--no-diff' in self.args
        if self.no_diff_flag:
            self.args.remove('--no-diff')

    def compare_to_formatted(self, filename: str) -> None:
        """
        Compare the content of a file to the output of the formatter.

        When editing in place, the formatter has no output: the file is compared before and after instead.
        """
        actual = self.get_filelines(filename)
        expected = self.get_formatted_lines(filename)
        if self.edit_in_place:
            expected = self.get_filelines(filename)
        diff = list(difflib.unified_diff(actual, expected, fromfile='original', tofile='formatted', lineterm=''))
        if diff:
            if not self.no_diff_flag:
                self.diff += '\n'.join([filename, 20 * '=', *diff, ''])
            self.returncode = 1

    def get_formatted_lines(self, filename: str) -> list[str]:
        """Get the expected output for a command applied to a file."""
        args = [self.command, *self.args, filename]
        child = _call_process.call_process(args)
        if child.stderr or child.returncode != 0:
            problem = f'Unexpected Stderr/return code received when analyzing {filename}.\nArgs: {args}'
            self.raise_error(problem, child.stdout + child.stderr)

        if self.dry_run:
            # clang-format dry-run mode is '-n'
            # If dry-run mode then we only look at the return code -> read the lines
            return self.get_filelines(filename)
        if not child.stdout:
            return []
        return child.stdout.split('\n')

    def get_filelines(self, filename: str) -> list[str]:
        """Get the lines in a file."""
        path = Path(filename)
        if not path.exists():
            self.raise_error(f'File {filename} not found', 'Check your path to the file.')
        return path.read_bytes().decode().split('\n')


class StaticAnalyzerCmd(Command):
    """Commands that analyze code without requiring a compilation database: cpplint, lizard."""

    def run(self):
        """Run the command on each file and fail if any of the calls failed."""
        if self.read_json_db:
            if not self.cmake.no_cmake_configure:
                self.cmake.configure(self.command, clean_build=self.clean_build)
            compile_db = self._resolve_compilation_database(self.cmake.build_dir, self.build_dir_list)
            if compile_db:
                self.files.extend(set(_read_compile_commands_json(compile_db)) - set(self.files))

        if self.all_at_once:
            self.run_command(self.files)
        else:
            for filename in self.files:
                self.run_command([filename])

        failures = [result for result in self.history if result.returncode != 0]
        if failures:
            for result in failures:
                sys.stderr.write(result.stdout + result.stderr)
            sys.exit(failures[0].returncode)
