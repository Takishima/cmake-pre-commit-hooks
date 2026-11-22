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

import json

from cmake_pc_hooks._cmake import trace

import pytest

# ==============================================================================


def test_parse_cache_variables():
    output = (
        '-- Cache values\n'
        'CMAKE_ADDR2LINE:FILEPATH=/usr/bin/addr2line\n'
        'CMAKE_CXX_FLAGS:STRING=\n'
        'CMAKE_CXX_FLAGS_RELEASE:STRING=-O3 -DNDEBUG\n'
        'CMAKE_VERBOSE_MAKEFILE:BOOL=FALSE\n'
        'not a variable\n'
        'FETCHCONTENT_BASE_DIR:PATH=/path/to/build/_deps\n'
    )

    assert trace.parse_cache_variables(output) == {
        'CMAKE_ADDR2LINE': '/usr/bin/addr2line',
        'CMAKE_CXX_FLAGS': '',
        'CMAKE_CXX_FLAGS_RELEASE': '-O3 -DNDEBUG',
        'CMAKE_VERBOSE_MAKEFILE': 'FALSE',
        'FETCHCONTENT_BASE_DIR': '/path/to/build/_deps',
    }


@pytest.mark.parametrize('with_fetchcontent_dir', [False, True])
def test_find_configured_files(tmp_path, with_fetchcontent_dir):
    source_dir = tmp_path
    build_dir = tmp_path / 'build'
    root = tmp_path.as_posix()
    calls = [
        {'version': {'major': 1, 'minor': 2}},
        {'args': ['VERSION', '3.20'], 'cmd': 'cmake_minimum_required', 'file': f'{root}/CMakeLists.txt'},
        {
            'args': ['/usr/share/cmake/Modules/in.cmake.in', f'{root}/build/_deps/catch2-subbuild/CMakeLists.txt'],
            'cmd': 'configure_file',
            'file': '/usr/share/cmake/Modules/FetchContent.cmake',
        },
        {
            'args': [f'{root}/build/_deps/catch2-src/config.hpp.in', f'{root}/build/generated/config.hpp'],
            'cmd': 'configure_file',
            'file': f'{root}/build/_deps/catch2-src/src/CMakeLists.txt',
        },
        {'args': ['test.cpp.in', 'test.cpp'], 'cmd': 'configure_file', 'file': f'{root}/CMakeLists.txt'},
        {'args': ['test.cpp.in', f'{root}/other.cpp'], 'cmd': 'configure_file', 'file': f'{root}/CMakeLists.txt'},
    ]
    trace_log = tmp_path / 'trace_log.json'
    trace_log.write_text('\n'.join(json.dumps(call) for call in calls), encoding='utf-8')
    cache_variables = {'FETCHCONTENT_BASE_DIR': f'{root}/build/_deps'} if with_fetchcontent_dir else {}

    configured_files = trace.find_configured_files(trace_log, source_dir, build_dir, cache_variables)

    expected = [str(build_dir / 'test.cpp'), str(source_dir / 'other.cpp')]
    if not with_fetchcontent_dir:
        expected.insert(0, str(build_dir / 'generated' / 'config.hpp'))
    assert configured_files == expected


# ==============================================================================
