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

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess as sp
import sys
from pathlib import Path

import fasteners
import hooks.utils

_LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()  # pylint: disable=no-member
logging.basicConfig(level=_LOGLEVEL)


def get_cmake_command(cmake_names=None):
    """
    Get the path to a CMake executable on the PATH or in the virtual environment.

    Args:
        cmake_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['cmake', 'cmake3']
    """
    if not cmake_names:
        cmake_names = ['cmake', 'cmake3']

    for cmake in cmake_names:
        # pylint: disable=no-member
        with open(os.devnull, 'w', encoding='utf-8') as devnull:
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


def _read_compile_commands_json(build_dir: Path):
    """Read a JSON compile database and return the list of files contained within."""
    compile_db = build_dir / 'compile_commands.json'
    if compile_db.exists():
        with open(str(compile_db), encoding='utf-8') as fd:
            data = json.load(fd)
        return [entry['file'] for entry in data]
    return []


def _append_in_namespace(namespace, key, values):
    current = getattr(namespace, key, [])
    if current is None:
        current = []
    current.append(values)
    setattr(namespace, key, current)


class _History:  # pylint: disable=too-few-public-methods
    __slots__ = ('stdout', 'stderr', 'returncode')

    def __init__(self, stdout, stderr, returncode):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _OSSpecificAction(argparse.Action):
    def __call__(self, parser, namespace, values, options_string=None):
        if self.dest == 'unix':
            _append_in_namespace(namespace, 'linux', values)
            _append_in_namespace(namespace, 'mac', values)

        _append_in_namespace(namespace, self.dest, values)


def executable_path(path):
    """
    Argparse validation function.

    Args:
        path (str): Path to some file or directory

    Returns:
        True if `path` points to a file that is executable, False otherwise
    """
    # pylint: disable=no-member
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    raise argparse.ArgumentTypeError(f'{path} is not a valid file and/or does not appear executable')


def copy_std_output_to_sys(result: _History):
    """Copy the standard output and error resulting from a command execution to system standard streams."""
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.stdout.flush()
    sys.stderr.flush()


