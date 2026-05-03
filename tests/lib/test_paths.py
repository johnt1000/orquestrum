"""Tests for orquestrum.lib.paths."""
import pytest
from pathlib import Path

from orquestrum.lib import paths
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


# ── v0.3 helpers ────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake canonical repo on disk; pin find_canonical_root() to it."""
    repo = tmp_path / 'fake-repo'
    (repo / 'agents').mkdir(parents=True)
    (repo / 'skills').mkdir()
    (repo / 'docs' / 'agent-context').mkdir(parents=True)
    (repo / 'orquestrum' / 'lib').mkdir(parents=True)
    (repo / 'pinned_refs.toml').write_text('# fake', encoding='utf-8')
    monkeypatch.setattr(paths, 'find_canonical_root', lambda *a, **kw: repo)
    return repo


@pytest.fixture()
def no_canonical(monkeypatch: pytest.MonkeyPatch):
    """Force find_canonical_root() to None — wheel install scenario."""
    monkeypatch.setattr(paths, 'find_canonical_root', lambda *a, **kw: None)


@pytest.fixture()
def isolated_orq_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / 'orq-home'
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    monkeypatch.delenv('ORQUESTRUM_CACHE', raising=False)
    return home


class TestCanonicalAssetsRoot:
    def test_prefers_dev_repo_when_available(self, fake_canonical: Path):
        assert paths.canonical_assets_root() == fake_canonical

    def test_falls_back_to_bundled_assets_when_no_repo(
        self, no_canonical, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        fake_assets = tmp_path / 'fake-bundle'
        fake_assets.mkdir()
        from orquestrum.lib import assets as assets_mod
        monkeypatch.setattr(assets_mod, 'assets_root', lambda: fake_assets)
        assert paths.canonical_assets_root() == fake_assets

    def test_never_returns_none(
        self, no_canonical, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        from orquestrum.lib import assets as assets_mod
        monkeypatch.setattr(assets_mod, 'assets_root', lambda: tmp_path)
        assert paths.canonical_assets_root() is not None


class TestConvertOutputRoot:
    def test_explicit_env_override_wins(
        self, fake_canonical: Path, isolated_orq_home: Path,
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        explicit = tmp_path / 'custom-cache'
        monkeypatch.setenv('ORQUESTRUM_CACHE', str(explicit))
        assert paths.convert_output_root() == explicit

    def test_dev_mode_writes_inside_repo(self, fake_canonical: Path):
        assert paths.convert_output_root() == fake_canonical / 'integrations'

    def test_wheel_mode_uses_user_cache(
        self, no_canonical, isolated_orq_home: Path,
    ):
        assert paths.convert_output_root() == isolated_orq_home / 'cache' / 'integrations'


class TestPinnedRefsPath:
    def test_prefers_repo_pins(self, fake_canonical: Path):
        result = paths.pinned_refs_path()
        assert result == fake_canonical / 'pinned_refs.toml'
        assert result.is_file()

    def test_falls_back_to_bundled(
        self, no_canonical, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        fake_assets = tmp_path / 'bundle'
        fake_assets.mkdir()
        from orquestrum.lib import assets as assets_mod
        monkeypatch.setattr(assets_mod, 'assets_root', lambda: fake_assets)
        assert paths.pinned_refs_path() == fake_assets / 'pinned_refs.toml'


class TestIsDevMode:
    def test_returns_true_in_repo(self, fake_canonical: Path):
        assert paths.is_dev_mode() is True

    def test_returns_false_when_no_repo(self, no_canonical):
        assert paths.is_dev_mode() is False

    def test_returns_false_when_repo_has_no_agents(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.setattr(paths, 'find_canonical_root', lambda *a, **kw: bare)
        assert paths.is_dev_mode() is False
