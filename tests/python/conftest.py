import json

import pytest

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