class Command(hooks.utils.Command):  # pylint: disable=too-many-instance-attributes
    """Super class that all commands inherit."""

    def __init__(self, command, look_behind, args):
        """Initialize a Command object."""
        super().__init__(command, look_behind, args)
        self.ddash_args = []
        self.cmake = get_cmake_command()
        self.clean_build = False
        self.source_dir = '.'
        self.build_dir = '.cmake_build'
        self.cmake_args = ['-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
        self.all_at_once = False
        self.read_json_db = False

        self.history = []

    def parse_args(self, args):
        """
        Parse some arguments into some usable variables.

        Args:
            args (:obj:`list` of :obj:`str`): list of arguments
        """
        parser = argparse.ArgumentParser()

        # CMake-related options
        parser.add_argument('-S', '--source-dir', type=str, help='Path to build directory', default=self.source_dir)
        parser.add_argument('-B', '--build-dir', action='append', type=str, help='Path to build directory')
        parser.add_argument(
            '-D', dest='defines', action='append', type=str, help='Create or update a cmake cache entry.', default=[]
        )
        parser.add_argument(
            '-U',
            dest='undefines',
            action='append',
            type=str,
            help='Remove matching entries from CMake cache.',
            default=[],
        )
        parser.add_argument('-G', dest='generator', type=str, help='Specify a build system generator.')
        parser.add_argument('-T', dest='toolset', type=str, help='Specify toolset name if supported by generator.')
        parser.add_argument('-A', dest='platform', type=str, help='Specify platform if supported by generator.')
        parser.add_argument(
            '-Werror', dest='errors', action='append', type=str, help='Make developer warnings errors.', default=[]
        )
        parser.add_argument(
            '-Wno-error',
            dest='no_error',
            action='append',
            type=str,
            help='Make developer warnings not errors.',
            default=[],
        )
        parser.add_argument('--preset', type=str, help='Specify a configure preset.')
        parser.add_argument(
            '--cmake', type=executable_path, help='Specify path to CMake executable.', default=self.cmake
        )

        parser.add_argument('-Wdev', action='store_true', help='Enable developer warnings.')
        parser.add_argument('-Wno-dev', action='store_true', help='Suppress developer warnings.')

        parser.add_argument(
            '--all-at-once',
            action='store_true',
            help='Pass all filenames at once to the linter/formatter instead of calling the command once for each file',
        )
        parser.add_argument(
            '--read-json-db',
            action='store_true',
            help=(
                'Run hooks on files found in compile_commands.json '
                '(if found and in addition to files specified on CLI)'
            ),
        )

        parser.add_argument(
            '--unix',
            action=_OSSpecificAction,
            type=str,
            help='Unix-only (ie. Linux and MacOS) options for CMake',
        )
        parser.add_argument('--linux', action=_OSSpecificAction, type=str, help='Linux-only options for CMake')
        parser.add_argument('--mac', action=_OSSpecificAction, type=str, help='Mac-only options for CMake')
        parser.add_argument('--win', action=_OSSpecificAction, type=str, help='Windows-only options for CMake')

        # Other options
        parser.add_argument('positionals', metavar='filenames', nargs="*", help='Filenames to check')
        parser.add_argument('--version', type=str, help='Version check')

        if not self.clean_build:
            parser.add_argument('--clean', action='store_true', help='Start from a clean build directory')

        known_args, self.args = parser.parse_known_args(args[1:])

        self.cmake = known_args.cmake
        self.all_at_once = known_args.all_at_once
        self.read_json_db = known_args.read_json_db
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

    def run(self):
        """Run the command."""
        self.run_cmake_configure()
        if self.read_json_db:
            self.files.extend(set(self.files).symmetric_difference(set(_read_compile_commands_json(self.build_dir))))
        if self.all_at_once:
            self.run_command(self.files)
        elif self.files:
            for filename in self.files:
                self.run_command([filename])
        else:
            logging.error('No files to process!')
            sys.exit(1)

        has_errors = False
        for res in self.history[1:]:
            copy_std_output_to_sys(res)
            has_errors |= self._parse_output(res)

        if has_errors:
            sys.exit(1)

    def run_command(self, filenames):  # pylint: disable=arguments-differ,arguments-renamed
        """Run the command and check for errors."""
        self.history.append(self._call_process([self.command] + filenames + self.args + self.ddash_args))

        # Compatibility with CLinters
        self.stdout = self.history[-1].stdout.encode()
        self.stderr = self.history[-1].stderr.encode()
        self.returncode = self.history[-1].returncode

    def run_cmake_configure(self):  # pylint: disable=too-many-branches
        """Run a CMake configure step."""
        configuring = Path(self.build_dir, '_configuring')

        self.build_dir.mkdir(exist_ok=True)

        rw_lock = fasteners.InterProcessReaderWriterLock(configuring)
        if not configuring.exists():
            with rw_lock.write_lock():
                if self.clean_build:
                    for path in self.build_dir.iterdir():
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path != configuring:
                            path.unlink()

                result = self._call_process(self.cmake + [str(self.source_dir)] + self.cmake_args, cwd=self.build_dir)
                result.stdout = '\n'.join(
                    [
                        f'Running CMake with: {self.cmake + [str(self.source_dir)] + self.cmake_args}',
                        f'  from within {self.build_dir}',
                        result.stdout,
                        '',
                    ]
                )

                if result.returncode == 0:
                    compiledb = Path(self.build_dir, 'compile_commands.json')
                    if not compiledb.exists():
                        result.returncode = 1
                        result.stderr += f'\nUnable to locate {compiledb}\n\n'
                        copy_std_output_to_sys(result)
                    else:
                        compiledb_srcdir = Path(self.source_dir, 'compile_commands.json')
                        if compiledb_srcdir.is_symlink() and compiledb_srcdir.resolve() == compiledb:
                            # If it's a symbolic link and points to the compilation database in the build directory,
                            # we're all good.
                            pass
                        else:
                            # In all other cases, we copy the compilation database into the source directory
                            if compiledb_srcdir.is_symlink():
                                logging.debug('Removing symbolic link at: %s', compiledb_srcdir)
                                compiledb_srcdir.unlink()
                                logging.debug(
                                    'copying compilation database from %s to %s', self.build_dir, self.source_dir
                                )
                            shutil.copy(compiledb, self.source_dir)
                else:
                    copy_std_output_to_sys(result)

                self.history.append(result)
                returncode = result.returncode
            configuring.unlink()
        else:
            returncode = 0
            with rw_lock.read_lock():
                pass

        if returncode != 0:
            sys.exit(returncode)

    def _parse_output(self, result):  # pylint: disable=unused-argument
        return NotImplemented

    def _call_process(self, args, **kwargs):
        try:
            sp_child = sp.run(args, check=True, stdout=sp.PIPE, stderr=sp.PIPE, **kwargs)
        except sp.CalledProcessError as e:
            ret = _History(e.stdout.decode(), e.stderr.decode(), e.returncode)
        else:
            ret = _History(sp_child.stdout.decode(), sp_child.stderr.decode(), sp_child.returncode)

            logging.debug('command `%s` exited with %d', ' '.join(args), ret.returncode)
            for line in ret.stdout.split('\n'):
                logging.debug('(stdout) %s', line)
            for line in ret.stderr.split('\n'):
                logging.debug('(stderr) %s', line)
        return ret

    def _setup_cmake_args(self, args):  # pylint: disable=too-many-branches
        self.cmake = args.cmake if isinstance(args.cmake, list) else [args.cmake]
        if not self.cmake:
            raise RuntimeError('Unable to locate CMake command')

        for define in args.defines:
            self.cmake_args.append(f'-D{define}')

        for undefine in args.undefines:
            self.cmake_args.append(f'-U{undefine}')

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
        if args.preset:
            self.cmake_args.append(f'--preset={args.preset}')

        for system, attr in (('Linux', 'linux'), ('Darwin', 'mac'), ('Windows', 'win')):
            platform_args = getattr(args, attr)
            if platform.system() == system and platform_args:
                for arg in platform_args:
                    self.cmake_args.append(arg.strip('"\''))


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
    """Commands that format code: clang-format, uncrustify."""

    def get_formatted_lines(self, filename: bytes):
        """Get the expected output for a command applied to a file."""
        filename_opts = self.get_filename_opts(filename)
        args = [self.command, *self.args, *filename_opts]
        child = self._call_process([arg.decode() if isinstance(arg, bytes) else arg for arg in args])
        if len(child.stderr) > 0 or child.returncode != 0:
            problem = f"Unexpected Stderr/return code received when analyzing {filename}.\nArgs: {args}"
            self.raise_error(problem, child.stdout + child.stderr)
        if child.stdout == "":
            return []
        return child.stdout.encode().split(b"\x0a")


class StaticAnalyzerCmd(Command, hooks.utils.StaticAnalyzerCmd):
    """Commands that analyze code and are not formatters."""
