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

import click

if TYPE_CHECKING:
    from types import SimpleNamespace

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
_PLATFORM_ARGS = {'Linux': ('unix', 'linux'), 'Darwin': ('unix', 'mac'), 'Windows': ('win',)}

CMAKE_OPTIONS = [
    click.Option(
        ['-S', '--source-dir'],
        type=click.Path(exists=True, file_okay=False, path_type=Path),
        default='.',
        help='Explicitly specify a source directory.',
    ),
    click.Option(['-B', '--build-dir'], multiple=True, help='Explicitly specify a build directory.'),
    click.Option(['-D', 'defines'], multiple=True, help='Create or update a cmake cache entry.'),
    click.Option(['-U', 'undefines'], multiple=True, help='Remove matching entries from CMake cache.'),
    click.Option(['-G', 'generator'], help='Specify a build system generator.'),
    click.Option(['-T', 'toolset'], help='Specify toolset name if supported by generator.'),
    click.Option(['-A', 'platform'], help='Specify platform if supported by generator.'),
    click.Option(
        ['-Werror', 'errors'], type=click.Choice(['dev']), multiple=True, help='Make developer warnings errors.'
    ),
    click.Option(
        ['-Wno-error', 'no_errors'],
        type=click.Choice(['dev']),
        multiple=True,
        help='Make developer warnings not errors.',
    ),
    click.Option(['--preset'], help='Specify a configure preset.'),
    click.Option(['-Wdev', 'dev_warnings'], is_flag=True, help='Enable developer warnings.'),
    click.Option(['-Wno-dev', 'no_dev_warnings'], is_flag=True, help='Suppress developer warnings.'),
    click.Option(['--clean'], is_flag=True, help='Start from a clean build directory'),
    click.Option(
        ['--cmake'],
        type=click.Path(exists=True, dir_okay=False, executable=True, path_type=Path),
        help='Specify path to CMake executable.',
    ),
    click.Option(
        ['--cmake-build-target', 'build_targets'],
        multiple=True,
        help=(
            'Build a CMake target after the configure step and before running the hook, e.g. to generate source '
            'files (may be specified multiple times)'
        ),
    ),
    click.Option(
        ['--codegen'],
        is_flag=True,
        help=(
            'Build the `codegen` CMake target after the configure step in order to generate source files '
            '(requires CMake >= 3.31 and a Ninja or Makefile generator)'
        ),
    ),
    click.Option(
        ['--detect-configured-files'],
        is_flag=True,
        help='Enable tracing of files generated using the configure_file(...) CMake function',
    ),
    click.Option(
        ['--no-automatic-discovery', 'automatic_discovery'],
        flag_value=False,
        default=True,
        help='Do not attempt to automatically look for a build directory',
    ),
    click.Option(
        ['--no-cmake-configure'],
        is_flag=True,
        help=(
            'Do not call CMake configure to generate a compilation database '
            '(ie. do not call CMake but still try to locate a compilation database if possible)'
        ),
    ),
    click.Option(['--unix'], multiple=True, help='Unix-only (ie. Linux and MacOS) options for CMake'),
    click.Option(['--linux'], multiple=True, help='Linux-only options for CMake'),
    click.Option(['--mac'], multiple=True, help='Mac-only options for CMake'),
    click.Option(['--win'], multiple=True, help='Windows-only options for CMake'),
]


def _cmake_args(args: SimpleNamespace) -> list[str]:
    """Convert the parsed options into the arguments to pass on to CMake."""
    cmake_args = []
    for key, format_str in _KEYWORD_ARGS.items():
        value = getattr(args, key)
        values = [value] if isinstance(value, str) else value or []
        cmake_args.extend(format_str.format(element) for element in values)

    cmake_args.extend(flag for key, flag in _FLAG_ARGS.items() if getattr(args, key))

    for key in _PLATFORM_ARGS.get(platform.system(), ()):
        cmake_args.extend(arg.strip('"\'') for arg in getattr(args, key))
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
    def from_namespace(cls, args: SimpleNamespace) -> CMakeOptions:
        """Create the options from the values of the `CMAKE_OPTIONS` command line options."""
        return cls(
            source_dir=args.source_dir,
            build_dirs=list(args.build_dir),
            cmake=args.cmake,
            no_cmake_configure=args.no_cmake_configure,
            automatic_discovery=args.automatic_discovery,
            detect_configured_files=args.detect_configured_files,
            build_targets=list(args.build_targets),
            codegen=args.codegen,
            cmake_args=_cmake_args(args),
        )
