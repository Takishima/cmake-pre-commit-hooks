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

"""Run the CMake configure and build steps."""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from cmake_pc_hooks import _call_process

import fasteners

from . import locate, trace

if TYPE_CHECKING:
    from .options import CMakeOptions

log = logging.getLogger(__name__)


class CMakeCommand:
    """Class used to encapsulate all CMake related functionality."""

    DEFAULT_BUILD_DIR = locate.DEFAULT_BUILD_DIR
    DEFAULT_TRACE_LOG = 'trace_log.json'
    COMPILE_DB_NAME = 'compile_commands.json'
    CODEGEN_TARGET = 'codegen'
    CODEGEN_MIN_VERSION = (3, 31)
    CODEGEN_GENERATORS = ('Ninja', 'Makefiles')

    def __init__(self, options: CMakeOptions) -> None:
        """Locate CMake and the build directory."""
        self.command = [options.cmake.resolve()] if options.cmake else locate.get_cmake_command()
        self.source_dir = options.source_dir.resolve()
        self.cmake_args = ['-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON', *options.cmake_args]
        self.no_cmake_configure = options.no_cmake_configure
        self.codegen = options.codegen
        self.build_targets = list(options.build_targets)
        if self.codegen and self.CODEGEN_TARGET not in self.build_targets:
            self.build_targets.append(self.CODEGEN_TARGET)
        self.cmake_configured_files = []

        self.build_dir = locate.find_build_directory(
            self.source_dir,
            options.build_dirs,
            automatic_discovery=options.automatic_discovery,
            create=not options.no_cmake_configure,
        )

        self.cmake_trace_log = None
        if options.detect_configured_files and self.build_dir:
            self.cmake_trace_log = self.build_dir / self.DEFAULT_TRACE_LOG

    def configure(self, command, *, clean_build=False):
        """
        Run a CMake configure step (multi-process safe).

        Only one process runs CMake: the one that gets the write lock. The others wait for it by taking the read
        lock. Trying to take the write lock is a single atomic operation, so a process cannot be done waiting before
        the configure step of another process has even started.

        Args:
            command (str): Name of calling command
            clean_build (bool): Clean build directory before calling CMake configure
        """
        if self.no_cmake_configure:
            log.debug('Not calling CMake configure')
            if self.build_targets:
                log.warning(
                    'Not building CMake target(s) %s since --no-cmake-configure was specified',
                    ', '.join(self.build_targets),
                )
            return

        if self.codegen:
            self._check_codegen_cmake_version()

        cmake_configure_lock_file = Path(self.build_dir, '_cmake_configure_lock')

        self.build_dir.mkdir(exist_ok=True)

        cmake_configure_lock = fasteners.InterProcessReaderWriterLock(cmake_configure_lock_file)
        step = 'configure'
        if cmake_configure_lock.acquire_write_lock(blocking=False):
            try:
                log.debug('Command %s with id %s is running CMake configure', command, os.getpid())
                step, returncode = self._configure_and_build(
                    lock_files=(cmake_configure_lock_file,), clean_build=clean_build
                )
                log.debug('Command %s with id %s is done running CMake configure', command, os.getpid())
            finally:
                cmake_configure_lock.release_write_lock()
        else:
            log.debug('Command %s with id %s is not running CMake configure and waiting', command, os.getpid())
            with cmake_configure_lock.read_lock():
                log.debug('Command %s with id %s is done waiting', command, os.getpid())
                returncode = 0

        if returncode != 0:
            log.error('CMake %s step failed. See output for more information.', step)
            sys.exit(returncode)

        if self.cmake_trace_log is not None:
            self._detect_configured_files()

    def _configure_and_build(self, lock_files, clean_build):
        """
        Run a CMake configure step followed by a build of the requested targets (if any).

        The return value is a tuple with the name of the last step that was run and its return code.
        """
        returncode = self._configure(lock_files=lock_files, clean_build=clean_build)
        if returncode == 0 and self.build_targets:
            return 'build', self._build()
        return 'configure', returncode

    def get_version(self):
        """Retrieve the version of the CMake executable (see `locate.get_version()`)."""
        return locate.get_version(self.command)

    def _check_codegen_cmake_version(self):
        """Make sure that the CMake executable is recent enough to provide the `codegen` target."""
        version = self.get_version()
        min_version_str = '.'.join(str(part) for part in self.CODEGEN_MIN_VERSION)
        if version is None:
            log.warning(
                'Unable to determine the CMake version: --codegen requires CMake >= %s',
                min_version_str,
            )
            return

        if version[: len(self.CODEGEN_MIN_VERSION)] < self.CODEGEN_MIN_VERSION:
            log.error(
                '--codegen requires CMake >= %s, but found CMake %s. Either upgrade CMake (or use --cmake to point to '
                'a newer one) or use --cmake-build-target to build a target of your project that generates the files.',
                min_version_str,
                '.'.join(str(part) for part in version),
            )
            sys.exit(1)

    def _get_generator(self):
        """Read the name of the CMake generator from the CMake cache (None if not found)."""
        try:
            cache = Path(self.build_dir, 'CMakeCache.txt').read_text(encoding='utf-8', errors='replace')
        except OSError:
            return None
        generator = re.search(r'^CMAKE_GENERATOR:\w+=(.*)$', cache, flags=re.MULTILINE)
        return generator.group(1).strip() if generator else None

    def _build(self):
        """Build some CMake targets (must be called after a successful CMake configure step)."""
        if self.codegen:
            generator = self._get_generator()
            if generator is not None and not any(name in generator for name in self.CODEGEN_GENERATORS):
                log.error(
                    '--codegen is only supported with the Ninja and Makefile generators, but %s is using "%s"',
                    self.build_dir,
                    generator,
                )
                return 1

        command = [*(str(cmd) for cmd in self.command), '--build', str(self.build_dir), '--target', *self.build_targets]
        log.debug('Building CMake target(s): %s', ', '.join(self.build_targets))
        result = _call_process.call_process(command)

        if result.returncode != 0:
            result.stdout = f'Running CMake with: {command}\n{result.stdout}\n'
            if self.CODEGEN_TARGET in self.build_targets:
                result.stderr += (
                    f'\nNB: the `{self.CODEGEN_TARGET}` target is only generated by CMake if policy CMP0171 is set to '
                    'NEW in your project, e.g. by using cmake_minimum_required(VERSION 3.31) or newer.\n\n'
                )
            result.to_stdout_and_stderr()

        return result.returncode

    def _call_cmake(self, extra_args):
        """Call CMake on the source directory from within the build directory."""
        command = [str(cmd) for cmd in self.command]

        result = _call_process.call_process(
            [*command, str(self.source_dir), *self.cmake_args, *extra_args],
            cwd=str(self.build_dir),
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
            extra_args.extend(
                [
                    '--trace-expand',
                    '--trace-format=json-v1',
                    f'--trace-redirect={self.cmake_trace_log}',
                ]
            )

        result = self._call_cmake(extra_args=extra_args)

        compiledb = Path(self.build_dir, self.COMPILE_DB_NAME)
        if not compiledb.exists():
            result.returncode = 1
            result.stderr += f'\nUnable to locate {compiledb}\n\n'

        if result.returncode != 0:
            result.to_stdout_and_stderr()

        return result.returncode

    def _detect_configured_files(self):
        """Use the CMake trace log to find the files generated by calls to configure_file()."""
        log.info('attempting to parse CMake trace log to detect calls to configure_file()')
        self.cmake_configured_files = []

        result = self._call_cmake(extra_args=['-N', '-LA'])
        if result.returncode != 0:
            log.error('failed to retrieve CMake cache variables')
            return

        self.cmake_configured_files = trace.find_configured_files(
            self.cmake_trace_log, self.source_dir, self.build_dir, trace.parse_cache_variables(result.stdout)
        )
