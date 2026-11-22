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

"""Hook for include-what-you-use."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._hook import Hook
from ._runner import make_main

if TYPE_CHECKING:
    from ._call_process import History


def has_errors(result: History) -> bool:
    """
    Tell whether include-what-you-use suggests any change.

    The return code is of no use since it is never 0. When several files are processed at once, the output may
    contain a mix of correct and incorrect files.
    """
    is_correct = 'has correct #includes/fwd-decls' in result.stdout
    has_suggestions = any(msg in result.stdout for msg in ('should add these lines:', 'should remove these lines:'))
    return has_suggestions or (bool(result.stdout) and not is_correct)


HOOK = Hook(
    name='include-what-you-use',
    version_prefix='include-what-you-use ',
    executables=('iwyu_tool.py', 'iwyu-tool', 'iwyu_tool'),
    version_executables=('include-what-you-use',),
    compile_db_arg='-p={}',
    double_dash=True,
    check=has_errors,
)

main = make_main(HOOK)


if __name__ == '__main__':  # pragma: nocover
    main()
