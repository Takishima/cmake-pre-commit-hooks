#!/usr/bin/env python3
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

"""Wrapper script for lizard."""

from hooks.utils import StaticAnalyzerCmd


class LizardCmd(StaticAnalyzerCmd):
    """Class for the lizard command."""

    command = "lizard"
    lookbehind = ""

    def __init__(self, args):
        """Initialize a LizardCmd object."""
        super().__init__(self.command, self.lookbehind, args)
        self.parse_args(args)

    def set_file_regex(self):
        """Get the file regex for a command's target files from the .pre-commit-hooks.yaml."""
        self.file_regex = r".*\.(?:c|cc|cxx|cpp|cu|h|hpp|hxx|py)$"

    def run(self):
        """Run lizard."""
        for filename in self.files:
            self.run_command([filename] + self.args)
            self.exit_on_error()


def main(argv=None):
    """
    Run command.

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    cmd = LizardCmd(argv)
    cmd.run()


if __name__ == "__main__":
    main()
