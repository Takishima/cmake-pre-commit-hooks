import itertools
import json
from collections import namedtuple

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


SetupCommandData = namedtuple(
    'SetupCommandData',
    [
        'all_at_once',
        'read_json_db',
        'compile_db_path',
        'json_db_file_list',
        'returncode',
        'file_list',
        'cmd_args',
        'configure',
        'sys_exit',
        'call_process',
    ],
)


@pytest.fixture(params=_setup_commands_args, ids=_setup_command_ids)
def setup_command(mocker, tmp_path, compile_commands, request):
    mocker.patch('hooks.utils.Command.check_installed', return_value=True)
    all_at_once, read_json_db, returncode = request.param

    configure = mocker.patch('cmake_pc_hooks._cmake.CMakeCommand.configure', return_value=0)
    sys_exit = mocker.patch('sys.exit', side_effect=ExitError)
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        return_value=mocker.Mock(stdout='', stderr='', returncode=returncode),
    )

    file_list = [tmp_path / 'file1.cpp', tmp_path / 'file2.cpp']
    for file in file_list:
        file.write_text('')

    args = []
    if read_json_db:
        args.append('--read-json-db')

    if all_at_once:
        args.append('--all-at-once')

    return SetupCommandData(
        all_at_once=all_at_once,
        read_json_db=read_json_db,
        compile_db_path=compile_commands[0],
        json_db_file_list=compile_commands[1],
        returncode=returncode,
        file_list=file_list,
        cmd_args=[*args, *[str(fname) for fname in file_list]],
        configure=configure,
        sys_exit=sys_exit,
        call_process=call_process,
    )


# ==============================================================================
