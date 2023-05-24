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

"""Custom argument parser to support parsing from TOML config files."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import toml

# ==============================================================================


def _append_in_namespace(namespace, key, values):
    current = getattr(namespace, key, [])
    if current is None:
        current = []
    current.append(values)
    setattr(namespace, key, current)


class OSSpecificAction(argparse.Action):
    """Custom action to support platform-specific arguments."""

    def __call__(self, parser, namespace, values, options_string=None):  # noqa: ARG002
        if self.dest == 'unix':
            _append_in_namespace(namespace, 'linux', values)
            _append_in_namespace(namespace, 'mac', values)

        _append_in_namespace(namespace, self.dest, values)


# ==============================================================================


def executable_path(path: str) -> Path:
    """
    Argparse validation function.

    Args:
        path: Path to some file or directory

    Returns:
        True if `path` points to a file that is executable, False otherwise

    Raises:
        argparse.ArgumentTypeError if path does not point to an executable file.
    """
    if Path(path).is_file() and os.access(path, os.X_OK):
        return path
    raise argparse.ArgumentTypeError(f'{path} is not a valid file and/or does not appear executable')


# ==============================================================================


def _load_data_from_toml(
    path: Path, section: str, path_must_exist: bool = True, section_must_exist: bool = True
) -> dict:
    """
    Load a TOML file and return the corresponding config dictionary.

    Note:
        If no section is specified, this function will only return the dictionary containing the first level of
        elements (ie. no nested sections).

    Args:
        namespace: Namespace to store results into
        path: Path to TOML file
        section: Name of section to load in TOML file
        path_must_exist: Whether a missing TOML file is considered an error or not
        section_must_exist: Whether a missing section in the TOML file is considered an error or not
    """
    try:
        with path.open(mode='r') as fd:
            config = toml.load(fd)
        if section:
            for sub_section in section.split('.'):
                config = config[sub_section]
            logging.debug('Loading data from %s table of %s', section, path)
        else:
            config = {key: value for key, value in config.items() if not isinstance(value, dict)}
            logging.debug('Loading data from root table of %s', path)
        return config
    except FileNotFoundError as err:
        if path_must_exist:
            raise FileNotFoundError(f'Unable to locate TOML file {path}') from err
        logging.debug('TOML file %s does not exist (not an error)', str(path))
    except KeyError as err:
        if section_must_exist:
            raise KeyError(f'Unable to locate section {section} in TOML file {path}') from err
        logging.debug('TOML file %s does not have a %s section (not an error)', str(path), section)
    return {}


# ==============================================================================


class ArgumentParser(argparse.ArgumentParser):
    """
    A wrapper of the argparse.ArgumentParser class that supports loading from TOML files.

    This class extends the functionality of the standard argparse.ArgumentParser by allowing users to specify default
    values for arguments in a TOML file, in addition to the command line.

    Argument are parsed from either the CLI or an optional TOML file using the following hierarchy:
        1. Arguments passed through the command line are selected over TOML
           arguments, even if both are passed
        2. Arguments from a TOML file if specified using the --config CLI argument
        3. Arguments from a default TOML config file location
        4. Arguments from an existing pyproject.toml file location
    """

    def __init__(
        self,
        *args: Any,
        default_config_name: str = None,
        pyproject_section_name: str = None,
        args_groups: list[dict] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize an instance of ArgumentParser.

        Keyword Args:
            default_config_name (str): Default name for a TOML configuration file
            pyproject_section_name (str): Name of section to look for in pyproject.toml file
            args_groups: List of argument groups to create. Items are dictionaries with keywords to pass onto
                add_argument_group()
            args: Same as for argparse.ArgumentParser()
            kwargs: Same as for argparse.ArgumentParser()
        """
        self._default_config_name = default_config_name
        self._pyproject_section_name = pyproject_section_name
        self.groups = []

        super().__init__(*args, **kwargs)

        if args_groups is not None:
            for arg_group in args_groups:
                self.groups.append(self.add_argument_group(**arg_group))

        group = self.add_argument_group(title='TOML options')
        group.add_argument(
            '--config',
            type=str,
            default='',
            help='Path to a TOML configuration file.',
        )
        group.add_argument(
            '--dump-toml',
            action='store_true',
            help='Dump the current set of CLI arguments as TOML-formatted output',
        )
        self._default_args = {}

    def parse_known_args(self, args: list = None, namespace: argparse.Namespace = None) -> argparse.Namespace:
        """
        Convert argument strings to objects and assign them as attributes of the namespace.

        Args:
            args: List of strings to parse. The default is taken from sys.argv.
            namespace: An object to take the attributes. The default is a new empty Namespace object.

        Return:
            The populated namespace.
        """
        # 1. Attempt to parse from pyproject.toml
        # 2. Attempt to parse from default config file
        # 3. Attempt to parse from TOML config file from CLI
        # 4. Use CLI arguments or default values

        tmp, _ = super().parse_known_args([])
        self._default_args = vars(tmp)

        if namespace is None:
            namespace = argparse.Namespace()

        if self._pyproject_section_name is not None:
            namespace = self._load_from_toml(
                namespace=namespace,
                path=Path('pyproject.toml'),
                section=self._pyproject_section_name,
                path_must_exist=False,
                section_must_exist=False,
            )

        if self._default_config_name is not None:
            namespace = self._load_from_toml(
                namespace=namespace, path=Path(self._default_config_name), path_must_exist=False
            )

        namespace, args = super().parse_known_args(args=args, namespace=namespace)
        if namespace.config:
            overridable_keys = set()
            for key, value in vars(namespace).items():
                default_value = self._default_args[key]
                if value == default_value:
                    overridable_keys.add(key)
            namespace = self._load_from_toml(
                namespace=namespace,
                path=Path(namespace.config),
                path_must_exist=True,
                overridable_keys=overridable_keys,
            )

        if namespace.dump_toml:
            exclude_keys = {'positionals', 'dump_toml'}
            print(
                toml.dumps(
                    {
                        key: value
                        for key, value in vars(namespace).items()
                        if value != self._default_args[key] and key not in exclude_keys
                    }
                )
            )
            sys.exit(0)

        return namespace, args

    def _load_from_toml(  # noqa: PLR0913
        self,
        namespace: argparse.Namespace,
        path: Path,
        section: str = '',
        path_must_exist: bool = True,
        section_must_exist: bool = True,
        overridable_keys: set = None,
    ) -> None:
        """
        Load a TOML file and set the attributes within the argparse namespace object.

        Args:
            namespace: Namespace to store results into
            path: Path to TOML file
            section: Name of section to load in TOML file
            path_must_exist: Whether a missing TOML file is considered an error or not
            section_must_exist: Whether a missing section in the TOML file is considered an error or not
            overridable_keys: List of keys that can be overridden by values in the TOML file
        """
        config = _load_data_from_toml(path, section, path_must_exist, section_must_exist)

        for key, value in config.items():
            if key not in self._default_args:
                self.error(f'unrecognized arguments: "{key}"')

            # NB: we can only do proper type check if the default value is given...
            default_value = self._default_args[key]
            if default_value is not None and not isinstance(value, type(default_value)):
                raise argparse.ArgumentTypeError(
                    f'TOML value type {type(value)} not compatible with parser argument '
                    f'{type(default_value)} for key "{key}"'
                )
            if overridable_keys is not None and key not in overridable_keys:
                logging.debug('  skipping non-overridable key: "%s"', key)
                continue

            logging.debug('  setting %s = %s', key, value)
            setattr(namespace, key, value)
        return namespace
