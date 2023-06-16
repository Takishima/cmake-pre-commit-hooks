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

import json
import logging
import os
import sys
from pathlib import Path

import hooks.utils

from . import _argparse, _call_process
from ._cmake import CMakeCommand

_LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=_LOGLEVEL, format='%(levelname)-5s:cmake-pc-hooks:%(message)s')
logging.getLogger('filelock').setLevel(logging.WARNING)


def _read_compile_commands_json(build_dir: Path) -> list[str]:
    """Read a JSON compile database and return the list of files contained within."""
    compile_db = build_dir / 'compile_commands.json'
    if compile_db.exists():
        with compile_db.open(encoding='utf-8') as fd:
            data = json.load(fd)
        return [entry['file'] for entry in data]
    return []


class Command(hooks.utils.Command):  # pylint: disable=too-many-instance-attributes
    """Super class that all commands inherit."""

    setup_cmake = True

    def __init__(self, command, look_behind, args):
        """Initialize a Command object."""
        super().__init__(command, look_behind, args)
        self.ddash_args = []
        self.cmake = CMakeCommand()
        self.clean_build = False
        self.all_at_once = False
        self.read_json_db = False

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
                'Run hooks on files found in compile_commands.json '
                '(if found and in addition to files specified on CLI)'
            ),
        )

        # Other options
        hook_options.add_argument('--version', type=str, help='Perform a version check')
        hook_options.add_argument('positionals', metavar='filenames', nargs='*', help='Filenames to check')

        known_args, self.args = parser.parse_known_args(args[1:])

        self.all_at_once = known_args.all_at_once
        self.read_json_db = known_args.read_json_db
        self.clean_build = known_args.clean

        if not known_args.build_dir and known_args.preset:
            raise RuntimeError('You *must* specify -B|--build-dir if you pass --preset as a CMake argument!')

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

    def run(self):
        """Run the command."""
        self.cmake.configure(self.command)
        if self.read_json_db:
            self.files.extend(set(_read_compile_commands_json(self.cmake.build_dir)) - set(self.files))
        self.files.extend(self.cmake.cmake_configured_files)

        if self.all_at_once:
            self.run_command(self.files)
        elif self.files:
            for filename in self.files:
                self.run_command([filename])
        else:
            logging.error('No files to process!')
            sys.exit(1)

        has_errors = False
        for res in self.history:
            res.to_stdout_and_stderr()
            has_errors |= self._parse_output(res)

        if has_errors:
            sys.exit(1)

    def run_command(self, filenames):  # pylint: disable=arguments-differ,arguments-renamed
        """Run the command and check for errors."""
        self.history.append(_call_process.call_process([self.command, *filenames, *self.args, *self.ddash_args]))
        self._clinters_compat()

    def _clinters_compat(self):
        """Compatibility with CLinters."""
        self.stdout = self.history[-1].stdout.encode()
        self.stderr = self.history[-1].stderr.encode()
        self.returncode = self.history[-1].returncode

    def _parse_output(self, result):  # noqa: ARG002
        return NotImplemented


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
        idx = -1
        files = []
        for _, fname in enumerate(reversed(self.files)):
            if Path(fname).is_file():
                files.append(fname)
            else:
                break

        if idx != len(files) - 1:
            # We have more than just filenames after '--'
            self.ddash_args.extend(['--'] + self.files[0:-idx])
        self.files = files


class FormatterCmd(Command, hooks.utils.FormatterCmd):
    """Commands that format code: clang-format, uncrustify."""

    setup_cmake = False

    def __init__(self, command: str, look_behind: str, args: list[str]):
        super().__init__(command, look_behind, args)
        self.dry_run = '-n' in self.args or '--dry-run' in self.args

    def get_formatted_lines(self, filename: bytes) -> list:  # pragma: nocover
        """Get the expected output for a command applied to a file."""
        filename_opts = self.get_filename_opts(filename)
        args = [self.command, *self.args, *filename_opts]
        # NB: only change w.r.t original method to handle both bytes and string argument types
        child = _call_process.call_process([arg.decode() if isinstance(arg, bytes) else arg for arg in args])
        if len(child.stderr) > 0 or child.returncode != 0:
            problem = f'Unexpected Stderr/return code received when analyzing {filename}.\nArgs: {args}'
            self.raise_error(problem, child.stdout + child.stderr)

        if self.dry_run:
            # clang-format dry-run mode is '-n'
            # If dry-run mode then we only look at the return code -> read the lines
            self.returncode = 0
            return self.get_filelines(filename)
        if not child.stdout:
            return []
        return child.stdout.encode().split(b'\x0a')


class StaticAnalyzerCmd(Command, hooks.utils.StaticAnalyzerCmd):
    """Commands that analyze code and are not formatters."""
