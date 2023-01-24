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

import logging
import os
import shutil
import subprocess
import sys

from setuptools import setup
from setuptools.command.egg_info import egg_info


def get_executable(exec_name):
    """Try to locate an executable in a Python virtual environment."""
    # pylint: disable=no-member
    try:
        root_path = os.environ['VIRTUAL_ENV']
        python = os.path.basename(sys.executable)
    except KeyError:
        root_path, python = os.path.split(sys.executable)

    exec_name = os.path.basename(exec_name)

    logging.info('trying to locate %s in %s', exec_name, root_path)

    search_paths = [root_path, os.path.join(root_path, 'bin'), os.path.join(root_path, 'Scripts')]

    # First try executing the program directly
    for base_path in search_paths:
        try:
            cmd = os.path.join(base_path, exec_name)
            with open(os.devnull, 'w', encoding='utf-8') as devnull:
                subprocess.check_call([cmd, '--version'], stdout=devnull, stderr=devnull)
        except (OSError, subprocess.CalledProcessError):
            logging.info('  failed in %s', base_path)
        else:
            logging.info('  command found: %s', cmd)
            return cmd

    # That did not work: try calling it through Python
    for base_path in search_paths:
        try:
            cmd = [python, os.path.join(base_path, exec_name)]
            with open(os.devnull, 'w', encoding='utf-8') as devnull:
                subprocess.check_call(cmd + ['--version'], stdout=devnull, stderr=devnull)
        except (OSError, subprocess.CalledProcessError):
            logging.info('  failed in %s', base_path)
        else:
            logging.info('  command found: %s', cmd)
            return cmd

    logging.info('  command *not* found in virtualenv!')

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
