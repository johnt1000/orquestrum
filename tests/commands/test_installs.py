"""Tests for `orquestrum installs` — manifest list + prune.

Coverage:
  - argparse: list + prune subcommands registered
  - list: empty, populated, marks stale/retired
  - prune --dry-run: counts but doesn't write
  - prune: removes stale + retired, writes backup, keeps valid
  - lib.installs_manifest helpers: classify_stale + prune_stale
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path

import pytest

from orquestrum.commands import installs as installs_cmd
from orquestrum.lib import installs_manifest as im


# ─── helper ────────────────────────────────────────────────────────────────


def _seed_manifest(home: Path, records: list[dict]) -> Path:
    """Write a synthetic installs.json with the given records."""
    path = home / 'installs.json'
    path.write_text(json.dumps({
        'schema_version': 1,
        'installs': records,
    }), encoding='utf-8')
    return path


def _record(target: str, tool: str = 'claude-code',
            version: str = '0.5.1') -> dict:
    return {
        'target': target,
        'tool': tool,
        'orquestrum_version': version,
        'installed_at': '2026-05-03T10:00:00',
        'files': ['agents/x.md'],
        'directories': ['agents'],
    }


# ─── lib helpers ───────────────────────────────────────────────────────────


class TestClassifyStale:
    def test_empty_returns_empty_buckets(self):
        result = im.classify_stale([])
        assert result == {'stale_target': [], 'retired_tool': [], 'valid': []}

    def test_separates_three_buckets(
        self, isolated_home: Path, tmp_path: Path,
    ):
        valid_target = tmp_path / 'real-project'
        valid_target.mkdir()
        records = [
            im.ToolInstall.from_dict(_record(str(valid_target), 'claude-code')),
            im.ToolInstall.from_dict(_record(str(tmp_path / 'gone'), 'claude-code')),
            im.ToolInstall.from_dict(_record(str(valid_target), 'aider')),  # retired
            im.ToolInstall.from_dict(_record(str(valid_target), 'cursor')),  # retired
        ]
        result = im.classify_stale(records)
        assert len(result['valid']) == 1
        assert len(result['stale_target']) == 1
        assert len(result['retired_tool']) == 2

    def test_retired_tool_takes_precedence_over_stale_target(
        self, isolated_home: Path, tmp_path: Path,
    ):
        """A retired-tool entry whose target is ALSO gone counts as
        retired (the more actionable category)."""
        record = im.ToolInstall.from_dict(_record(str(tmp_path / 'gone'), 'aider'))
        result = im.classify_stale([record])
        assert len(result['retired_tool']) == 1
        assert len(result['stale_target']) == 0


class TestPruneStale:
    def test_dry_run_does_not_write(
        self, isolated_home: Path, tmp_path: Path,
    ):
        path = _seed_manifest(isolated_home, [
            _record(str(tmp_path / 'gone'), 'claude-code'),
            _record(str(tmp_path / 'gone2'), 'aider'),
        ])
        before = path.read_text()
        removed_stale, removed_retired, kept = im.prune_stale(dry_run=True)
        assert removed_stale == 1
        assert removed_retired == 1
        assert kept == 0
        # File untouched
        assert path.read_text() == before

    def test_prune_removes_dead_keeps_valid(
        self, isolated_home: Path, tmp_path: Path,
    ):
        valid = tmp_path / 'real'
        valid.mkdir()
        _seed_manifest(isolated_home, [
            _record(str(valid), 'claude-code'),
            _record(str(tmp_path / 'gone'), 'claude-code'),
            _record(str(valid), 'aider'),
        ])
        removed_stale, removed_retired, kept = im.prune_stale(dry_run=False)
        assert removed_stale == 1
        assert removed_retired == 1
        assert kept == 1
        # Disk reflects the trimmed manifest
        survivors = im.list_installs()
        assert len(survivors) == 1
        assert survivors[0].tool == 'claude-code'
        assert survivors[0].target == str(valid)

    def test_prune_clean_manifest_is_noop(
        self, isolated_home: Path, tmp_path: Path,
    ):
        valid = tmp_path / 'real'
        valid.mkdir()
        _seed_manifest(isolated_home, [_record(str(valid))])
        removed_stale, removed_retired, kept = im.prune_stale(dry_run=False)
        assert (removed_stale, removed_retired, kept) == (0, 0, 1)


# ─── argparse + handlers ───────────────────────────────────────────────────


class TestRegister:
    def test_subcommands_registered(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        installs_cmd.register(sub)
        assert 'installs' in sub.choices
        sub_actions = [a for a in sub.choices['installs']._actions
                       if isinstance(a, argparse._SubParsersAction)]
        assert sub_actions
        assert set(sub_actions[0].choices) == {'list', 'prune'}


class TestList:
    def test_empty_manifest_prints_setup_hint(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        # No installs.json → empty
        rc = installs_cmd._list(argparse.Namespace())
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No installs recorded' in out

    def test_lists_with_marks_for_stale_and_retired(
        self, isolated_home: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ):
        valid = tmp_path / 'real'
        valid.mkdir()
        _seed_manifest(isolated_home, [
            _record(str(valid), 'claude-code'),
            _record(str(tmp_path / 'gone'), 'claude-code'),
            _record(str(valid), 'aider'),
        ])
        rc = installs_cmd._list(argparse.Namespace())
        assert rc == 0
        out = capsys.readouterr().out
        assert '3 install record(s)' in out
        assert '✓' in out  # at least one valid
        assert '✗' in out  # stale or retired
        assert 'stale' in out
        assert 'retired' in out
        assert 'orquestrum installs prune' in out  # call to action


class TestPrune:
    def test_dry_run_prints_plan_does_not_write(
        self, isolated_home: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ):
        path = _seed_manifest(isolated_home, [
            _record(str(tmp_path / 'gone'), 'claude-code'),
        ])
        before = path.read_text()
        rc = installs_cmd._prune(argparse.Namespace(dry_run=True))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'Prune plan' in out
        assert 'dry-run' in out
        # File untouched
        assert path.read_text() == before

    def test_prune_writes_and_creates_backup(
        self, isolated_home: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ):
        valid = tmp_path / 'real'
        valid.mkdir()
        path = _seed_manifest(isolated_home, [
            _record(str(valid), 'claude-code'),
            _record(str(tmp_path / 'gone'), 'claude-code'),
        ])
        rc = installs_cmd._prune(argparse.Namespace(dry_run=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert '✓ Pruned' in out
        # Backup exists with today's date
        date = dt.date.today().strftime('%Y%m%d')
        backup = path.with_suffix(f'.json.bak.{date}')
        assert backup.exists()
        # Backup matches pre-prune content (2 entries)
        backup_data = json.loads(backup.read_text())
        assert len(backup_data['installs']) == 2
        # Live manifest now has 1 entry
        live = json.loads(path.read_text())
        assert len(live['installs']) == 1

    def test_clean_manifest_prints_no_op_message(
        self, isolated_home: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ):
        valid = tmp_path / 'real'
        valid.mkdir()
        _seed_manifest(isolated_home, [_record(str(valid))])
        rc = installs_cmd._prune(argparse.Namespace(dry_run=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'clean' in out
        assert 'Pruned' not in out
