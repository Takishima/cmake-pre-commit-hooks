#   Copyright 2023 Damien Nguyen <ngn.damien@gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Sub-process handling classes and functions."""

from __future__ import annotations

import logging
import subprocess as sp
import sys


class History:  # pylint: disable=too-few-public-methods
    """Process execution data."""

    __slots__ = ('stdout', 'stderr', 'returncode')

    def __init__(self, stdout, stderr, returncode):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def to_stdout_and_stderr(self):
        """Copy the relevant content to the standard output and error streams."""
        sys.stdout.write(self.stdout)
        sys.stdout.flush()
        sys.stderr.write(self.stderr)
        sys.stderr.flush()


def call_process(args: list, **kwargs: any) -> History:
    """
    Call a process using subprocess and save the output for later use.

    Args:
        args: Arguments to pass onto subprocess.run()
        kwargs: Keyword arguments to pass onto subprocess.run()

    Returns:
        A History object instance.
    """
    try:
        sp_child = sp.run(args, check=True, capture_output=True, **kwargs)
    except sp.CalledProcessError as err:
        ret = History(err.stdout.decode(), err.stderr.decode(), err.returncode)
    else:
        ret = History(sp_child.stdout.decode(), sp_child.stderr.decode(), sp_child.returncode)

    logging.debug('command `%s` exited with %d', ' '.join(args), ret.returncode)
    for line in ret.stdout.split('\n'):
        logging.debug('(stdout) %s', line)
    for line in ret.stderr.split('\n'):
        logging.debug('(stderr) %s', line)
    return ret
