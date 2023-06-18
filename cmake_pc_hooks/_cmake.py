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

"""CMake related function and classes."""

import contextlib
import json
import logging
import os
import platform
import re
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
    DEFAULT_TRACE_LOG = 'trace_log.json'

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
        self.cmake_trace_log = None
        self.cmake_configured_files = []

    def add_cmake_arguments_to_parser(self, parser):
        """Add CMake options to an argparse.ArgumentParser."""
        # Create option group here to control the order
        cmake_options = parser.add_argument_group(
            title='CMake options',
            description='Options mirroring those of CMake and that will be passed onto CMake as-is.',
        )
        options = parser.add_argument_group(
            title='Other CMake related options', description='Options used to configure how CMake is called'
        )
        platform_specific_cmake = parser.add_argument_group(
            title='Options to define platform-dependent CMake variables',
            description=(
                'This allows you to set CMake variables during the configuration depending on the platform the hooks '
                'are currently running on.'
                'For example --unix="CMAKE_CXX_COMPILER=g++" will only define this CMake variable on UNIX platforms.'
            ),
        )

        # Custom options
        options.add_argument('--clean', action='store_true', help='Start from a clean build directory')
        options.add_argument('--cmake', type=_argparse.executable_path, help='Specify path to CMake executable.')
        options.add_argument(
            '--detect-configured-files',
            action='store_true',
            help='Enable tracing of files generated  using the configure_file(...) CMake function',
        )
        options.add_argument(
            '--no-automatic-discovery',
            action='store_false',
            dest='automatic_discovery',
            help='Do not attempt to automatically look for a build directory',
        )

        # Platform-specific CMake options
        platform_specific_cmake.add_argument(
            '--unix',
            action=_argparse.OSSpecificAction,
            type=str,
            help='Unix-only (ie. Linux and MacOS) options for CMake',
        )
        platform_specific_cmake.add_argument(
            '--linux', action=_argparse.OSSpecificAction, type=str, help='Linux-only options for CMake'
        )
        platform_specific_cmake.add_argument(
            '--mac', action=_argparse.OSSpecificAction, type=str, help='Mac-only options for CMake'
        )
        platform_specific_cmake.add_argument(
            '--win', action=_argparse.OSSpecificAction, type=str, help='Windows-only options for CMake'
        )

        # CMake-like options
        cmake_options.add_argument('-S', '--source-dir', type=str, help='Path to build directory', default='.')
        cmake_options.add_argument('-B', '--build-dir', action='append', type=str, help='Path to build directory')
        cmake_options.add_argument(
            '-D', dest='defines', action='append', type=str, help='Create or update a cmake cache entry.', default=[]
        )
        cmake_options.add_argument(
            '-U',
            dest='undefines',
            action='append',
            type=str,
            help='Remove matching entries from CMake cache.',
            default=[],
        )
        cmake_options.add_argument('-G', dest='generator', type=str, help='Specify a build system generator.')
        cmake_options.add_argument(
            '-T', dest='toolset', type=str, help='Specify toolset name if supported by generator.'
        )
        cmake_options.add_argument('-A', dest='platform', type=str, help='Specify platform if supported by generator.')
        cmake_options.add_argument(
            '-Werror', dest='errors', choices=['dev'], help='Make developer warnings errors.', default=[]
        )
        cmake_options.add_argument(
            '-Wno-error',
            dest='no_errors',
            choices=['dev'],
            help='Make developer warnings not errors.',
            default=[],
        )
        cmake_options.add_argument('--preset', type=str, help='Specify a configure preset.')

        cmake_options.add_argument('-Wdev', dest='dev_warnings', action='store_true', help='Enable developer warnings.')
        cmake_options.add_argument(
            '-Wno-dev', dest='no_dev_warnings', action='store_true', help='Suppress developer warnings.'
        )

    def resolve_build_directory(self, build_dir_list=None, automatic_discovery=True):
        """Locate a valid build directory based on internal list and automatic discovery if enabled."""
        # First try to locate a valid build directory based on internal list
        build_dir_list = [] if build_dir_list is None else [Path(path) for path in build_dir_list]
        for build_dir in build_dir_list:
            if build_dir.exists() and Path(build_dir, 'CMakeCache.txt').exists():
                logging.debug('Located valid build directory with CMakeCache.txt at: %s', str(build_dir))
                self.build_dir = build_dir.resolve()
                return

        # If that fails or none have been passed, attempt automatic discovery
        if automatic_discovery:
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

        self.resolve_build_directory(
            build_dir_list=cmake_args.build_dir, automatic_discovery=cmake_args.automatic_discovery
        )

        if cmake_args.detect_configured_files:
            self.cmake_trace_log = self.build_dir / self.DEFAULT_TRACE_LOG

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
        if self.source_dir is None:
            logging.error('No source dir was for CMake! Did you call `setup_cmake_args()`?')
            sys.exit(1)

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

        if self.cmake_trace_log is not None:
            self._parse_cmake_trace_log()

    def _call_cmake(self, extra_args=None):
        command = [str(cmd) for cmd in self.command]
        if extra_args is None:
            extra_args = []

        result = _call_process.call_process(
            [*command, str(self.source_dir), *self.cmake_args, *extra_args], cwd=str(self.build_dir)
        )
        result.stdout = '\n'.join(
            [
                f'Running CMake with: {[*command, str(self.source_dir), *self.cmake_args]}',
                f'  from within {self.build_dir}',
                result.stdout,
                '',
            ]
        )

        return result

    def _configure(self, lock_files, clean_build):
        """Run a CMake configure step."""
        self.build_dir.mkdir(exist_ok=True)

        if clean_build:
            for path in self.build_dir.iterdir():
                if path.is_dir():
                    shutil.rmtree(path)
                elif path not in lock_files:
                    path.unlink()

        extra_args = []
        if self.cmake_trace_log:
            extra_args.extend(['--trace-expand', '--trace-format=json-v1', f'--trace-redirect={self.cmake_trace_log}'])

        result = self._call_cmake(extra_args=extra_args)

        compiledb = Path(self.build_dir, 'compile_commands.json')
        if not compiledb.exists():
            result.returncode = 1
            result.stderr += f'\nUnable to locate {compiledb}\n\n'

        if result.returncode != 0:
            result.to_stdout_and_stderr()

        return result.returncode

    def _parse_cmake_trace_log(self):
        logging.info('attempting to parse CMake trace log to detect calls to configure_file()')
        self.cmake_configured_files = []

        if not self.cmake_trace_log:
            logging.info('no trace log provided, aborting.')
            return

        result = self._call_cmake(extra_args=['-N', '-LA'])
        if result.returncode != 0:
            logging.error('failed to retrieve CMake cache variables')
            return

        cmake_cache_variables = {}
        for line in result.stdout.splitlines():
            cmake_var = re.match(r'^(\w+):(BOOL|FILEPATH|PATH|STRING|INTERNAL)=(.*)$', line)
            if cmake_var:
                cmake_cache_variables[cmake_var.group(1)] = cmake_var.group(3)

        # ------------------------------

        def _is_relevant_configure_file_call(json_data):
            """
            Filter out the list of configure_file() calls.

            The criteria are:
              - Being a call to configure_file()
              - Originating from a CMake file located inside the source directory
              - Not originating from a CMake file located in FETCHCONTENT_BASE_DIR (if defined)
            """
            if json_data.get('cmd', '') != 'configure_file':
                return False

            is_relevant = self.source_dir.as_posix() in json_data['file']
            with contextlib.suppress(KeyError):
                is_relevant &= cmake_cache_variables['FETCHCONTENT_BASE_DIR'] not in json_data['file']
            return is_relevant

        with self.cmake_trace_log.open('r') as fd:
            configure_file_calls = [json.loads(line) for line in fd.readlines()]

        for configure_file_call in (data for data in configure_file_calls if _is_relevant_configure_file_call(data)):
            input_file, configured_file = (Path(arg) for arg in configure_file_call['args'][:2])
            if not configured_file.is_absolute():
                configured_file = self.build_dir / configured_file
            logging.debug('detected call to configure_file(%s %s [...])', str(input_file), str(configured_file))
            self.cmake_configured_files.append(str(configured_file))


# ==============================================================================
