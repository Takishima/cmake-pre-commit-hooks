# Copyright 2023 Damien Nguyen <ngn.damien@gmail.com>
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

"""Utility functions and classes for argument parsing."""

import argparse
import os
from pathlib import Path

# ==============================================================================


def _append_in_namespace(namespace, key, values):
    current = getattr(namespace, key, [])
    if current is None:
        current = []
    current.append(values)
    setattr(namespace, key, current)


class OSSpecificAction(argparse.Action):
    def __call__(self, parser, namespace, values, options_string=None):  # noqa: ARG002
        if self.dest == 'unix':
            _append_in_namespace(namespace, 'linux', values)
            _append_in_namespace(namespace, 'mac', values)

        _append_in_namespace(namespace, self.dest, values)


# ==============================================================================


def executable_path(path):
    """
    Argparse validation function.

    Args:
        path (str): Path to some file or directory

    Returns:
        True if `path` points to a file that is executable, False otherwise
    """
    if Path(path).is_file() and os.access(path, os.X_OK):
        return path
    raise argparse.ArgumentTypeError(f'{path} is not a valid file and/or does not appear executable')


# ==============================================================================
