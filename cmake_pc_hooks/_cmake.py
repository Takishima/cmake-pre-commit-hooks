# Copyright 2023 Damien Nguyen <ngn.damien@gmail.com>
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

import logging
import os
import platform
import shutil
import subprocess as sp
import sys
from pathlib import Path

import fasteners
import filelock

from . import _argparse, _call_process

# ==============================================================================


def get_cmake_command(cmake_names=None):  # pragma: nocover
    """
    Get the path to a CMake executable on the PATH or in the virtual environment.

    Args:
        cmake_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['cmake', 'cmake3']
    """
    if not cmake_names:
        cmake_names = ['cmake', 'cmake3']

    for cmake in cmake_names:
        with Path(os.devnull).open(mode='w', encoding='utf-8') as devnull:
            try:
                sp.check_call([cmake, '--version'], stdout=devnull, stderr=devnull)
                return [shutil.which(cmake)]
            except (OSError, sp.CalledProcessError):
                pass

            # CMake not in PATH, should have installed Python CMake module
            # -> try to find out where it is
            python_executable = Path(sys.executable)
            try:
                root_path = Path(os.environ['VIRTUAL_ENV'])
                python = python_executable.name
            except KeyError:
                root_path = python_executable.parent
                python = python_executable.name

            search_paths = [root_path, root_path / 'bin', root_path / 'Scripts']

            # First try executing CMake directly
            for base_path in search_paths:
                try:
                    cmake_cmd = base_path / cmake
                    sp.check_call([cmake_cmd, '--version'], stdout=devnull, stderr=devnull)
                    return [cmake_cmd]
                except (OSError, sp.CalledProcessError):
                    pass

            # That did not work: try calling it through Python
            for base_path in search_paths:
                try:
                    cmake_cmd = [python, base_path / 'cmake']
                    sp.check_call([*cmake_cmd, '--version'], stdout=devnull, stderr=devnull)
                    return cmake_cmd
                except (OSError, sp.CalledProcessError):
                    pass

    # Nothing worked -> give up!
    return None


