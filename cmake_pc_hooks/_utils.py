# -*- coding: utf-8 -*-
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

""""Base classes and functions for C/C++ linters and formatters"""

import argparse
import os
import subprocess as sp
from pathlib import Path
import shutil
import sys

import fasteners
import hooks.utils


def get_cmake_command(cmake_names=None):
    """
    Get the path to a CMake executable on the PATH or in the virtual environment

    Args:
        cmake_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['cmake', 'cmake3']
    """
    if not cmake_names:
        cmake_names = ['cmake', 'cmake3']

    for cmake in cmake_names:
        with open(os.devnull, 'w') as devnull:
            try:
                sp.check_call([cmake, '--version'], stdout=devnull, stderr=devnull)
                return [shutil.which(cmake)]
            except (OSError, sp.CalledProcessError):
                pass

            # CMake not in PATH, should have installed Python CMake module
            # -> try to find out where it is
            try:
                root_path = os.environ['VIRTUAL_ENV']
                python = os.path.basename(sys.executable)
            except KeyError:
                root_path, python = os.path.split(sys.executable)

            search_paths = [root_path, os.path.join(root_path, 'bin'), os.path.join(root_path, 'Scripts')]

            # First try executing CMake directly
            for base_path in search_paths:
                try:
                    cmake_cmd = os.path.join(base_path, cmake)
                    sp.check_call([cmake_cmd, '--version'], stdout=devnull, stderr=devnull)
                    return [cmake_cmd]
                except (OSError, sp.CalledProcessError):
                    pass

            # That did not work: try calling it through Python
            for base_path in search_paths:
                try:
                    cmake_cmd = [python, os.path.join(base_path, 'cmake')]
                    sp.check_call(cmake_cmd + ['--version'], stdout=devnull, stderr=devnull)
                    return [cmake_cmd]
                except (OSError, sp.CalledProcessError):
                    pass

    # Nothing worked -> give up!
    return None


def executable_path(path):
    """
    Argparse validation function

    Args:
        path (str): Path to some file or directory

    Returns:
        True if `path` points to a file that is executable, False otherwise
    """
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    raise argparse.ArgumentTypeError(f'{path} is not a valid file and/or does not appear executable')


