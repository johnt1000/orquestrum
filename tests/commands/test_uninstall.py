"""End-user uninstall flow: `orquestrum uninstall`.

Project removal, --all, --self, and --dry-run are all covered. The CLI
self-removal subprocess is patched out — we never run `pip uninstall` for real.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

import pytest

from orquestrum.commands import uninstall
from orquestrum.lib import registry


class TestDescribeRemoval:
    def test_lists_orquestrum_files_for_claude_code(self, initialized_project: Path):
        # Pretend a claude-code agent file is present
        agents_dir = initialized_project / '.claude' / 'agents'
        agents_dir.mkdir(parents=True)
        (initialized_project / '.sdd').mkdir()
        (agents_dir / 'helm-the-architect.md').write_text('---\nname: x\n---', encoding='utf-8')

        items = uninstall._describe_removal(initialized_project, 'claude-code')
        assert any('.sdd/' in item for item in items)
        # v0.5 fixture: manifest lives at .orquestrum/manifest.md, not at root
        assert any('.orquestrum/' in item for item in items)
        assert any('registry entry' in item for item in items)

    def test_lists_legacy_orquestrum_md_when_present(self, initialized_project: Path):
        """Legacy v0.4 projects had ORQUESTRUM.md at the root. Uninstall
        must still surface it for removal so old projects clean up cleanly."""
        # Add the legacy file alongside the v0.5 layout
        (initialized_project / 'ORQUESTRUM.md').write_text('# legacy', encoding='utf-8')
        items = uninstall._describe_removal(initialized_project, 'claude-code')
        assert any('ORQUESTRUM.md' in item for item in items)

    def test_lists_files_for_opencode(self, initialized_project: Path):
        agents_dir = initialized_project / '.opencode' / 'agents'
        agents_dir.mkdir(parents=True)
        (initialized_project / '.opencode' / 'docs').mkdir()
        (agents_dir / 'helm-the-architect.md').write_text('---\nname: x\n---', encoding='utf-8')
        items = uninstall._describe_removal(initialized_project, 'opencode')
        assert any('.opencode/docs/' in item for item in items)


class TestProjectUninstall:
    def test_returns_1_outside_project(
        self, project_root: Path, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        # No .orquestrum/ in project_root
        rc = uninstall._uninstall_project(project_root, yes=True)
        assert rc == 1
        err = capsys.readouterr().err
        assert 'not in an Orquestrum project' in err

    def test_dry_run_does_not_delete(
        self, initialized_project: Path, capsys: pytest.CaptureFixture,
    ):
        rc = uninstall._uninstall_project(initialized_project, yes=True, dry_run=True)
        assert rc == 0
        # .orquestrum still present after dry-run
        assert (initialized_project / '.orquestrum').is_dir()
        out = capsys.readouterr().out
        assert '(dry-run)' in out

    def test_removes_orquestrum_dir_and_manifest(
        self, initialized_project: Path, capsys: pytest.CaptureFixture,
    ):
        registry.register_project(name='to-remove', path=initialized_project)
        rc = uninstall._uninstall_project(initialized_project, yes=True)
        assert rc == 0
        assert not (initialized_project / '.orquestrum').is_dir()
        assert not (initialized_project / 'ORQUESTRUM.md').exists()
        assert registry.find_by_path(initialized_project) is None


class TestUninstallAll:
    def test_no_projects_short_circuits(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        rc = uninstall._uninstall_all(yes=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No projects registered' in out

    def test_dry_run_lists_without_deleting(
        self, initialized_project: Path, capsys: pytest.CaptureFixture, isolated_home: Path,
    ):
        registry.register_project(name='alpha', path=initialized_project, tool='claude-code')
        rc = uninstall._uninstall_all(yes=True, dry_run=True)
        assert rc == 0
        # Still there
        assert (initialized_project / '.orquestrum').is_dir()
        out = capsys.readouterr().out
        assert '(dry-run)' in out
        assert 'alpha' in out

    def test_skips_paths_that_no_longer_exist(
        self, isolated_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        ghost = tmp_path / 'ghost-proj'
        ghost.mkdir()
        registry.register_project(name='ghost', path=ghost)
        ghost.rmdir()
        rc = uninstall._uninstall_all(yes=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'skipped' in out


class TestUninstallSelf:
    def test_dry_run_prints_command_only(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_detect_env', lambda: 'uv-tool')
        rc = uninstall._uninstall_self(yes=True, dry_run=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'uv tool uninstall orquestrum' in out
        assert '(dry-run)' in out

    def test_invokes_subprocess_when_yes(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_detect_env', lambda: 'venv')

        captured: dict = {}

        def fake_run(cmd, **kw):
            captured['cmd'] = cmd
            class _Ret:
                returncode = 0
            return _Ret()

        monkeypatch.setattr(subprocess, 'run', fake_run)
        rc = uninstall._uninstall_self(yes=True)
        assert rc == 0
        assert captured['cmd'][:2] == ['pip', 'uninstall']

    def test_unknown_env_prints_manual_instructions(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_detect_env', lambda: 'unknown')
        rc = uninstall._uninstall_self(yes=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'uv tool uninstall' in out
        assert 'pip uninstall' in out


class TestHandlerDispatch:
    def test_self_uninstall_routes_to_self(
        self, monkeypatch: pytest.MonkeyPatch, isolated_home: Path,
    ):
        captured: dict = {}
        monkeypatch.setattr(uninstall, '_uninstall_self',
                            lambda **kw: captured.update(kw) or 0)
        ns = argparse.Namespace(self_uninstall=True, all_=False, yes=True, dry_run=False)
        assert uninstall._handler(ns) == 0
        assert captured == {'yes': True, 'dry_run': False}

    def test_all_routes_to_all(
        self, monkeypatch: pytest.MonkeyPatch, isolated_home: Path,
    ):
        captured: dict = {}
        monkeypatch.setattr(uninstall, '_uninstall_all',
                            lambda **kw: captured.update(kw) or 0)
        ns = argparse.Namespace(self_uninstall=False, all_=True, yes=True, dry_run=True)
        uninstall._handler(ns)
        assert captured == {'yes': True, 'dry_run': True}

    def test_default_routes_to_project(
        self, monkeypatch: pytest.MonkeyPatch, project_root: Path,
        isolated_home: Path,
    ):
        captured: dict = {}

        def fake_project(root, **kw):
            captured['root'] = root
            captured.update(kw)
            return 0

        monkeypatch.setattr(uninstall, '_uninstall_project', fake_project)
        ns = argparse.Namespace(self_uninstall=False, all_=False, yes=True, dry_run=False)
        uninstall._handler(ns)
        assert captured['root'] == project_root
        assert captured['yes'] is True


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        uninstall.register(sub)
        assert 'uninstall' in sub.choices
