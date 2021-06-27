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

"""Wrapper script for cppcheck."""

from pathlib import Path
import sys
import shutil


from ._utils import ClangAnalyzerCmd


def get_iwyu_tool_command(iwyu_tool_names=None):
    """
    Get the path to the iwyu-tool.py executable on the PATH or in the virtual environment

    Args:
        iwyu_tool_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['iwyu_tool.py', 'iwyu-tool']
    """
    if not iwyu_tool_names:
        iwyu_tool_names = ['iwyu_tool.py', 'iwyu-tool', 'iwyu_tool']

    for iwyu_tool in iwyu_tool_names:
        fname = shutil.which(iwyu_tool)
        if fname:
            return fname

    # Nothing worked -> give up!
    return None


def get_iwyu_command(iwyu_names=None):
    """
    Get the path to the include-what-you-use executable on the PATH or in the virtual environment

    Args:
        iwyu_names (:obj:`list` of :obj:`str`): Names for the CMake command
            Defaults to ['include-what-you-use']
    """
    if not iwyu_names:
        iwyu_names = ['include-what-you-use']

    for iwyu in iwyu_names:
        fname = shutil.which(iwyu)
        if fname:
            return fname

    # Nothing worked -> give up!
    return None


class IWYUToolCmd(ClangAnalyzerCmd):
    """Class for the iwyu_tool.py command."""

    command = get_iwyu_tool_command()
    command_for_version = get_iwyu_command()
    lookbehind = "include-what-you-use "

    def __init__(self, args):
        if self.command is None:
            raise RuntimeError('Unable to locate path to iwyu-tool')
        if self.command_for_version is None:
            raise RuntimeError('Unable to locate path to include-what-you-use executable!')

        super().__init__(self.command, self.lookbehind, args)
        self.check_installed()
        self.parse_args(args)
        self.handle_ddash_args()

        # Force location of compile database
        self.add_if_missing([f'-p={Path(self.build_dir, "compile_commands.json")}'])

    def get_version_str(self):
        """Get the version string like 8.0.0 for a given command."""
        args = [self.command_for_version, '--version']
        sp_child = sp.run(args, stdout=sp.PIPE, stderr=sp.PIPE)
        version_str = str(sp_child.stdout, encoding='utf-8')
        # After version like `8.0.0` is expected to be '\n' or ' '
        if not re.search(self.look_behind, version_str):
            self.raise_error(
                'getting version',
                'The version format for this command has changed. Create an issue at '
                'github.com/Takishima/cmake-pre-commit-hooks.',
            )
        regex = self.look_behind + r'((?:\d+\.)+[\d+_\+\-a-z]+)'
        version = re.search(regex, version_str).group(1)
        return version

    def run(self):
        """Run iwyu_tool command"""
        self.run_cmake_configure()
        error_output = []
        for filename in self.files:
            self.run_command(filename)
            error_output.extend(self.parse_output())

        if error_output:
            self.raise_error("Include-What-You-Use violations found\n", ''.join(error_output))

    def parse_output(self):
        """
        Include-What-You-Use return code is never 0
        Figure out what it is based on stdout and return that instead
        """
        is_correct = "has correct #includes/fwd-decls" in self.stdout

        if not is_correct and self.stdout:
            output = ''
            for line in self.stdout.split('\n'):
                if line and not line[0] == '#':
                    output += line + '\n'
            for line in self.stderr.split('\n'):
                if line and not line[0] == '#':
                    output += line + '\n'
            self.stdout = ''
            self.stderr = ''
            return [output]
        return []


def main():
    """
    Main function

    Args:
        argv (:obj:`list` of :obj:`str`): list of arguments
    """
    cmd = IWYUToolCmd(sys.argv[1:])
    cmd.run()


if __name__ == "__main__":
    main()
