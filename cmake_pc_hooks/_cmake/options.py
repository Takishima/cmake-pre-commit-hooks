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

"""Command line options related to CMake."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from cmake_pc_hooks import _argparse

if TYPE_CHECKING:
    import argparse

_KEYWORD_ARGS = {
    'defines': '-D{}',
    'undefines': '-U{}',
    'errors': '-Werror={}',
    'no_errors': '-Wno-error={}',
    'generator': '-G{}',
    'toolset': '-T{}',
    'platform': '-A{}',
    'preset': '--preset={}',
}
_FLAG_ARGS = {'dev_warnings': '-Wdev', 'no_dev_warnings': '-Wno-dev'}
_PLATFORM_ARGS = {'linux': 'Linux', 'mac': 'Darwin', 'win': 'Windows'}


def add_cmake_arguments_to_parser(parser: argparse.ArgumentParser) -> None:
    """
    Add CMake options to an argparse.ArgumentParser.

    The option groups are all created first in order to control the order in which they show in the help message.
    """
    cmake_options = parser.add_argument_group(
        title='CMake options',
        description='Options mirroring those of CMake and that will be passed onto CMake as-is.',
    )
    options = parser.add_argument_group(
        title='Other CMake related options',
        description='Options used to configure how CMake is called',
    )
    platform_specific_cmake = parser.add_argument_group(
        title='Options to define platform-dependent CMake variables',
        description=(
            'This allows you to set CMake variables during the configuration depending on the platform the hooks '
            'are currently running on.'
            'For example --unix="CMAKE_CXX_COMPILER=g++" will only define this CMake variable on UNIX platforms.'
        ),
    )

    options.add_argument('--clean', action='store_true', help='Start from a clean build directory')
    options.add_argument(
        '--cmake',
        type=_argparse.executable_path,
        help='Specify path to CMake executable.',
    )
    options.add_argument(
        '--cmake-build-target',
        action='append',
        dest='build_targets',
        type=str,
        help=(
            'Build a CMake target after the configure step and before running the hook, e.g. to generate source '
            'files (may be specified multiple times)'
        ),
        default=[],
    )
    options.add_argument(
        '--codegen',
        action='store_true',
        help=(
            'Build the `codegen` CMake target after the configure step in order to generate source files '
            '(requires CMake >= 3.31 and a Ninja or Makefile generator)'
        ),
    )
    options.add_argument(
        '--detect-configured-files',
        action='store_true',
        help='Enable tracing of files generated  using the configure_file(...) CMake function',
    )
    options.add_argument(
        '--no-automatic-discovery',
        action='store_false',
        dest='automatic_discovery',
        help='Do not attempt to automatically look for a build directory',
    )
    options.add_argument(
        '--no-cmake-configure',
        action='store_true',
        dest='no_cmake_configure',
        help=(
            'Do not call CMake configure to generate a compilation database '
            '(ie. do not call CMake but still try to locate a compilation database if possible)'
        ),
    )

    platform_specific_cmake.add_argument(
        '--unix',
        action=_argparse.OSSpecificAction,
        type=str,
        help='Unix-only (ie. Linux and MacOS) options for CMake',
    )
    platform_specific_cmake.add_argument(
        '--linux',
        action=_argparse.OSSpecificAction,
        type=str,
        help='Linux-only options for CMake',
    )
    platform_specific_cmake.add_argument(
        '--mac',
        action=_argparse.OSSpecificAction,
        type=str,
        help='Mac-only options for CMake',
    )
    platform_specific_cmake.add_argument(
        '--win',
        action=_argparse.OSSpecificAction,
        type=str,
        help='Windows-only options for CMake',
    )

    cmake_options.add_argument('-S', '--source-dir', type=str, help='Path to build directory', default='.')
    cmake_options.add_argument(
        '-B',
        '--build-dir',
        action='append',
        type=str,
        help='Path to build directory',
    )
    cmake_options.add_argument(
        '-D',
        dest='defines',
        action='append',
        type=str,
        help='Create or update a cmake cache entry.',
        default=[],
    )
    cmake_options.add_argument(
        '-U',
        dest='undefines',
        action='append',
        type=str,
        help='Remove matching entries from CMake cache.',
        default=[],
    )
    cmake_options.add_argument('-G', dest='generator', type=str, help='Specify a build system generator.')
    cmake_options.add_argument(
        '-T',
        dest='toolset',
        type=str,
        help='Specify toolset name if supported by generator.',
    )
    cmake_options.add_argument(
        '-A',
        dest='platform',
        type=str,
        help='Specify platform if supported by generator.',
    )
    cmake_options.add_argument(
        '-Werror',
        dest='errors',
        choices=['dev'],
        help='Make developer warnings errors.',
        default=[],
    )
    cmake_options.add_argument(
        '-Wno-error',
        dest='no_errors',
        choices=['dev'],
        help='Make developer warnings not errors.',
        default=[],
    )
    cmake_options.add_argument('--preset', type=str, help='Specify a configure preset.')

    cmake_options.add_argument(
        '-Wdev',
        dest='dev_warnings',
        action='store_true',
        help='Enable developer warnings.',
    )
    cmake_options.add_argument(
        '-Wno-dev',
        dest='no_dev_warnings',
        action='store_true',
        help='Suppress developer warnings.',
    )


def _cmake_args(args: argparse.Namespace) -> list[str]:
    """Convert the parsed options into the arguments to pass on to CMake."""
    cmake_args = []
    for key, format_str in _KEYWORD_ARGS.items():
        value = getattr(args, key)
        values = [value] if isinstance(value, str) else value or []
        cmake_args.extend(format_str.format(element) for element in values)

    cmake_args.extend(flag for key, flag in _FLAG_ARGS.items() if getattr(args, key))

    for key, system in _PLATFORM_ARGS.items():
        if platform.system() == system:
            cmake_args.extend(arg.strip('"\'') for arg in getattr(args, key) or [])
    return cmake_args


@dataclass
class CMakeOptions:
    """Options that control how CMake is called."""

    source_dir: Path = field(default_factory=Path)
    """Path to the source directory."""

    build_dirs: list[str] = field(default_factory=list)
    """Candidate build directories, by order of preference."""

    cmake: Path | None = None
    """Path to the CMake executable, if it should not be looked up."""

    no_cmake_configure: bool = False
    """Whether to skip the CMake configure step."""

    automatic_discovery: bool = True
    """Whether to look for an existing build directory inside the source directory."""

    detect_configured_files: bool = False
    """Whether to trace CMake in order to detect the files generated by `configure_file()`."""

    build_targets: list[str] = field(default_factory=list)
    """CMake targets to build after the configure step."""

    codegen: bool = False
    """Whether to build the `codegen` CMake target after the configure step."""

    cmake_args: list[str] = field(default_factory=list)
    """Arguments passed on to CMake as-is."""

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> CMakeOptions:
        """Create the options from the result of a parser set up with `add_cmake_arguments_to_parser()`."""
        return cls(
            source_dir=Path(args.source_dir),
            build_dirs=list(args.build_dir or []),
            cmake=Path(args.cmake) if args.cmake else None,
            no_cmake_configure=args.no_cmake_configure,
            automatic_discovery=args.automatic_discovery,
            detect_configured_files=args.detect_configured_files,
            build_targets=list(args.build_targets or []),
            codegen=bool(args.codegen),
            cmake_args=_cmake_args(args),
        )