class CMakeCommand:
    """Class used to encapsulate all CMake related functionality."""

    DEFAULT_BUILD_DIR = '.cmake_build'

    def __init__(self, cmake_names=None):
        """
        Initialize a CMakeCommand object.

        Args:
            cmake_names (list[str] | None): List of possible names for the CMake executable
        """
        self.command = get_cmake_command(cmake_names)
        self.source_dir = None
        self.build_dir = None
        self.cmake_args = ['-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON']

    def add_cmake_arguments_to_parser(self, parser):
        """Add CMake options to an argparse.ArgumentParser."""
        parser.add_argument('-S', '--source-dir', type=str, help='Path to build directory', default='.')
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
            '-Werror', dest='errors', choices=['dev'], help='Make developer warnings errors.', default=[]
        )
        parser.add_argument(
            '-Wno-error',
            dest='no_errors',
            choices=['dev'],
            help='Make developer warnings not errors.',
            default=[],
        )
        parser.add_argument('--preset', type=str, help='Specify a configure preset.')
        parser.add_argument('--cmake', type=_argparse.executable_path, help='Specify path to CMake executable.')

        parser.add_argument('-Wdev', dest='dev_warnings', action='store_true', help='Enable developer warnings.')
        parser.add_argument(
            '-Wno-dev', dest='no_dev_warnings', action='store_true', help='Suppress developer warnings.'
        )

        parser.add_argument(
            '--unix',
            action=_argparse.OSSpecificAction,
            type=str,
            help='Unix-only (ie. Linux and MacOS) options for CMake',
        )
        parser.add_argument('--linux', action=_argparse.OSSpecificAction, type=str, help='Linux-only options for CMake')
        parser.add_argument('--mac', action=_argparse.OSSpecificAction, type=str, help='Mac-only options for CMake')
        parser.add_argument('--win', action=_argparse.OSSpecificAction, type=str, help='Windows-only options for CMake')

    def resolve_build_directory(self, build_dir_list=None):
        """Locate a valid build directory based on internal list and automatic discovery if enabled."""
        # First try to locate a valid build directory based on internal list
        build_dir_list = [] if build_dir_list is None else [Path(path) for path in build_dir_list]
        for build_dir in build_dir_list:
            if build_dir.exists() and Path(build_dir, 'CMakeCache.txt').exists():
                logging.debug('Located valid build directory with CMakeCache.txt at: %s', str(build_dir))
                self.build_dir = build_dir.resolve()
                return

        # If that fails or none have been passed, attempt automatic discovery
        for path in sorted(self.source_dir.glob('*')):
            if path.is_dir() and (path / 'CMakeCache.txt').exists():
                logging.info('Automatic build dir discovery resulted in: %s', str(path))
                self.build_dir = path
                return

        if not build_dir_list:
            self.build_dir = self.source_dir / self.DEFAULT_BUILD_DIR
        else:
            self.build_dir = Path(build_dir_list[0]).resolve()
        logging.info('Unable to locate a valid build directory. Will be creating one at %s', str(self.build_dir))

    def setup_cmake_args(self, cmake_args):
        """
        Setup CMake arguments.

        Args:
            cmake_args: Dictionary-like data structure with following keys:
                - 'defines': list[str]
                - 'undefined': list[str]
                - 'errors': list[str]
                - 'no_errors': list[str]
                - 'generator': str
                - 'toolset': str
                - 'platform': str
                - 'preset': str
                - 'cmake': str
                - 'dev_warnings': bool
                - 'no_dev_warnings': bool
                - 'linux': list[str]
                - 'mac': list[str]
                - 'win': list[str]
        """
        self.source_dir = Path(cmake_args.source_dir).resolve()
        if cmake_args.cmake:
            self.command = [Path(cmake_args.cmake).resolve()]

        keyword_args = {
            'defines': ([], '-D{}'),
            'undefines': ([], '-U{}'),
            'errors': ([], '-Werror={}'),
            'no_errors': ([], '-Wno-error={}'),
            'generator': ('', '-G{}'),
            'toolset': ('', '-T{}'),
            'platform': ('', '-A{}'),
            'preset': ('', '--preset={}'),
        }

        for key, (default, format_str) in keyword_args.items():
            value = getattr(cmake_args, key, default)
            if value:
                if isinstance(value, str):
                    self.cmake_args.append(format_str.format(value))
                else:
                    for element in value:
                        self.cmake_args.append(format_str.format(element))

        flag_args = {
            'dev_warnings': (False, '-Wdev'),
            'no_dev_warnings': (False, '-Wno_dev'),
        }
        for key, (default, flag_str) in flag_args.items():
            if getattr(cmake_args, key, default):
                self.cmake_args.append(flag_str)

        platform_args = {
            'linux': ([], 'Linux'),
            'mac': ([], 'Darwin'),
            'win': ([], 'Windows'),
        }

        for key, (default, platform_name) in platform_args.items():
            platform_args = getattr(cmake_args, key, default)
            if platform.system() == platform_name and platform_args:
                for arg in platform_args:
                    self.cmake_args.append(arg.strip('"\''))

    def configure(self, command, clean_build=False):
        """
        Run a CMake configure step (multi-process safe).

        Args:
            command (str): Name of calling command
            clean_build (bool): Clean build directory before calling CMake configure
        """
        cmake_configure_lock_file = Path(self.build_dir, '_cmake_configure_lock')
        cmake_configure_try_lock_file = Path(self.build_dir, '_cmake_configure_try_lock')

        self.build_dir.mkdir(exist_ok=True)

        cmake_configure_try_lock = filelock.FileLock(cmake_configure_try_lock_file)
        cmake_configure_lock = fasteners.InterProcessReaderWriterLock(cmake_configure_lock_file)
        try:
            with cmake_configure_try_lock.acquire(blocking=False):  # noqa: SIM117
                with cmake_configure_lock.write_lock():
                    logging.debug('Command %s with id %s is running CMake configure', command, os.getpid())
                    returncode = self._configure(
                        lock_files=(cmake_configure_lock_file, cmake_configure_try_lock_file), clean_build=clean_build
                    )
                    logging.debug('Command %s with id %s is done running CMake configure', command, os.getpid())
        except filelock.Timeout:
            logging.debug('Command %s with id %s is not running CMake configure and waiting', command, os.getpid())
            with cmake_configure_lock.read_lock():
                logging.debug('Command %s with id %s is done waiting', command, os.getpid())
                returncode = 0

        if returncode != 0:
            logging.error('CMake configure step failed. See output for more information.')
            sys.exit(returncode)

    def _configure(self, lock_files, clean_build):
        """Run a CMake configure step."""
        command = [str(cmd) for cmd in self.command]

        self.build_dir.mkdir(exist_ok=True)

        if clean_build:
            for path in self.build_dir.iterdir():
                if path.is_dir():
                    shutil.rmtree(path)
                elif path not in lock_files:
                    path.unlink()

        result = _call_process.call_process([*command, str(self.source_dir), *self.cmake_args], cwd=str(self.build_dir))
        result.stdout = '\n'.join(
            [
                f'Running CMake with: {[*command, str(self.source_dir), *self.cmake_args]}',
                f'  from within {self.build_dir}',
                result.stdout,
                '',
            ]
        )

        compiledb = Path(self.build_dir, 'compile_commands.json')
        if not compiledb.exists():
            result.returncode = 1
            result.stderr += f'\nUnable to locate {compiledb}\n\n'

        if result.returncode != 0:
            result.to_stdout_and_stderr()

        return result.returncode


# ==============================================================================
