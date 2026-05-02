"""Unit tests for `orquestrum repos` — list / add / remove."""
from __future__ import annotations
import argparse
from pathlib import Path

import pytest

from orquestrum.commands import repos
from orquestrum.lib import registry


def _ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


class TestReposList:
    def test_empty_registry_prints_friendly_message(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        rc = repos._list(_ns())
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No projects registered' in out

    def test_lists_registered_projects(
        self, isolated_home: Path, project_root: Path, capsys: pytest.CaptureFixture,
    ):
        registry.register_project(name='alpha', path=project_root, tool='claude-code')
        rc = repos._list(_ns())
        assert rc == 0
        out = capsys.readouterr().out
        assert 'alpha' in out
        assert 'claude-code' in out
        assert '1 project(s) registered' in out


class TestReposAdd:
    def test_adds_existing_directory(
        self, isolated_home: Path, project_root: Path, capsys: pytest.CaptureFixture,
    ):
        ns = _ns(path=str(project_root), name=None, tool='opencode', provider='claude')
        rc = repos._add(ns)
        assert rc == 0
        entries = registry.load_registry()
        assert any(e['name'] == project_root.name and e['tool'] == 'opencode' for e in entries)

    def test_rejects_missing_directory(
        self, isolated_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        missing = tmp_path / 'does-not-exist'
        ns = _ns(path=str(missing), name=None, tool=None, provider=None)
        rc = repos._add(ns)
        assert rc == 1
        out = capsys.readouterr().out
        assert 'not a directory' in out

    def test_uses_explicit_name_when_provided(
        self, isolated_home: Path, project_root: Path,
    ):
        ns = _ns(path=str(project_root), name='custom', tool=None, provider=None)
        repos._add(ns)
        assert registry.find_by_name('custom') is not None


class TestReposRemove:
    def test_removes_by_name(self, isolated_home: Path, project_root: Path):
        registry.register_project(name='to-remove', path=project_root)
        ns = _ns(identifier='to-remove')
        rc = repos._remove(ns)
        assert rc == 0
        assert registry.find_by_name('to-remove') is None

    def test_removes_by_path(self, isolated_home: Path, project_root: Path):
        registry.register_project(name='by-path', path=project_root)
        ns = _ns(identifier=str(project_root))
        rc = repos._remove(ns)
        assert rc == 0
        assert registry.find_by_name('by-path') is None

    def test_returns_1_when_no_match(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        ns = _ns(identifier='nope')
        rc = repos._remove(ns)
        assert rc == 1
        assert 'No project matched' in capsys.readouterr().out


class TestReposRegistration:
    def test_register_creates_subparser_choices(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        repos.register(sub)
        repos_parser = sub.choices['repos']
        # Inspect nested subparsers
        nested = [a for a in repos_parser._actions if hasattr(a, 'choices') and a.dest == 'repos_cmd']
        assert nested
        for action_name in ('list', 'add', 'remove'):
            assert action_name in nested[0].choices
