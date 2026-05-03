"""Unit tests for `orquestrum doctor` — the developer/installer health-check.

These tests target individual checks instead of running the full handler against
the live system, so they are deterministic across machines.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from orquestrum.commands import doctor


class TestReport:
    def test_ok_does_not_increment_counters(self, capsys: pytest.CaptureFixture):
        r = doctor.Report()
        r.ok('python', 'detail')
        assert r.errors == 0 and r.warnings == 0
        assert r.results[0]['status'] == 'ok'
        out = capsys.readouterr().out
        assert 'python' in out

    def test_fail_increments_errors(self, capsys: pytest.CaptureFixture):
        r = doctor.Report()
        r.fail('uv', detail='missing', fix='install uv')
        assert r.errors == 1
        out = capsys.readouterr().out
        assert 'fix:' in out
        assert 'install uv' in out

    def test_warn_increments_warnings(self, capsys: pytest.CaptureFixture):
        r = doctor.Report()
        r.warn('extra', detail='missing', fix='install it')
        assert r.warnings == 1
        out = capsys.readouterr().out
        assert 'install it' in out

    def test_section_prints_blank_line_then_title(self, capsys: pytest.CaptureFixture):
        r = doctor.Report()
        r.section('Runtime')
        out = capsys.readouterr().out
        assert 'Runtime' in out


class TestPythonCheck:
    def test_passes_on_modern_python(self, capsys: pytest.CaptureFixture):
        r = doctor.Report()
        doctor._check_python(r)
        # 3.12+ required by pyproject.toml — always green here
        assert r.errors == 0
        assert any(res['status'] == 'ok' and res['label'].startswith('python') for res in r.results)


class TestUvCheck:
    def test_marks_fail_when_uv_missing(self, monkeypatch: pytest.MonkeyPatch):
        import shutil
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        r = doctor.Report()
        doctor._check_uv(r)
        assert r.errors == 1
        assert any('uv installed' in res['label'] for res in r.results)

    def test_marks_ok_when_uv_present(self, monkeypatch: pytest.MonkeyPatch):
        import shutil
        monkeypatch.setattr(shutil, 'which', lambda name: '/usr/local/bin/uv')

        class _Out:
            stdout = 'uv 0.6.0\n'
            stderr = ''

        monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: _Out())
        r = doctor.Report()
        doctor._check_uv(r)
        assert r.errors == 0
        assert any('uv installed' in res['label'] and res['status'] == 'ok' for res in r.results)


class TestInstallMethodCheck:
    def test_uv_tool_marks_ok(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_detect_env', lambda: 'uv-tool')
        r = doctor.Report()
        doctor._check_orquestrum_install(r)
        assert r.errors == 0 and r.warnings == 0
        assert any('uv tool' in (res.get('detail') or '') for res in r.results)

    def test_unknown_marks_warning(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_detect_env', lambda: 'unknown')
        r = doctor.Report()
        doctor._check_orquestrum_install(r)
        assert r.warnings == 1


class TestExtrasCheck:
    def test_missing_ui_extra_yields_warning(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.commands import extras
        monkeypatch.setattr(extras, '_is_installed', lambda name: False)
        r = doctor.Report()
        doctor._check_extras(r)
        # Both ui and webview are missing → 2 warnings
        assert r.warnings >= 1
        assert any('ui' in res['label'] for res in r.results)


class TestIntegrationsCheck:
    def test_user_mode_reports_bundled_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        # No dev repo found → bundled source reported, cache used
        from orquestrum.lib import paths as paths_mod
        monkeypatch.setattr(paths_mod, 'find_canonical_root', lambda *a, **kw: None)
        bundle = tmp_path / 'bundle'
        bundle.mkdir()
        from orquestrum.lib import assets as assets_mod
        monkeypatch.setattr(assets_mod, 'assets_root', lambda: bundle)
        cache = tmp_path / 'cache'
        monkeypatch.setenv('ORQUESTRUM_CACHE', str(cache))
        r = doctor.Report()
        doctor._check_integrations(r)
        # Source report present
        assert any('SDD source' in res['label'] for res in r.results)
        assert any('bundled' in (res.get('detail') or '') for res in r.results)
        # Cache missing → warning
        assert r.warnings == 1

    def test_missing_cache_dir_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        from orquestrum.lib import paths as paths_mod
        monkeypatch.setattr(paths_mod, 'find_canonical_root', lambda *a, **kw: None)
        cache = tmp_path / 'never-created'
        monkeypatch.setenv('ORQUESTRUM_CACHE', str(cache))
        r = doctor.Report()
        doctor._check_integrations(r)
        assert r.warnings == 1
        assert any('orquestrum convert' in (res.get('fix') or '') for res in r.results)

    def test_complete_cache_marks_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        from orquestrum.lib import paths as paths_mod
        monkeypatch.setattr(paths_mod, 'find_canonical_root', lambda *a, **kw: None)
        cache = tmp_path / 'cache'
        for tool in ('claude-code', 'opencode', 'cursor', 'aider', 'windsurf'):
            (cache / tool).mkdir(parents=True)
        monkeypatch.setenv('ORQUESTRUM_CACHE', str(cache))
        r = doctor.Report()
        doctor._check_integrations(r)
        # 1 ok for source + 1 ok for cache = 0 warnings
        assert r.errors == 0 and r.warnings == 0
        assert any('5 tools' in (res.get('detail') or '') for res in r.results)


class TestRegistryCheck:
    def test_empty_registry_marks_ok(self, isolated_home: Path):
        r = doctor.Report()
        doctor._check_registry(r)
        assert r.errors == 0 and r.warnings == 0
        assert any('empty' in (res.get('detail') or '') for res in r.results)

    def test_stale_registry_warns(
        self, isolated_home: Path, tmp_path: Path,
    ):
        from orquestrum.lib import registry
        ghost = tmp_path / 'ghost-project'
        ghost.mkdir()
        registry.register_project(name='ghost', path=ghost)
        ghost.rmdir()
        r = doctor.Report()
        doctor._check_registry(r)
        assert r.warnings == 1
        assert any('stale' in (res.get('detail') or '') for res in r.results)


class TestCurrentProjectCheck:
    def test_skips_when_not_a_project(
        self, project_root: Path, isolated_home: Path,
    ):
        r = doctor.Report()
        doctor._check_current_project(r)
        assert r.errors == 0 and r.warnings == 0
        assert any('skipped' in (res.get('detail') or '') for res in r.results)

    def test_complete_project_marks_ok(self, initialized_project: Path):
        r = doctor.Report()
        doctor._check_current_project(r)
        assert r.errors == 0 and r.warnings == 0

    def test_partial_project_warns(self, project_root: Path):
        # Has ORQUESTRUM.md but no .orquestrum/
        (project_root / 'ORQUESTRUM.md').write_text('# Manifest', encoding='utf-8')
        r = doctor.Report()
        doctor._check_current_project(r)
        assert r.warnings == 1
        assert any('incomplete' in (res.get('detail') or '') for res in r.results)


class TestHandler:
    def test_returns_0_when_no_errors(
        self, monkeypatch: pytest.MonkeyPatch, isolated_home: Path,
        project_root: Path, capsys: pytest.CaptureFixture,
    ):
        # Force everything to OK
        monkeypatch.setattr(doctor, '_check_python', lambda r: r.ok('python'))
        monkeypatch.setattr(doctor, '_check_uv', lambda r: r.ok('uv'))
        monkeypatch.setattr(doctor, '_check_orquestrum_install', lambda r: r.ok('install'))
        monkeypatch.setattr(doctor, '_check_extras', lambda r: r.ok('extras'))
        monkeypatch.setattr(doctor, '_check_integrations', lambda r: r.ok('integrations'))
        monkeypatch.setattr(doctor, '_check_registry', lambda r: r.ok('registry'))
        monkeypatch.setattr(doctor, '_check_current_project', lambda r: r.ok('current'))

        ns = argparse.Namespace(as_json=False)
        rc = doctor._handler(ns)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'all required checks passed' in out

    def test_returns_1_on_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        monkeypatch.setattr(doctor, '_check_python', lambda r: r.fail('python', detail='too old'))
        monkeypatch.setattr(doctor, '_check_uv', lambda r: r.ok('uv'))
        monkeypatch.setattr(doctor, '_check_orquestrum_install', lambda r: r.ok('install'))
        monkeypatch.setattr(doctor, '_check_extras', lambda r: None)
        monkeypatch.setattr(doctor, '_check_integrations', lambda r: None)
        monkeypatch.setattr(doctor, '_check_registry', lambda r: None)
        monkeypatch.setattr(doctor, '_check_current_project', lambda r: None)

        ns = argparse.Namespace(as_json=False)
        rc = doctor._handler(ns)
        assert rc == 1
        out = capsys.readouterr().out
        assert 'error(s)' in out

    def test_json_emits_machine_readable_summary(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        monkeypatch.setattr(doctor, '_check_python', lambda r: r.ok('python'))
        monkeypatch.setattr(doctor, '_check_uv', lambda r: r.warn('uv', 'missing'))
        monkeypatch.setattr(doctor, '_check_orquestrum_install', lambda r: None)
        monkeypatch.setattr(doctor, '_check_extras', lambda r: None)
        monkeypatch.setattr(doctor, '_check_integrations', lambda r: None)
        monkeypatch.setattr(doctor, '_check_registry', lambda r: None)
        monkeypatch.setattr(doctor, '_check_current_project', lambda r: None)

        ns = argparse.Namespace(as_json=True)
        doctor._handler(ns)
        out = capsys.readouterr().out
        import json
        # Last JSON object on stdout is the summary
        # Find first '{' after stripping color codes
        start = out.index('{')
        end = out.rindex('}') + 1
        summary = json.loads(out[start:end])
        assert summary['warnings'] == 1
        assert summary['errors'] == 0


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        doctor.register(sub)
        assert 'doctor' in sub.choices
