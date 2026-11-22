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

"""Hook for lizard."""

from ._hook import Hook, has_failed_quiet_on_success
from ._runner import make_main

HOOK = Hook(name='lizard', check=has_failed_quiet_on_success)

main = make_main(HOOK)


if __name__ == '__main__':  # pragma: nocover
    main()
