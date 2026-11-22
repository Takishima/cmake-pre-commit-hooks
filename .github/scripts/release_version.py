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

"""Determine the version of the next release from the changelog fragments."""

# Usage: release_version.py [auto|scheduled|patch|minor|major|<version>]
#
# The version (without leading "v") is printed and written to the `version` output of the GitHub Actions step. Nothing
# is written if a scheduled run finds nothing worth releasing.

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

FRAGMENTS_DIR = Path('changelog.d')
CHANGELOG = Path('CHANGELOG.md')

# Fragment types (see [tool.towncrier] in pyproject.toml) that users notice, and the version bump they call for
BUMPS = {
    'added': 'minor',
    'changed': 'minor',
    'deprecated': 'minor',
    'removed': 'minor',
    'fixed': 'patch',
    'security': 'patch',
}

VERSION = re.compile(r'\d+\.\d+\.\d+(-[0-9a-z.]+)?')


def fragment_types(directory: Path) -> set[str]:
    """Return the types of the fragments found in a directory (`<name>.<type>.md` or `<name>.<type>.<n>.md`)."""
    types = set()
    for fragment in directory.glob('*.*.md'):
        parts = fragment.name.split('.')
        types.add(parts[-3] if parts[-2].isdigit() else parts[-2])
    return types


def latest_version(changelog: str) -> tuple[int, int, int]:
    """Return the latest stable version listed in a changelog."""
    match = re.search(r'^## \[v?(\d+)\.(\d+)\.(\d+)\]', changelog, flags=re.MULTILINE)
    if not match:
        msg = 'unable to find the latest release in the changelog: please give an explicit version'
        raise ValueError(msg)
    major, minor, patch = (int(number) for number in match.groups())
    return major, minor, patch


def next_version(request: str, types: set[str], latest: tuple[int, int, int]) -> str | None:
    """Return the version to release, or None if a scheduled run has nothing worth releasing."""
    # The request is `auto`, `scheduled`, `patch`, `minor`, `major` or an explicit version. The bump for `auto` and
    # `scheduled` is deduced from the types of the changelog fragments waiting to be released, starting from the
    # latest released version.
    request = request.strip().lower()
    scheduled = request == 'scheduled'

    if not types:
        if scheduled:
            return None
        msg = 'no changelog fragment: nothing to release'
        raise ValueError(msg)

    if request in {'auto', 'scheduled'}:
        bumps = {BUMPS[kind] for kind in types if kind in BUMPS}
        if scheduled and not bumps:
            return None  # only repository maintenance: not worth a release
        request = 'minor' if 'minor' in bumps else 'patch'

    major, minor, patch = latest
    if request == 'major':
        return f'{major + 1}.0.0'
    if request == 'minor':
        return f'{major}.{minor + 1}.0'
    if request == 'patch':
        return f'{major}.{minor}.{patch + 1}'

    version = request.removeprefix('v')
    if not VERSION.fullmatch(version):
        msg = f"'{request}' is not valid: expected auto, patch, minor, major or a version such as v1.2.3 or v1.2.3-rc.1"
        raise ValueError(msg)
    return version


def tag_exists(tag: str) -> bool:
    """Check whether a tag exists on the remote repository."""
    result = subprocess.run(
        ['git', 'ls-remote', '--exit-code', '--tags', 'origin', f'refs/tags/{tag}'],  # ruff: ignore[start-process-with-partial-path]
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main(argv: list[str]) -> int:
    """Print the next version and pass it on to the following workflow steps."""
    request = argv[1] if len(argv) > 1 else 'auto'
    try:
        version = next_version(
            request, fragment_types(FRAGMENTS_DIR), latest_version(CHANGELOG.read_text(encoding='utf-8'))
        )
        if version and tag_exists(f'v{version}'):
            msg = f'tag v{version} already exists'
            raise ValueError(msg)  # ruff: ignore[raise-within-try]
    except ValueError as error:
        print(f'::error::{error}')
        return 1

    if version is None:
        print('::notice::No user-facing change waiting to be released')
        return 0

    print(f'Next release: v{version}')
    if 'GITHUB_OUTPUT' in os.environ:
        with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
            output.write(f'version={version}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
