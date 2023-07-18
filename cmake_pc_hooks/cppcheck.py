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

"""Wrapper script for cppcheck."""

import logging
import sys
from pathlib import Path

from . import _call_process
from ._utils import Command


class CppcheckCmd(Command):
    """Class for the cppcheck command."""

    command = 'cppcheck'
    lookbehind = 'Cppcheck '

    def __init__(self, args):
        """Initialize a CppcheckCmd object."""
        super().__init__(self.command, self.lookbehind, args)
        self.parse_args(args)
        # quiet for stdout purposes
        self.add_if_missing(['-q'])
        # make cppcheck behave as expected for pre-commit
        self.add_if_missing(['--error-exitcode=1'])
        # Enable all of the checks
        self.add_if_missing(['--enable=all'])

        compile_db = self._resolve_compilation_database(self.cmake.build_dir, self.build_dir_list)
        if not self.cmake.no_cmake_configure or compile_db:
            self.add_if_missing([f'--project={compile_db}'])

    def run_command(self, filenames):
        """Run the command and check for errors."""
        filter_args = [f'--file-filter=*{Path(filename).parent.name}/{Path(filename).name}' for filename in filenames]
        self.history.append(_call_process.call_process([self.command, *filter_args, *self.args, *self.ddash_args]))
        self._clinters_compat()

    def _parse_output(self, result):
        """
        Parse output and check whether some errors occurred.

        Args:
            result (namedtuple): Result from calling a command

        Returns:
            False if no errors were detected, True in all other cases.
        """
        # Useless error see https://stackoverflow.com/questions/6986033
        logging.debug('parsing output from %s', result.stderr)
        useless_error_part = 'Cppcheck cannot find all the include files'
        result.stderr = ''.join(
            [line for line in result.stderr.splitlines(keepends=True) if useless_error_part not in line]
        )
        self._clinters_compat()
        return result.returncode != 0


def main(argv=None):
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    if argv is None:
        argv = sys.argv
    cmd = CppcheckCmd(argv)
    cmd.run()


if __name__ == '__main__':  # pragma: nocover
    main()
