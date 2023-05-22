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

import subprocess as sp

from cmake_pc_hooks._call_process import History, call_process

# ==============================================================================


def test_history(mocker):
    stdout = 'out'
    stderr = 'err'
    returncode = 1
    history = History(stdout=stdout, stderr=stderr, returncode=returncode)

    assert history.stdout == stdout
    assert history.stderr == stderr
    assert history.returncode == returncode

    sys_stdout = mocker.patch('sys.stdout')
    sys_stderr = mocker.patch('sys.stderr')

    history.to_stdout_and_stderr()

    sys_stdout.write.assert_called_once()
    sys_stderr.write.assert_called_once()


# ==============================================================================


def test_call_process_success(mocker):
    sp_run = mocker.patch('subprocess.run')

    args = ['cmake', '/path/to/src_dir', '-B/path/to/build_dir']
    kwargs = {'my_arg': 'One'}
    call_process(args, **kwargs)
    sp_run.assert_called_once_with(args, **kwargs, check=True, capture_output=True)


def test_call_process_invalid(mocker):
    stdout = b'out'
    stderr = b'err'
    sp_run = mocker.patch(
        'subprocess.run', side_effect=sp.CalledProcessError(-1, cmd=None, output=stdout, stderr=stderr)
    )

    args = ['cmake', '/path/to/src_dir', '-B/path/to/build_dir']
    kwargs = {'my_arg': 'One'}
    result = call_process(args, **kwargs)
    assert isinstance(result, History)
    assert result.stdout == stdout.decode()
    assert result.stderr == stderr.decode()
    assert result.returncode == -1
    sp_run.assert_called_once_with(args, **kwargs, check=True, capture_output=True)


# ==============================================================================
