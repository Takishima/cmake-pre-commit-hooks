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

import sys

from cmake_pc_hooks._cmake import locate

import pytest

# ==============================================================================


@pytest.mark.parametrize(('cmd', 'is_valid'), [('cmake-INVALID', False), (sys.executable, True)])
def test_try_calling_cmake(cmd, is_valid):
    assert locate._try_calling_cmake([cmd]) == is_valid


# ==============================================================================


@pytest.mark.parametrize(
    ('stdout', 'returncode', 'expected'),
    [
        ('cmake version 3.28.3\n\nCMake suite maintained and supported by Kitware', 0, (3, 28, 3)),
        ('cmake version 3.31.0-rc1\n', 0, (3, 31, 0)),
        ('cmake3 version 4.1\n', 0, (4, 1, 0)),
        ('cmake version 3.31.0\n', 1, None),
        ('garbage', 0, None),
    ],
)
def test_get_version(mocker, stdout, returncode, expected):
    call_process = mocker.patch(
        'cmake_pc_hooks._call_process.call_process',
        return_value=mocker.Mock(stdout=stdout, stderr='', returncode=returncode),
    )

    assert locate.get_version(['cmake']) == expected
    call_process.assert_called_once_with(['cmake', '--version'])


def test_get_version_no_cmake(mocker):
    call_process = mocker.patch('cmake_pc_hooks._call_process.call_process', side_effect=OSError)

    assert locate.get_version(None) is None
    call_process.assert_not_called()

    assert locate.get_version(['cmake']) is None


# ==============================================================================


@pytest.mark.parametrize('automatic_discovery', [False, True])
@pytest.mark.parametrize(
    ('build_dirs', 'tree', 'expected', 'expected_without_discovery'),
    [
        ([], ['build/'], locate.DEFAULT_BUILD_DIR, locate.DEFAULT_BUILD_DIR),
        ([], ['build/CMakeCache.txt'], 'build', locate.DEFAULT_BUILD_DIR),
        ([], ['gcc-build/CMakeCache.txt', 'build/CMakeCache.txt'], 'build', locate.DEFAULT_BUILD_DIR),
        ([], ['file.txt', 'build/CMakeCache.txt'], 'build', locate.DEFAULT_BUILD_DIR),
        (['clang', 'gcc'], ['gcc-build/compile_commands.json'], 'clang', 'clang'),
        (['clang'], ['gcc-build/CMakeCache.txt'], 'gcc-build', 'clang'),
        (['clang', 'gcc'], ['gcc/CMakeCache.txt', 'build/CMakeCache.txt'], 'gcc', 'gcc'),
        (
            ['clang'],
            ['gcc-build/CMakeCache.txt', 'clang/CMakeCache.txt', 'build/CMakeCache.txt'],
            'clang',
            'clang',
        ),
    ],
)
def test_find_build_directory(tmp_path, automatic_discovery, build_dirs, tree, expected, expected_without_discovery):
    for name in tree:
        path = tmp_path / name
        if name.endswith('/'):
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'')

    build_dir = locate.find_build_directory(
        tmp_path, [str(tmp_path / name) for name in build_dirs], automatic_discovery=automatic_discovery
    )

    assert build_dir == tmp_path / (expected if automatic_discovery else expected_without_discovery)


def test_find_build_directory_without_creating_one(tmp_path):
    (tmp_path / 'build').mkdir()

    assert locate.find_build_directory(tmp_path, [str(tmp_path / 'build')], create=False) is None

    (tmp_path / 'build' / 'CMakeCache.txt').write_bytes(b'')
    assert locate.find_build_directory(tmp_path, [str(tmp_path / 'build')], create=False) == tmp_path / 'build'


# ==============================================================================
