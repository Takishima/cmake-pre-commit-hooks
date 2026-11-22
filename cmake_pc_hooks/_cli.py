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

"""Command line options of the hooks."""

from __future__ import annotations

from types import SimpleNamespace

import click
from click.core import ParameterSource

from . import _config
from ._cmake import CMAKE_OPTIONS

_NOT_SETTINGS = ('files', 'hooks_config', 'dump_toml')


def _toml_type(param: click.Parameter) -> type:
    """Give the type of the TOML value expected for an option."""
    if param.multiple:
        return list
    return bool if param.is_flag else str


def _option_types(command: click.Command) -> dict[str, type]:
    """Give the type of the TOML value expected for each option that can be set from a TOML file."""
    return {param.name: _toml_type(param) for param in command.params if param.name not in _NOT_SETTINGS}


def _load_settings(ctx: click.Context, _param: click.Parameter, value: str | None) -> str | None:
    """Use the settings of the TOML files as default values of the options (callback of `--hooks-config`)."""
    try:
        ctx.default_map = _config.load_settings(ctx.obj, value, _option_types(ctx.command))
    except _config.ConfigError as err:
        raise click.UsageError(str(err), ctx) from err
    return value


HOOK_OPTIONS = [
    click.Option(
        ['--all-at-once'],
        is_flag=True,
        help='Pass all filenames at once to the linter/formatter instead of calling the command once for each file',
    ),
    click.Option(
        ['--read-json-db'],
        is_flag=True,
        help='Run hooks on files found in compile_commands.json (if found and in addition to files specified on CLI)',
    ),
    click.Option(['--version'], help='Perform a version check'),
    click.Option(
        ['--hooks-config'],
        is_eager=True,
        callback=_load_settings,
        help='Path to a TOML configuration file.',
    ),
    click.Option(
        ['--dump-toml'],
        is_flag=True,
        help='Dump the current set of CLI arguments as TOML-formatted output',
    ),
    click.Argument(['files'], nargs=-1, type=click.UNPROCESSED),
]

COMMAND = click.Command(
    'cmake-pc-hook', params=[*CMAKE_OPTIONS, *HOOK_OPTIONS], context_settings={'ignore_unknown_options': True}
)


def parse_args(hook_name: str, args: list[str]) -> tuple[SimpleNamespace, list[str], list[str]]:
    """
    Parse the command line of a hook.

    The options that are not ours are meant for the tool. Everything after a `--` is taken as a filename.

    Returns:
        The options of the hook, the arguments meant for the tool and the filenames.
    """
    after_double_dash = []
    if '--' in args:
        index = args.index('--')
        args, after_double_dash = args[:index], args[index + 1 :]

    ctx = COMMAND.make_context(f'cmake-pc-{hook_name}-hook', list(args), obj=hook_name)
    options = SimpleNamespace(**ctx.params)

    if options.dump_toml:
        click.echo(
            _config.dump_toml(
                {
                    param.name: ctx.params[param.name]
                    for param in COMMAND.params
                    if param.name not in _NOT_SETTINGS
                    and ctx.get_parameter_source(param.name) != ParameterSource.DEFAULT
                }
            ),
            nl=False,
        )
        ctx.exit(0)

    tool_args = [arg for arg in options.files if arg.startswith('-')]
    files = [arg for arg in options.files if not arg.startswith('-')]
    return options, tool_args, [*files, *after_double_dash]
