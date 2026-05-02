"""Tests for orquestrum.lib.paths."""
import os
import pytest
from pathlib import Path
from orquestrum.lib.paths import (
    orquestrum_home,
    find_project_root,
    find_canonical_root,
    canonical_root_from_package,
)


class TestOrquestrumHome:
    def test_returns_a_path(self):
        p = orquestrum_home()
        assert isinstance(p, Path)

    def test_directory_created_when_missing(self, tmp_path: Path, monkeypatch):
        target = tmp_path / 'custom_home'
        monkeypatch.setenv('ORQUESTRUM_HOME', str(target))
        p = orquestrum_home()
        assert p.is_dir()

    def test_respects_env_var(self, tmp_path: Path, monkeypatch):
        target = tmp_path / 'my_home'
        monkeypatch.setenv('ORQUESTRUM_HOME', str(target))
        assert orquestrum_home() == target


class TestFindProjectRoot:
    def test_finds_orquestrum_dir(self, tmp_path: Path):
        (tmp_path / '.orquestrum').mkdir()
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_finds_orquestrum_dir_in_parent(self, tmp_path: Path):
        (tmp_path / '.orquestrum').mkdir()
        child = tmp_path / 'sub' / 'nested'
        child.mkdir(parents=True)
        result = find_project_root(child)
        assert result == tmp_path

    def test_returns_none_when_not_found(self, tmp_path: Path):
        result = find_project_root(tmp_path)
        assert result is None


class TestFindCanonicalRoot:
    def test_returns_none_for_empty_dir(self, tmp_path: Path):
        result = find_canonical_root(tmp_path)
        assert result is None

    def test_finds_root_when_markers_present(self, tmp_path: Path):
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills').mkdir()
        (tmp_path / 'orquestrum' / 'lib').mkdir(parents=True)
        (tmp_path / 'docs' / 'agent-context').mkdir(parents=True)
        result = find_canonical_root(tmp_path)
        assert result == tmp_path


class TestCanonicalRootFromPackage:
    def test_returns_path_when_in_repo(self):
        result = canonical_root_from_package()
        assert result is not None
        assert (result / 'agents').is_dir()
        assert (result / 'skills').is_dir()
