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

"""Wrapper script for include-what-you-use."""

import logging
import shutil
import sys

from ._utils import ClangAnalyzerCmd

log = logging.getLogger(__name__)


def get_iwyu_tool_command(iwyu_tool_names=None):
    """
    Get the path to the iwyu-tool.py executable on the PATH or in the virtual environment.

    Args:
        iwyu_tool_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['iwyu_tool.py', 'iwyu-tool']
    """
    if not iwyu_tool_names:
        iwyu_tool_names = ['iwyu_tool.py', 'iwyu-tool', 'iwyu_tool']

    for iwyu_tool in iwyu_tool_names:
        fname = shutil.which(iwyu_tool)
        if fname:
            log.debug('found iwyu-tool command at %s', fname)
            return fname

    # Nothing worked -> give up!
    return None


def get_iwyu_command(iwyu_names=None):
    """
    Get the path to the include-what-you-use executable on the PATH or in the virtual environment.

    Args:
        iwyu_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['include-what-you-use']
    """
    if not iwyu_names:
        iwyu_names = ['include-what-you-use']

    for iwyu in iwyu_names:
        fname = shutil.which(iwyu)
        if fname:
            log.debug('found iwyu command at %s', fname)
            return fname

    # Nothing worked -> give up!
    return None


class IWYUToolCmd(ClangAnalyzerCmd):
    """Class for the iwyu_tool.py command."""

    lookbehind = 'include-what-you-use '

    def __init__(self, args):
        """
        Initialize an IWYUToolCmd object.

        The version is read from include-what-you-use since iwyu-tool does not have one.
        """
        command = get_iwyu_tool_command()
        if command is None:
            msg = 'Unable to locate path to iwyu-tool'
            raise FileNotFoundError(msg)

        version_command = get_iwyu_command()
        if version_command is None:
            msg = 'Unable to locate path to include-what-you-use executable!'
            raise FileNotFoundError(msg)

        super().__init__(command, self.lookbehind, args)
        self.version_command = version_command
        self.check_installed()
        self.parse_args(args)
        self.handle_ddash_args()
        self.log = logging.getLogger(__name__)

        # Force location of compile database
        compile_db = self._resolve_compilation_database(self.cmake.build_dir, self.build_dir_list)
        if compile_db:
            self.add_if_missing([f'-p={compile_db}'])

    def _parse_output(self, result):
        """
        Parse output and check whether some errors occurred.

        Args:
            result (namedtuple): Result from calling a command

        Returns:
            False if no errors were detected, True in all other cases.

        Notes:
            Include-What-You-Use return code is never 0
        """
        self.log.debug('parsing output from %s', result.stdout)
        is_correct = 'has correct #includes/fwd-decls' in result.stdout
        # NB: when several files are processed at once, the output may contain a mix of correct and incorrect files
        has_suggestions = any(msg in result.stdout for msg in ('should add these lines:', 'should remove these lines:'))

        return has_suggestions or (bool(result.stdout) and not is_correct)


def main(argv=None):
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    if argv is None:
        argv = sys.argv
    cmd = IWYUToolCmd(argv)
    cmd.run()


if __name__ == '__main__':  # pragma: nocover
    main()
