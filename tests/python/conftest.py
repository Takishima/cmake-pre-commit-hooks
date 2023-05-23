import itertools
import json

import pytest
from _test_utils import ExitError

# ==============================================================================


@pytest.fixture()
def compile_commands(tmp_path):
    path = tmp_path / 'build' / 'compile_commands.json'

    data = []
    file_list = [
        tmp_path / 'directory/one.cpp',
        tmp_path / 'directory/two.cpp',
        tmp_path / 'directory/three.cpp',
    ]

    for fname in file_list:
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.write_text('')
        data.append(
            {
                'directory': str(fname.parent),
                'file': str(fname),
                'command': f'/usr/bin/c++ -DONE -DTWO -Wall -c {fname}',
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode='w', encoding='utf-8') as fd:
        json.dump(data, fd)

    return path, file_list


# ==============================================================================


_setup_commands_args = itertools.product(
    (False, True),  # all_at_once
    (False, True),  # read_json_db
    (0, 1),  # returncode
)


def _setup_command_ids(param):
    all_at_once, read_json_db, returncode = param
    return f'{"all_files" if all_at_once else "single_file"}-{"w_db" if read_json_db else "no_db"}-ret_{returncode}'


@pytest.fixture(params=_setup_commands_args, ids=_setup_command_ids)
def setup_command(mocker, request):
    mocker.patch('hooks.utils.Command.check_installed', return_value=True)
    all_at_once, read_json_db, returncode = request.param
    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)

    args = []
    if read_json_db:
        args.append('--read-json-db')

    if all_at_once:
        args.append('--all-at-once')

    return all_at_once, read_json_db, returncode, args, configure, sys_exit


# ==============================================================================
