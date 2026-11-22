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

"""Wrapper script for cpplint."""

import sys

from . import _call_process
from ._utils import StaticAnalyzerCmd


class CpplintCmd(StaticAnalyzerCmd):
    """Class for the cpplint command."""

    command = 'cpplint'
    lookbehind = 'cpplint '

    def __init__(self, args):
        """Initialize a CpplintCmd object."""
        super().__init__(self.command, self.lookbehind, args)
        self.check_installed()
        self.parse_args(args)
        self.add_if_missing(['--verbose=0'])

    def run_command(self, filenames):
        """Run the command with the options before the filenames, as cpplint requires."""
        self.history.append(_call_process.call_process([self.command, *self.args, *filenames]))


def main(argv=None):
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    if argv is None:
        argv = sys.argv

    cmd = CpplintCmd(argv)
    cmd.run()


if __name__ == '__main__':  # pragma: nocover
    main()
