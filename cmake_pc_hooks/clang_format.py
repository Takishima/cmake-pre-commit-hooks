# -*- coding: utf-8 -*-
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

"""Wrapper script for clang-format."""

import sys

from ._utils import FormatterCmd


class ClangFormatCmd(FormatterCmd):
    """Class for the ClangFormat command."""

    command = "clang-format"
    lookbehind = "clang-format version "

    def __init__(self, args):
        """Initialize a ClangFormatCmd object."""
        super().__init__(self.command, self.lookbehind, args)
        self.check_installed()
        self.parse_args(args)
        self.set_diff_flag()
        self.edit_in_place = "-i" in self.args

    def run(self):
        """Run clang-format. Error if diff is incorrect."""
        for filename in self.files:
            self.compare_to_formatted(filename)
        if self.returncode != 0:
            sys.stdout.buffer.write(self.stderr)
            sys.exit(self.returncode)


def main():
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    cmd = ClangFormatCmd(sys.argv[1:])
    cmd.run()


if __name__ == "__main__":
    main()
