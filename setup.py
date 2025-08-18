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

"""Dummy setup script."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess  # noqa: S404
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.egg_info import egg_info

log = logging.getLogger(__name__)


def _try_calling_executable(exec_cmd: list[str | Path]) -> bool:
    """
    Try to call CMake using the provided command.

    Args:
        exec_cmd: CMake command line

    Return:
        True if command line is valid, False otherwise
    """
    with Path(os.devnull).open(mode='w', encoding='utf-8') as devnull:
        try:
            subprocess.check_call([*exec_cmd, '--version'], stdout=devnull, stderr=devnull)
        except (OSError, subprocess.CalledProcessError):
            return False
        else:
            return True


def get_executable(exec_name):
    """Try to locate an executable in a Python virtual environment."""
    python_executable = Path(sys.executable)
    try:
        root_path = Path(os.environ['VIRTUAL_ENV'])
        python = python_executable.name
    except KeyError:
        root_path = python_executable.parent
        python = python_executable.name

    exec_name = Path(exec_name).name

    log.info('trying to locate %s in %s', exec_name, root_path)

    search_paths = [root_path, root_path / 'bin', root_path / 'Scripts']

    # First try executing the program directly
    for base_path in search_paths:
        cmd = [base_path / exec_name]
        if _try_calling_executable(cmd):
            log.info('  command found: %s', cmd)
            return cmd
        log.info('  failed in %s', base_path)

    # That did not work: try calling it through Python
    for base_path in search_paths:
        cmd = [python, base_path / exec_name]

        if _try_calling_executable(cmd):
            log.info('  command found: %s', cmd)
            return cmd
        log.info('  failed in %s', base_path)

    log.info('  command *not* found in virtualenv!')

    return shutil.which(exec_name)


class EggInfo(egg_info):
    """
    Custom egg_info command.

    Makes sure that clang-format is added to the list of requirements if the command cannot be found on the path.
    """

    def run(self):
        """Run the egg_info command."""
        for exec_name, pkg in ({'clang-format': 'clang-format', 'lizard': 'lizard'}).items():
            if get_executable(exec_name) is None:
                self.distribution.install_requires.append(pkg)

        egg_info.run(self)


setup(
    cmdclass={
        'egg_info': EggInfo,
    }
)
