# Copyright 2021 Damien Nguyen
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

"""Tests for the release automation scripts in .github/scripts."""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent / '.github' / 'scripts'


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_version = load_script('release_version')
pre_commit_fragments = load_script('pre_commit_fragments')


@pytest.fixture
def repository(tmp_path, monkeypatch):
    """Empty repository with a changelog whose latest release is v1.5.0."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(release_version, 'tag_exists', lambda tag: tag == 'v1.0.0')
    monkeypatch.setenv('GITHUB_OUTPUT', str(tmp_path / 'output'))
    (tmp_path / 'changelog.d').mkdir()
    (tmp_path / 'changelog.d' / 'README.md').write_text('# Changelog fragments\n')
    (tmp_path / 'CHANGELOG.md').write_text(
        '# Changelog\n\n'
        '## [v1.6.0-rc.1](https://example.com) - 2026-01-02\n\n'
        '## [v1.5.0](https://example.com) - 2026-01-01\n\n'
        '## [v1.4.1] - 2025-01-01\n'
    )
    return tmp_path


def add_fragments(repository, *names):
    for name in names:
        (repository / 'changelog.d' / name).write_text('Some change\n')


def output(repository):
    path = repository / 'output'
    return path.read_text() if path.exists() else ''


def test_fragment_types(repository):
    add_fragments(repository, '+a.fixed.md', '12.added.md', '12.added.1.md', '+b.c.repository.md')
    assert release_version.fragment_types(repository / 'changelog.d') == {'fixed', 'added', 'repository'}


def test_latest_version_skips_pre_releases(repository):
    assert release_version.latest_version((repository / 'CHANGELOG.md').read_text()) == (1, 5, 0)


def test_latest_version_not_found():
    with pytest.raises(ValueError, match='latest release'):
        release_version.latest_version('# Changelog\n')


@pytest.mark.parametrize(
    ('request_', 'types', 'expected'),
    [
        ('auto', {'fixed', 'repository'}, '1.5.1'),
        ('auto', {'security'}, '1.5.1'),
        ('auto', {'repository'}, '1.5.1'),
        ('auto', {'fixed', 'added'}, '1.6.0'),
        ('auto', {'changed'}, '1.6.0'),
        ('auto', {'deprecated'}, '1.6.0'),
        ('auto', {'removed'}, '1.6.0'),
        ('scheduled', {'fixed'}, '1.5.1'),
        ('scheduled', {'added', 'repository'}, '1.6.0'),
        ('scheduled', {'repository'}, None),
        ('scheduled', set(), None),
        ('patch', {'added'}, '1.5.1'),
        ('MINOR', {'fixed'}, '1.6.0'),
        ('major', {'fixed'}, '2.0.0'),
        ('2.0.0', {'fixed'}, '2.0.0'),
        ('v2.0.0', {'fixed'}, '2.0.0'),
        ('V2.0.0-rc.1', {'fixed'}, '2.0.0-rc.1'),
    ],
)
def test_next_version(request_, types, expected):
    assert release_version.next_version(request_, types, (1, 5, 0)) == expected


@pytest.mark.parametrize(
    ('request_', 'types', 'message'),
    [
        ('auto', set(), 'nothing to release'),
        ('v2.0.0', set(), 'nothing to release'),
        ('1.6', {'fixed'}, 'not valid'),
        ('bogus', {'fixed'}, 'not valid'),
        ('v1.6.0; echo', {'fixed'}, 'not valid'),
    ],
)
def test_next_version_invalid(request_, types, message):
    with pytest.raises(ValueError, match=message):
        release_version.next_version(request_, types, (1, 5, 0))


def test_main(repository, capsys):
    add_fragments(repository, '+a.fixed.md')
    assert release_version.main(['release_version.py']) == 0
    assert output(repository) == 'version=1.5.1\n'
    assert 'v1.5.1' in capsys.readouterr().out


def test_main_scheduled_without_user_facing_change(repository, capsys):
    add_fragments(repository, '+a.repository.md')
    assert release_version.main(['release_version.py', 'scheduled']) == 0
    assert not output(repository)
    assert '::notice::' in capsys.readouterr().out


def test_main_nothing_to_release(repository, capsys):
    assert release_version.main(['release_version.py', 'auto']) == 1
    assert not output(repository)
    assert '::error::' in capsys.readouterr().out


def test_main_existing_tag(repository, capsys):
    add_fragments(repository, '+a.fixed.md')
    assert release_version.main(['release_version.py', 'v1.0.0']) == 1
    assert not output(repository)
    assert 'already exists' in capsys.readouterr().out


def test_pre_commit_fragments(repository, monkeypatch):
    monkeypatch.setenv(
        'PR_BODY',
        '<!--pre-commit.ci start-->\n'
        'updates:\n'
        '- [github.com/pre-commit/pre-commit-hooks: v4.6.0 → v6.0.0](https://example.com)\n'
        '- https://github.com/PyCQA/doc8/: v1.1.1 → v2.0.0\n'
        '- [github.com/adrienverge/yamllint.git: v1.35.1 → v1.38.0](https://example.com)\n'
        '- [github.com/asottile/blacken-docs: 1.16.0 → 1.20.0](https://example.com)\n'
        '<!--pre-commit.ci end-->\n',
    )
    pre_commit_fragments.main()

    fragments = {path.name: path.read_text() for path in (repository / 'changelog.d').glob('+*.md')}
    assert fragments == {
        f'+pre-commit-{slug}.repository.md': f'Update `{hook}` hook to v{version}\n'
        for slug, hook, version in (
            ('pre-commit-pre-commit-hooks', 'pre-commit/pre-commit-hooks', '6.0.0'),
            ('pycqa-doc8', 'PyCQA/doc8', '2.0.0'),
            ('adrienverge-yamllint', 'adrienverge/yamllint', '1.38.0'),
            ('asottile-blacken-docs', 'asottile/blacken-docs', '1.20.0'),
        )
    }
    assert release_version.fragment_types(repository / 'changelog.d') == {'repository'}