class Command(hooks.utils.Command):  # pylint: disable=too-many-instance-attributes
    """
    Super class that all commands inherit.
    """

    def __init__(self, command, look_behind, args):
        super().__init__(command, look_behind, args)
        self.ddash_args = []
        self.cmake = get_cmake_command()
        self.clean_build = False
        self.source_dir = '.'
        self.build_dir = '.cmake_build'
        self.cmake_args = ['-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']

    def parse_args(self, args):
        """
        Parse some arguments into some usable variables

        Args:
            args (:obj:`list` of :obj:`str`): list of arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-S', '--source-dir', type=str, help='Path to build directory', default=self.source_dir)
        parser.add_argument('-B', '--build-dir', action='append', type=str, help='Path to build directory')
        parser.add_argument(
            '-D', dest='defines', action='append', type=str, help='Create or update a cmake cache entry.'
        )
        parser.add_argument(
            '-U', dest='undefines', action='append', type=str, help='Remove matching entries from CMake cache.'
        )
        parser.add_argument('-G', dest='generator', type=str, help='Specify a build system generator.')
        parser.add_argument('-T', dest='toolset', type=str, help='Specify toolset name if supported by generator.')
        parser.add_argument('-A', dest='platform', type=str, help='Specify platform if supported by generator.')
        parser.add_argument('-Werror', dest='errors', action='append', type=str, help='Make developer warnings errors.')
        parser.add_argument(
            '-Wno-error', dest='no_error', action='append', type=str, help='Make developer warnings not errors.'
        )
        parser.add_argument(
            '--cmake', type=executable_path, help='Make developer warnings not errors.', default=self.cmake
        )

        parser.add_argument('-Wdev', action='store_true', help='Enable developer warnings.')
        parser.add_argument('-Wno-dev', action='store_true', help='Suppress developer warnings.')


        parser.add_argument('positionals', metavar='filenames', nargs="*", help='Filenames to check')
        parser.add_argument('--version', type=str, help='Version check')

        if not self.clean_build:
            parser.add_argument('--clean', action='store_true', help='Start from a clean build directory')

        known_args, self.args = parser.parse_known_args(args)

        self.clean_build = known_args.clean
        self.source_dir = Path(known_args.source_dir).resolve()

        if not known_args.build_dir:
            known_args.build_dir = [self.build_dir]  # default value

        # Try all the passed build directories if one already exists, use that one, otherwise take the first one
        for build_dir in [Path(path) for path in known_args.build_dir]:
            if build_dir.exists() and Path(build_dir, 'CMakeCache.txt').exists():
                self.build_dir = build_dir.resolve()
                break
        else:
            self.build_dir = Path(known_args.build_dir[0]).resolve()
        self._setup_cmake_args(known_args)

        if not self.source_dir.exists() and not self.source_dir.is_dir():
            sys.stderr.write(f'{self.source_dir} is not a valid source directory\n')
            sys.exit(1)

        if known_args.version:
            actual_version = self.get_version_str()
            self.assert_version(actual_version, known_args.version)

        # NB: if '--' may be present on the command line, the command class for that particular command needs to call
        #     handle_ddash_args() in order to properly handle the filenames in those cases.
        self.files = known_args.positionals

    def run_command(self, filename):
        """Run the command and check for errors"""

        try:
            sp_child = sp.run(
                [self.command, filename] + self.args + self.ddash_args, check=True, stdout=sp.PIPE, stderr=sp.PIPE
            )
        except sp.CalledProcessError as e:
            self.stdout += e.stdout.decode()
            self.stderr += e.stderr.decode()
            self.returncode = e.returncode
        else:
            # Set class stdout/stderr/retcode so there's a local copy for testing
            self.stdout += sp_child.stdout.decode()
            self.stderr += sp_child.stderr.decode()
            self.returncode = sp_child.returncode


    def run_cmake_configure(self):  # pylint: disable=too-many-branches
        """Run a CMake configure step"""
        configuring = Path(self.build_dir, '_configuring')
        has_lock = False

        self.build_dir.mkdir(exist_ok=True)

        rw_lock = fasteners.InterProcessReaderWriterLock(configuring)
        if not configuring.exists():
            with rw_lock.write_lock():
                has_lock = True
                if self.clean_build:
                    for path in self.build_dir.iterdir():
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path != configuring:
                            path.unlink()
                try:
                    sp_child = sp.run(
                        self.cmake + [str(self.source_dir)] + self.cmake_args,
                        cwd=self.build_dir,
                        check=True,
                        stdout=sp.PIPE,
                        stderr=sp.PIPE,
                    )
                except sp.CalledProcessError as e:
                    stdout = (
                        f'Running CMake with: {self.cmake + [str(self.source_dir)] + self.cmake_args}\n'
                        + f'  from within {self.build_dir}\n'
                        + e.output.decode()
                    )
                    stderr = e.stderr.decode()
                    self.returncode = e.returncode
                else:
                    stdout = (
                        f'Running CMake with: {self.cmake + [str(self.source_dir)] + self.cmake_args}\n'
                        + f'  from within {self.build_dir}\n'
                        + sp_child.stdout.decode()
                    )
                    stderr = sp_child.stderr.decode()
                    self.returncode = sp_child.returncode

                compiledb = Path(self.build_dir, 'compile_commands.json')
                if self.returncode == 0:
                    if compiledb.exists():
                        shutil.copy(compiledb, self.source_dir)
                    else:
                        self.returncode = 1
                        stderr += f'\nUnable to locate {compiledb}\n\n'

                if self.returncode != 0:
                    sys.stdout.write(stdout + '\n')
                    sys.stderr.write(stderr)
                    sys.stdout.flush()
                    sys.stderr.flush()
        else:
            with rw_lock.read_lock():
                pass

        if has_lock and configuring.exists():
            configuring.unlink()

        if self.returncode != 0:
            sys.exit(self.returncode)

    def _setup_cmake_args(self, args):
        self.cmake = args.cmake if isinstance(args.cmake, list) else [args.cmake]
        if not self.cmake:
            raise RuntimeError('Unable to locate CMake command')

        if args.defines:
            for define in args.defines:
                self.cmake_args.append(f'-D{define}')
        if args.undefines:
            for undefine in args.undefines:
                self.cmake_args.append(f'-U{undefine}')
        if args.errors:
            for error in args.errors:
                self.cmake_args.append(f'-Werror={error}')

        if args.generator:
            self.cmake_args.append(f'-G{args.generator}')
        if args.toolset:
            self.cmake_args.append(f'-T{args.toolset}')
        if args.platform:
            self.cmake_args.append(f'-A{args.platform}')

        if args.Wdev:
            self.cmake_args.append('-Wdev')
        if args.Wno_dev:
            self.cmake_args.append('-Wno-dev')


class ClangAnalyzerCmd(Command):
    """Commands that statically analyze code: clang-tidy, oclint"""

    def handle_ddash_args(self):
        """
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
        for idx, fname in enumerate(reversed(self.files)):
            if Path(fname).is_file():
                files.append(fname)
            else:
                break

        if idx != len(files) - 1:
            # We have more than just filenames after '--'
            self.ddash_args.extend(['--'] + self.files[0:-idx])
        self.files = files


class FormatterCmd(Command, hooks.utils.FormatterCmd):
    """Commands that format code: clang-format, uncrustify"""
