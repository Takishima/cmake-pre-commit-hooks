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

"""Hook for clang-tidy."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ._hook import Hook
from ._runner import make_main

if TYPE_CHECKING:
    from ._call_process import History

log = logging.getLogger(__name__)


def has_errors(result: History) -> bool:
    """Tell whether clang-tidy reported errors, after hiding its complaints about system files."""
    if not result.stdout or 'non-user code' in result.stderr:
        result.stderr = ''
    log.debug('returncode %d', result.returncode)
    log.debug('parsing output from %s', result.stderr)

    return result.returncode != 0 or any(
        msg in result.stderr
        for msg in (
            'error generated.',
            'errors generated.',
            'warning treated as error',
            'warnings treated as errors',
        )
    )


HOOK = Hook(
    name='clang-tidy',
    version_prefix='LLVM version ',
    compile_db_arg='-p={}',
    double_dash=True,
    check=has_errors,
)

main = make_main(HOOK)


if __name__ == '__main__':  # pragma: nocover
    main()
