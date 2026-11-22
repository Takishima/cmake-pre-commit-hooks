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

"""Locate the CMake executable and the build directory."""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

from cmake_pc_hooks import _call_process

log = logging.getLogger(__name__)

DEFAULT_BUILD_DIR = '.cmake_build'


def _try_calling_cmake(cmake_cmd: list[str | Path]) -> bool:
    """
    Try to call CMake using the provided command.

    Args:
        cmake_cmd: CMake command line

    Return:
        True if command line is valid, False otherwise
    """
    try:
        return _call_process.call_process([*(str(cmd) for cmd in cmake_cmd), '--version']).returncode == 0
    except OSError:
        return False


def get_cmake_command(cmake_names=None):  # pragma: nocover
    """
    Get the path to a CMake executable on the PATH or in the virtual environment.

    For each name, CMake is looked up on the PATH, then in the virtual environment (where the `cmake` Python
    package installs it): first as an executable, then as a script to run with Python.

    Args:
        cmake_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['cmake', 'cmake3']
    """
    if not cmake_names:
        cmake_names = ['cmake', 'cmake3']

    for cmake in cmake_names:
        cmake_cmd = shutil.which(cmake)
        if cmake_cmd is not None and _try_calling_cmake([cmake_cmd]):
            return [cmake_cmd]

        python_executable = Path(sys.executable)
        try:
            root_path = Path(os.environ['VIRTUAL_ENV'])
            python = python_executable.name
        except KeyError:
            root_path = python_executable.parent
            python = python_executable.name

        search_paths = [root_path, root_path / 'bin', root_path / 'Scripts']

        for base_path in search_paths:
            cmake_cmd = [base_path / cmake]
            if _try_calling_cmake(cmake_cmd):
                return cmake_cmd

        for base_path in search_paths:
            cmake_cmd = [python, base_path / 'cmake']
            if _try_calling_cmake(cmake_cmd):
                return cmake_cmd

    return None


def get_version(command: list[str | Path] | None) -> tuple[int, ...] | None:
    """
    Retrieve the version of a CMake executable.

    The version is a tuple of integers (major, minor, patch) or None if the version could not be determined.
    """
    if not command:
        return None

    try:
        result = _call_process.call_process([*(str(cmd) for cmd in command), '--version'])
    except OSError:
        return None

    version = re.search(r'version\s+(\d+)\.(\d+)(?:\.(\d+))?', result.stdout)
    if result.returncode != 0 or not version:
        return None
    return tuple(int(part or 0) for part in version.groups())


def find_build_directory(
    source_dir: Path, build_dirs: list[str], *, automatic_discovery: bool = True, create: bool = True
) -> Path | None:
    """
    Locate the CMake build directory.

    The candidates are, in order: the first of `build_dirs` that contains a CMake cache, then (with automatic
    discovery) the first sub-directory of the source directory that contains one. If there is none, the result is the
    directory to create: the first of `build_dirs` or else a default one. It is None if `create` is False.
    """
    for build_dir in (Path(path) for path in build_dirs):
        if build_dir.exists() and Path(build_dir, 'CMakeCache.txt').exists():
            log.debug('Located valid build directory with CMakeCache.txt at: %s', build_dir)
            return build_dir.resolve()

    if automatic_discovery:
        for path in sorted(source_dir.glob('*')):
            if path.is_dir() and (path / 'CMakeCache.txt').exists():
                log.info('Automatic build dir discovery resulted in: %s', path)
                return path

    if not create:
        log.info('Unable to locate a valid build directory. Will not be creating one')
        return None

    build_dir = Path(build_dirs[0]).resolve() if build_dirs else source_dir / DEFAULT_BUILD_DIR
    log.info('Unable to locate a valid build directory. Will be creating one at %s', build_dir)
    return build_dir
