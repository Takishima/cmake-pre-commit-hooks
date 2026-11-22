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

from pathlib import Path

from cmake_pc_hooks import clang_format

import pytest
from _test_utils import ExitError, command_main_asserts

# ==============================================================================


UNFORMATTED = 'int  main( ){\n  return 0;}\n'
FORMATTED = 'int main() {\n  return 0;\n}\n'


def _fake_clang_format(mocker, *, stderr='', returncode=0):
    """Mock call_process() with a formatter that always produces FORMATTED (and writes it to the file with -i)."""

    def _call_process(args):
        if '-i' in args:
            Path(args[-1]).write_bytes(FORMATTED.encode())
            return mocker.Mock(stdout='', stderr=stderr, returncode=returncode)
        return mocker.Mock(stdout=FORMATTED, stderr=stderr, returncode=returncode)

    return mocker.patch('cmake_pc_hooks._call_process.call_process', side_effect=_call_process)


@pytest.fixture
def source_files(mocker, tmp_path):
    mocker.patch('cmake_pc_hooks._utils.Command.check_installed', return_value=True)
    good, bad = tmp_path / 'good.cpp', tmp_path / 'bad.cpp'
    good.write_bytes(FORMATTED.encode())
    bad.write_bytes(UNFORMATTED.encode())
    return str(good), str(bad)


# ==============================================================================


def test_clang_format_formatted_file(mocker, capsys, source_files):
    good, _ = source_files
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_clang_format(mocker)

    command = clang_format.ClangFormatCmd(args=['clang-format', '--style=Google', good])
    assert command.files == [good]
    assert not command.edit_in_place
    command.run()

    call_process.assert_called_once_with(['clang-format', '--style=Google', good])
    sys_exit.assert_not_called()
    assert not capsys.readouterr().out


def test_clang_format_unformatted_files(mocker, capsys, source_files):
    good, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_clang_format(mocker)

    command = clang_format.ClangFormatCmd(args=['clang-format', good, bad])
    command.run()

    sys_exit.assert_called_once_with(1)
    stdout = capsys.readouterr().out
    assert stdout.startswith(f'{bad}\n{"=" * 20}\n--- original\n+++ formatted\n')
    assert '-int  main( ){' in stdout
    assert '+int main() {' in stdout
    assert good not in stdout
    assert Path(bad).read_bytes().decode() == UNFORMATTED


def test_clang_format_no_diff(mocker, capsys, source_files):
    _, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    call_process = _fake_clang_format(mocker)

    command = clang_format.ClangFormatCmd(args=['clang-format', '--no-diff', bad])
    assert command.no_diff_flag
    assert '--no-diff' not in command.args
    command.run()

    call_process.assert_called_once_with(['clang-format', bad])
    sys_exit.assert_called_once_with(1)
    assert not capsys.readouterr().out


def test_clang_format_edit_in_place(mocker, capsys, source_files):
    good, bad = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_clang_format(mocker)

    command = clang_format.ClangFormatCmd(args=['clang-format', '-i', good, bad])
    assert command.edit_in_place
    command.run()

    sys_exit.assert_called_once_with(1)
    assert Path(bad).read_bytes().decode() == FORMATTED
    assert bad in capsys.readouterr().out


@pytest.mark.parametrize(('stderr', 'returncode'), [('some warning', 0), ('', 1)], ids=['stderr', 'returncode'])
def test_clang_format_dry_run_or_failure(mocker, capsys, source_files, stderr, returncode):
    _, bad = source_files
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    _fake_clang_format(mocker, stderr=stderr, returncode=returncode)

    command = clang_format.ClangFormatCmd(args=['clang-format', '-n', bad])
    assert command.dry_run
    with pytest.raises(ExitError):
        command.run()

    sys_exit.assert_called_once_with(1)
    assert 'Unexpected Stderr/return code received' in capsys.readouterr().err


def test_clang_format_dry_run_success(mocker, capsys, source_files):
    good, _ = source_files
    sys_exit = mocker.patch('sys.exit')
    _fake_clang_format(mocker)

    command = clang_format.ClangFormatCmd(args=['clang-format', '--dry-run', good])
    command.run()

    sys_exit.assert_not_called()
    assert not capsys.readouterr().out


def test_clang_format_empty_output(mocker, source_files, tmp_path):
    mocker.patch('sys.exit')
    mocker.patch(
        'cmake_pc_hooks._call_process.call_process', return_value=mocker.Mock(stdout='', stderr='', returncode=0)
    )
    empty = tmp_path / 'empty.cpp'
    empty.write_text('', encoding='utf-8')

    command = clang_format.ClangFormatCmd(args=['clang-format', str(empty)])
    assert command.get_formatted_lines(str(empty)) == []


def test_clang_format_missing_file(mocker, capsys, source_files, tmp_path):
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    missing = str(tmp_path / 'missing.cpp')

    command = clang_format.ClangFormatCmd(args=['clang-format', missing])
    with pytest.raises(ExitError):
        command.run()

    sys_exit.assert_called_once_with(1)
    assert f'File {missing} not found' in capsys.readouterr().err


# ==============================================================================


def test_clang_format_main(mocker):
    argv = ['clang-format', '-i', 'file.txt']
    command_main_asserts(mocker, 'clang_format.ClangFormatCmd', clang_format.main, argv)


# ==============================================================================
