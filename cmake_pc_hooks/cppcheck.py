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

"""Hook for cppcheck."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._hook import Hook
from ._runner import make_main

if TYPE_CHECKING:
    from ._call_process import History


def file_filter(filename: str) -> str:
    """Create the option that restricts the analysis of the CMake project to one file."""
    return f'--file-filter=*{Path(filename).parent.name}/{Path(filename).name}'


def has_errors(result: History) -> bool:
    """
    Tell whether cppcheck reported errors, after hiding a useless message.

    See https://stackoverflow.com/questions/6986033
    """
    result.stderr = ''.join(
        line
        for line in result.stderr.splitlines(keepends=True)
        if 'Cppcheck cannot find all the include files' not in line
    )
    return result.returncode != 0


HOOK = Hook(
    name='cppcheck',
    version_prefix='Cppcheck ',
    default_args=('-q', '--error-exitcode=1', '--enable=all'),
    compile_db_arg='--project={}',
    file_arg=file_filter,
    check=has_errors,
)

main = make_main(HOOK)


if __name__ == '__main__':  # pragma: nocover
    main()
