"""Unit tests for `orquestrum extras` — list and install optional dependency groups."""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

import pytest

from orquestrum.commands import extras


def _ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


class TestExtrasList:
    def test_register_creates_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        extras.register(sub)
        assert 'extras' in sub.choices

    def test_list_when_called_without_subcmd(
        self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch,
    ):
        # Force `ui` and `webview` reported as missing for deterministic output
        monkeypatch.setattr(extras, '_is_installed', lambda name: False)
        rc = extras._handler(_ns(extras_cmd=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'Available extras' in out
        assert 'ui' in out and 'webview' in out
        assert 'orquestrum extras install' in out

    def test_list_shows_all_installed_message(
        self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(extras, '_is_installed', lambda name: True)
        rc = extras._handler(_ns(extras_cmd=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'All extras installed' in out


class TestIsInstalledHelper:
    def test_returns_true_for_installed_module(self, monkeypatch: pytest.MonkeyPatch):
        # 'sys' is always importable
        monkeypatch.setitem(extras._EXTRAS, 'fake-real', {
            'description': 'Always-real module',
            'check': 'sys',
            'packages': [],
            'system_hint': {},
        })
        try:
            assert extras._is_installed('fake-real') is True
        finally:
            del extras._EXTRAS['fake-real']

    def test_returns_false_for_missing_module(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(extras._EXTRAS, 'fake-missing', {
            'description': 'Bogus module that cannot exist',
            'check': 'orquestrum_definitely_not_real_module_xyz',
            'packages': [],
            'system_hint': {},
        })
        try:
            assert extras._is_installed('fake-missing') is False
        finally:
            del extras._EXTRAS['fake-missing']


class TestDetectEnv:
    def test_detects_venv_when_pyvenv_cfg_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        prefix = tmp_path / 'venv'
        prefix.mkdir()
        (prefix / 'pyvenv.cfg').write_text('home = /usr/bin\n', encoding='utf-8')
        monkeypatch.setattr('sys.prefix', str(prefix))
        assert extras._detect_env() == 'venv'

    def test_detects_unknown_when_no_markers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        prefix = tmp_path / 'plain'
        prefix.mkdir()
        monkeypatch.setattr('sys.prefix', str(prefix))
        assert extras._detect_env() == 'unknown'

    def test_detects_uv_tool_under_xdg_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        # Build a fake uv tool layout under HOME/.local/share/uv/tools/orquestrum
        fake_home = tmp_path / 'home'
        prefix = fake_home / '.local' / 'share' / 'uv' / 'tools' / 'orquestrum'
        prefix.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        monkeypatch.setattr('sys.prefix', str(prefix))
        assert extras._detect_env() == 'uv-tool'


class TestInstall:
    def test_venv_path_invokes_uv_sync(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        captured: dict = {}

        def fake_run(cmd, **kw):
            captured['cmd'] = cmd
            class _Ret:
                returncode = 0
            return _Ret()

        monkeypatch.setattr(extras, '_detect_env', lambda: 'venv')
        monkeypatch.setattr(subprocess, 'run', fake_run)
        rc = extras._install(['ui'])
        assert rc == 0
        assert captured['cmd'][:2] == ['uv', 'sync']
        assert '--extra' in captured['cmd']
        assert 'ui' in captured['cmd']

    def test_uv_tool_path_includes_with_packages(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        captured: dict = {}

        def fake_run(cmd, **kw):
            captured['cmd'] = cmd
            class _Ret:
                returncode = 0
            return _Ret()

        monkeypatch.setattr(extras, '_detect_env', lambda: 'uv-tool')
        monkeypatch.setattr(subprocess, 'run', fake_run)
        rc = extras._install(['ui'])
        assert rc == 0
        # Expect `uv tool install orquestrum --with <pkg> ...`
        assert captured['cmd'][:3] == ['uv', 'tool', 'install']
        assert '--with' in captured['cmd']

    def test_unknown_env_prints_manual_command(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        monkeypatch.setattr(extras, '_detect_env', lambda: 'unknown')
        rc = extras._install(['ui', 'webview'])
        assert rc == 0
        out = capsys.readouterr().out
        assert 'pip install "orquestrum[ui,webview]"' in out
        assert 'uv sync --extra ui --extra webview' in out

    def test_handler_routes_to_install_when_subcmd_set(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        called = {}

        def fake_install(names):
            called['names'] = names
            return 0

        monkeypatch.setattr(extras, '_install', fake_install)
        rc = extras._handler(_ns(extras_cmd='install', names=['ui']))
        assert rc == 0
        assert called['names'] == ['ui']
