"""Tests for orquestrum.lib.installs_manifest — persistent install record."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.lib import installs_manifest


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sandbox ORQUESTRUM_HOME for the test."""
    home = tmp_path / 'orq-home'
    home.mkdir(parents=True)
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    return home


# ─── load / save round-trip ─────────────────────────────────────────────────


class TestEmptyManifest:
    def test_list_returns_empty_when_no_file(self, isolated_home: Path):
        assert installs_manifest.list_installs() == []

    def test_get_returns_none_when_empty(self, isolated_home: Path, tmp_path: Path):
        assert installs_manifest.get_install('cursor', tmp_path) is None


class TestRecordInstall:
    def test_writes_manifest_file(self, isolated_home: Path, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        files = [target / '.cursor' / 'rules' / 'a.mdc']
        dirs = [target / '.cursor' / 'rules', target / '.cursor']
        installs_manifest.record_install('cursor', target, files=files, directories=dirs)

        manifest_file = isolated_home / 'installs.json'
        assert manifest_file.is_file()
        data = json.loads(manifest_file.read_text(encoding='utf-8'))
        assert data['schema_version'] == 1
        assert len(data['installs']) == 1
        rec = data['installs'][0]
        assert rec['tool'] == 'cursor'
        assert rec['target'] == str(target.resolve())

    def test_paths_stored_relative_to_target(self, isolated_home: Path, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        installs_manifest.record_install(
            'cursor', target,
            files=[target / '.cursor' / 'rules' / 'helm.mdc'],
            directories=[target / '.cursor' / 'rules'],
        )
        rec = installs_manifest.get_install('cursor', target)
        assert rec is not None
        assert '.cursor/rules/helm.mdc' in rec.files
        assert '.cursor/rules' in rec.directories

    def test_re_recording_replaces_existing_entry(self, isolated_home: Path, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        installs_manifest.record_install(
            'cursor', target, files=[target / 'a.mdc'], directories=[],
        )
        installs_manifest.record_install(
            'cursor', target, files=[target / 'b.mdc'], directories=[],
        )
        recs = [r for r in installs_manifest.list_installs() if r.tool == 'cursor']
        assert len(recs) == 1
        assert recs[0].files == ['b.mdc']

    def test_multiple_tools_per_target_kept_separate(self, isolated_home: Path, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        installs_manifest.record_install(
            'cursor', target, files=[target / 'a.mdc'], directories=[],
        )
        installs_manifest.record_install(
            'aider', target, files=[target / 'CONVENTIONS.md'], directories=[],
        )
        assert len(installs_manifest.list_installs()) == 2
        assert installs_manifest.get_install('cursor', target) is not None
        assert installs_manifest.get_install('aider', target) is not None


class TestRemoveInstall:
    def test_removes_entry(self, isolated_home: Path, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        installs_manifest.record_install('cursor', target, files=[], directories=[])
        removed = installs_manifest.remove_install('cursor', target)
        assert removed is not None
        assert removed.tool == 'cursor'
        assert installs_manifest.get_install('cursor', target) is None

    def test_returns_none_when_not_present(self, isolated_home: Path, tmp_path: Path):
        assert installs_manifest.remove_install('cursor', tmp_path) is None

    def test_only_removes_matching_target_and_tool(
        self, isolated_home: Path, tmp_path: Path,
    ):
        target_a = tmp_path / 'a'; target_a.mkdir()
        target_b = tmp_path / 'b'; target_b.mkdir()
        installs_manifest.record_install('cursor', target_a, files=[], directories=[])
        installs_manifest.record_install('cursor', target_b, files=[], directories=[])
        installs_manifest.remove_install('cursor', target_a)
        assert installs_manifest.get_install('cursor', target_a) is None
        assert installs_manifest.get_install('cursor', target_b) is not None


# ─── enumerate_writes ───────────────────────────────────────────────────────


class TestEnumerateWrites:
    def test_lists_files_and_new_dirs(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        (src / 'sub' / 'deeper').mkdir(parents=True)
        target.mkdir()
        (src / 'a.md').write_text('x', encoding='utf-8')
        (src / 'sub' / 'b.md').write_text('y', encoding='utf-8')
        (src / 'sub' / 'deeper' / 'c.md').write_text('z', encoding='utf-8')

        files, dirs = installs_manifest.enumerate_writes(src, target)
        # 3 files
        assert len(files) == 3
        # 2 new dirs (sub, sub/deeper)
        assert len(dirs) == 2

    def test_existing_dir_not_listed_as_created(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        (src / 'agents').mkdir(parents=True)
        (target / 'agents').mkdir(parents=True)
        (src / 'agents' / 'helm.md').write_text('x', encoding='utf-8')

        files, dirs = installs_manifest.enumerate_writes(src, target)
        assert len(files) == 1
        # `agents/` already existed at target — not orquestrum-owned
        assert dirs == []

    def test_ignore_filenames_skipped(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        src.mkdir()
        target.mkdir()
        (src / 'keep.md').write_text('x', encoding='utf-8')
        (src / 'settings.json').write_text('{}', encoding='utf-8')
        files, _ = installs_manifest.enumerate_writes(
            src, target, ignore_filenames={'settings.json'},
        )
        assert len(files) == 1
        assert files[0].name == 'keep.md'

    def test_missing_src_returns_empty(self, tmp_path: Path):
        files, dirs = installs_manifest.enumerate_writes(
            tmp_path / 'missing', tmp_path / 'target',
        )
        assert files == [] and dirs == []


# ─── surgical_uninstall ────────────────────────────────────────────────────


class TestSurgicalUninstall:
    def test_removes_only_recorded_files(
        self, isolated_home: Path, tmp_path: Path,
    ):
        target = tmp_path / 'project'
        (target / '.cursor' / 'rules').mkdir(parents=True)
        # Two orquestrum files + one user file in the same dir
        ours_a = target / '.cursor' / 'rules' / 'helm-the-architect.mdc'
        ours_b = target / '.cursor' / 'rules' / 'lore-product-strategist.mdc'
        user_extra = target / '.cursor' / 'rules' / 'my-personal-rule.mdc'
        for f in (ours_a, ours_b, user_extra):
            f.write_text('rules', encoding='utf-8')

        installs_manifest.record_install(
            'cursor', target,
            files=[ours_a, ours_b],
            directories=[target / '.cursor' / 'rules', target / '.cursor'],
        )

        removed_files, removed_dirs = installs_manifest.surgical_uninstall(
            'cursor', target,
        )
        assert sorted(removed_files) == sorted([
            '.cursor/rules/helm-the-architect.mdc',
            '.cursor/rules/lore-product-strategist.mdc',
        ])
        # Critically: user file untouched
        assert user_extra.is_file()
        assert user_extra.read_text() == 'rules'
        # `.cursor/rules/` not removed because user file still in it
        assert (target / '.cursor' / 'rules').is_dir()
        # `.cursor/` not removed either (still has rules/ child)
        assert (target / '.cursor').is_dir()

    def test_removes_empty_dirs_orquestrum_created(
        self, isolated_home: Path, tmp_path: Path,
    ):
        target = tmp_path / 'project'
        (target / '.sdd' / 'docs').mkdir(parents=True)
        f = target / '.sdd' / 'docs' / 'SDLC.md'
        f.write_text('x', encoding='utf-8')
        installs_manifest.record_install(
            'claude-code', target,
            files=[f],
            directories=[target / '.sdd' / 'docs', target / '.sdd'],
        )
        installs_manifest.surgical_uninstall('claude-code', target)
        # Both dirs gone (were empty)
        assert not (target / '.sdd' / 'docs').exists()
        assert not (target / '.sdd').exists()

    def test_drops_manifest_entry_on_completion(
        self, isolated_home: Path, tmp_path: Path,
    ):
        target = tmp_path / 'project'
        target.mkdir()
        installs_manifest.record_install(
            'cursor', target, files=[], directories=[],
        )
        installs_manifest.surgical_uninstall('cursor', target)
        assert installs_manifest.get_install('cursor', target) is None

    def test_no_manifest_returns_empty_lists(
        self, isolated_home: Path, tmp_path: Path,
    ):
        files, dirs = installs_manifest.surgical_uninstall('cursor', tmp_path)
        assert files == [] and dirs == []

    def test_missing_files_silently_skipped(
        self, isolated_home: Path, tmp_path: Path,
    ):
        target = tmp_path / 'project'
        target.mkdir()
        # Record a file that doesn't exist on disk (already removed externally)
        installs_manifest.record_install(
            'cursor', target,
            files=[target / 'gone.mdc'],
            directories=[],
        )
        removed_files, _ = installs_manifest.surgical_uninstall('cursor', target)
        assert removed_files == []  # nothing actually removed (already gone)
        # Manifest still cleaned up
        assert installs_manifest.get_install('cursor', target) is None


# ─── corrupt manifest tolerance ────────────────────────────────────────────


class TestCorruptManifest:
    def test_invalid_json_treated_as_empty(self, isolated_home: Path):
        (isolated_home / 'installs.json').write_text('not json', encoding='utf-8')
        # Doesn't crash — returns empty
        assert installs_manifest.list_installs() == []

    def test_missing_installs_key_treated_as_empty(self, isolated_home: Path):
        (isolated_home / 'installs.json').write_text(
            json.dumps({'schema_version': 1}), encoding='utf-8',
        )
        assert installs_manifest.list_installs() == []
