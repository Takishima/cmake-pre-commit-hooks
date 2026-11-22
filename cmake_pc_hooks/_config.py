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

"""Settings of the hooks read from TOML files."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from ._hook import HOOK_NAMES

if sys.version_info >= (3, 11):  # pragma: nocover
    import tomllib
else:  # pragma: nocover
    import tomli as tomllib

log = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = 'cmake_pc_hooks.toml'
PYPROJECT_FILE = 'pyproject.toml'
PYPROJECT_SECTION = ('tool', 'cmake_pc_hooks')


class ConfigError(ValueError):
    """Exception raised when the settings of a TOML file are not valid."""


def load_settings(hook_name: str, config_file: str | None, option_types: dict[str, type]) -> dict[str, Any]:
    """
    Load the settings of a hook from the TOML files.

    The files are read in this order, with each one overriding the previous ones:
        1. `pyproject.toml` (table `tool.cmake_pc_hooks`)
        2. `cmake_pc_hooks.toml`
        3. `config_file`, if any

    In each file, the settings found in a table named after the hook override the common ones.

    Args:
        hook_name: Name of the hook
        config_file: Path to an extra TOML file, which must exist
        option_types: Type of the value expected for each valid setting
    """
    settings = {}
    for path, section in ((Path(PYPROJECT_FILE), PYPROJECT_SECTION), (Path(DEFAULT_CONFIG_FILE), ())):
        settings.update(_hook_settings(_read_table(path, section), hook_name, option_types, path))

    if config_file:
        path = Path(config_file)
        if not path.is_file():
            msg = f'Unable to locate TOML file {path}'
            raise ConfigError(msg)
        settings.update(_hook_settings(_read_table(path), hook_name, option_types, path))
    return settings


def dump_toml(settings: dict[str, Any]) -> str:
    """Format some settings as the content of a TOML file."""
    return ''.join(f'{key} = {_toml_value(value)}\n' for key, value in settings.items())


def _toml_value(value: object) -> str:
    """Format a boolean, a string, a path or a list of those as a TOML value."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple)):
        return f'[{", ".join(_toml_value(element) for element in value)}]'
    return json.dumps(str(value), ensure_ascii=False)


def _read_table(path: Path, section: tuple[str, ...] = ()) -> dict[str, Any]:
    """Read a table of a TOML file. The result is empty if the file or the table does not exist."""
    try:
        with path.open('rb') as fd:
            table = tomllib.load(fd)
    except FileNotFoundError:
        log.debug('TOML file %s does not exist (not an error)', path)
        return {}
    except tomllib.TOMLDecodeError as err:
        msg = f'{path} is not a valid TOML file: {err}'
        raise ConfigError(msg) from err

    for name in section:
        table = table.get(name, {})
    log.debug('Loading data from %s', path)
    return table


def _hook_settings(table: dict[str, Any], hook_name: str, option_types: dict[str, type], path: Path) -> dict[str, Any]:
    """Check all the settings of a table and return those that apply to a hook."""
    common = {key: value for key, value in table.items() if key not in HOOK_NAMES}
    _check_settings(common, option_types, str(path))

    for name in HOOK_NAMES:
        if name in table:
            if not isinstance(table[name], dict):
                msg = f'"{name}" in {path} must be a table'
                raise ConfigError(msg)
            _check_settings(table[name], option_types, f'table "{name}" of {path}')

    return {**common, **table.get(hook_name, {})}


def _check_settings(settings: dict[str, Any], option_types: dict[str, type], where: str) -> None:
    """Make sure that some settings are known options of the hooks and have the expected type."""
    for key, value in settings.items():
        if key not in option_types:
            msg = f'unknown option "{key}" in {where}'
            raise ConfigError(msg)
        if not isinstance(value, option_types[key]):
            msg = f'option "{key}" in {where} must be of type {option_types[key].__name__}'
            raise ConfigError(msg)
