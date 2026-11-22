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

"""Description of a hook."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._call_process import History


HOOK_NAMES = ('clang-format', 'clang-tidy', 'cppcheck', 'cpplint', 'include-what-you-use', 'lizard')


def has_failed(result: History) -> bool:
    """Tell whether a tool failed by looking at its return code."""
    return result.returncode != 0


def has_failed_quiet_on_success(result: History) -> bool:
    """Tell whether a tool failed by looking at its return code and hide its output if it succeeded."""
    if result.returncode == 0:
        result.disable_print_output()
    return result.returncode != 0


@dataclass(frozen=True)
class Hook:
    """Description of a hook: which tool it runs and how."""

    name: str
    """Name of the tool."""

    version_prefix: str = ''
    """Text that comes right before the version number in the output of `<tool> --version`."""

    executables: tuple[str, ...] = ()
    """Names under which the tool may be installed (defaults to `name`)."""

    version_executables: tuple[str, ...] = ()
    """Names of the executable to ask for the version, if it is not the tool itself."""

    default_args: tuple[str, ...] = ()
    """Options added to the command line unless the user already set them (with any value)."""

    compile_db_arg: str | None = None
    """
    Option used to pass the compilation database, e.g. `-p={}`.

    Hooks that define it always run a CMake configure step. The others only do so when `--read-json-db` is used.
    """

    double_dash: bool = False
    """Whether arguments after `--` are compiler options to place at the end of the command line."""

    options_first: bool = False
    """Whether the tool requires its options to come before the filenames."""

    file_arg: Callable[[str], str] = str
    """Function to convert a filename into the argument passed to the tool."""

    check: Callable[[History], bool] = has_failed
    """Function that tells whether a call to the tool failed. It may also edit the output to display."""

    formatter: bool = False
    """Whether the tool is a formatter: the hook then fails if a file differs from its formatted version."""
