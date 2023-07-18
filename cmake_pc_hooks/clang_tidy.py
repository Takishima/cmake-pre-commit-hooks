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

"""Wrapper script for clang-tidy."""

import logging
import sys

from ._utils import ClangAnalyzerCmd


class ClangTidyCmd(ClangAnalyzerCmd):
    """Class for the clang-tidy command."""

    command = 'clang-tidy'
    lookbehind = 'LLVM version '

    def __init__(self, args):
        """Initialize a ClangTidyCmd object."""
        super().__init__(self.command, self.lookbehind, args)
        self.parse_args(args)
        self.edit_in_place = '-fix' in self.args or '--fix-errors' in self.args
        self.handle_ddash_args()

        compile_db = self._resolve_compilation_database(self.cmake.build_dir, self.build_dir_list)
        if not self.cmake.no_cmake_configure or compile_db:
            self.add_if_missing([f'-p={compile_db}'])

    def _parse_output(self, result):
        """
        Parse output and check whether some errors occurred.

        Args:
            result (namedtuple): Result from calling a command

        Returns:
            False if no errors were detected, True in all other cases.
        """
        # Reset stderr if it's complaining about problems in system files
        if not result.stdout or 'non-user code' in result.stderr:
            result.stderr = ''

        logging.debug('returncode %d', result.returncode)
        logging.debug('parsing output from %s', result.stderr)
        return result.returncode != 0 or any(
            msg in result.stderr
            for msg in (
                'error generated.',
                'errors generated.',
                'warning treated as error',
                'warnings treated as errors',
            )
        )


def main(argv=None):
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    if argv is None:
        argv = sys.argv
    cmd = ClangTidyCmd(argv)
    cmd.run()


if __name__ == '__main__':  # pragma: nocover
    main()
