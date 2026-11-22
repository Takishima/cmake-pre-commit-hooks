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

from cmake_pc_hooks import _cli

import click
import pytest

# ==============================================================================


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def parse(*args, hook_name='clang-tidy'):
    return _cli.parse_args(hook_name, list(args))


# ==============================================================================


def test_parse_args_defaults():
    options, tool_args, files = parse()

    assert not tool_args
    assert not files
    assert not options.all_at_once
    assert not options.read_json_db
    assert not options.dump_toml
    assert options.version is None
    assert options.hooks_config is None
    assert options.source_dir == Path()
    assert options.build_dir == ()


def test_parse_args_hook_options():
    options, tool_args, files = parse('--all-at-once', '--read-json-db', '--version=18', '-Bbuild', 'file.cpp')

    assert options.all_at_once
    assert options.read_json_db
    assert options.version == '18'
    assert options.build_dir == ('build',)
    assert not tool_args
    assert files == ['file.cpp']


def test_parse_args_passes_unknown_options_to_the_tool():
    args = ['--checks=-*,readability-*', '--fix-errors', '-p=build/compile_commands.json', '-j4', '--config={}']

    options, tool_args, files = parse('one.cpp', *args, '-DONE', 'two.cpp')

    assert tool_args == args
    assert files == ['one.cpp', 'two.cpp']
    assert options.defines == ('ONE',)


def test_parse_args_double_dash():
    options, tool_args, files = parse('--checks=*', '-Bbuild', '--', '-std=c++17', '-DTWO', 'file.cpp')

    assert tool_args == ['--checks=*']
    assert files == ['-std=c++17', '-DTWO', 'file.cpp']
    assert options.build_dir == ('build',)
    assert options.defines == ()


def test_parse_args_help(capsys):
    with pytest.raises(click.exceptions.Exit) as excinfo:
        parse('--help', hook_name='lizard')

    assert excinfo.value.exit_code == 0
    stdout = capsys.readouterr().out
    assert stdout.startswith('Usage: cmake-pc-lizard-hook [OPTIONS] [FILES]...')
    assert '--hooks-config' in stdout


def test_parse_args_invalid_value():
    with pytest.raises(click.UsageError, match='does not exist'):
        parse('-S', 'missing', 'file.cpp')


# ==============================================================================


def test_parse_args_settings_from_toml(project):
    (project / 'pyproject.toml').write_text(
        '[tool.cmake_pc_hooks]\nbuild_dir = ["pyproject"]\nautomatic_discovery = false\nerrors = ["dev"]\n'
        '[tool.cmake_pc_hooks.cppcheck]\nall_at_once = true\n',
        encoding='utf-8',
    )

    options, _, _ = parse('file.cpp')
    assert options.build_dir == ('pyproject',)
    assert not options.automatic_discovery
    assert options.errors == ('dev',)
    assert not options.all_at_once

    options, _, _ = parse('file.cpp', hook_name='cppcheck')
    assert options.all_at_once

    options, _, _ = parse('-Bcli', 'file.cpp')
    assert options.build_dir == ('cli',)


def test_parse_args_hooks_config(project):
    (project / 'cmake_pc_hooks.toml').write_text('build_dir = ["default"]\ngenerator = "Ninja"\n', encoding='utf-8')
    (project / 'custom.toml').write_text('build_dir = ["custom"]\n', encoding='utf-8')

    options, _, _ = parse('--hooks-config=custom.toml', 'file.cpp')
    assert options.hooks_config == 'custom.toml'
    assert options.build_dir == ('custom',)
    assert options.generator == 'Ninja'

    options, _, _ = parse('--hooks-config', 'custom.toml', '-Bcli', 'file.cpp')
    assert options.build_dir == ('cli',)


@pytest.mark.parametrize(
    ('content', 'message'),
    [
        ('not_an_option = true\n', 'unknown option "not_an_option"'),
        ('files = ["file.cpp"]\n', 'unknown option "files"'),
        ('dump_toml = true\n', 'unknown option "dump_toml"'),
        ('hooks_config = "other.toml"\n', 'unknown option "hooks_config"'),
        ('build_dir = "build"\n', 'must be of type list'),
        ('source_dir = "missing"\n', 'does not exist'),
    ],
)
def test_parse_args_invalid_settings(project, content, message):
    (project / 'cmake_pc_hooks.toml').write_text(content, encoding='utf-8')

    with pytest.raises(click.UsageError, match=message):
        parse('file.cpp')


def test_parse_args_missing_hooks_config():
    with pytest.raises(click.UsageError, match=r'Unable to locate TOML file missing\.toml'):
        parse('--hooks-config=missing.toml', 'file.cpp')


# ==============================================================================


def test_parse_args_dump_toml(project, capsys):
    (project / 'cmake_pc_hooks.toml').write_text('generator = "Ninja"\nclean = false\n', encoding='utf-8')

    with pytest.raises(click.exceptions.Exit) as excinfo:
        parse('--dump-toml', '-Bbuild', '-DONE', '-Wdev', '--no-automatic-discovery', '--checks=*', 'file.cpp')

    assert excinfo.value.exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        'build_dir = ["build"]',
        'defines = ["ONE"]',
        'generator = "Ninja"',
        'dev_warnings = true',
        'clean = false',
        'automatic_discovery = false',
    ]


# ==============================================================================
