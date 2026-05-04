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

    def test_check_modules_all_present_returns_true(self, monkeypatch: pytest.MonkeyPatch):
        """New schema: `check_modules` lists every required import name.
        All present → True."""
        monkeypatch.setitem(extras._EXTRAS, 'multi-real', {
            'description': 'Multi-module extra (all real)',
            'check_modules': ['sys', 'os', 'json'],
            'packages': [],
            'system_hint': {},
        })
        try:
            assert extras._is_installed('multi-real') is True
        finally:
            del extras._EXTRAS['multi-real']

    def test_check_modules_one_missing_returns_false(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Partial install scenario: one of N modules is missing — extra
        must be reported as missing, not installed. This is the bug the
        screenshot revealed (jinja2 missing while fastapi present)."""
        monkeypatch.setitem(extras._EXTRAS, 'partial', {
            'description': 'Has sys + missing module',
            'check_modules': ['sys', 'orquestrum_definitely_not_real_xyz'],
            'packages': [],
            'system_hint': {},
        })
        try:
            assert extras._is_installed('partial') is False
        finally:
            del extras._EXTRAS['partial']

    def test_ui_extra_actually_uses_check_modules(self):
        """Sanity-check: the real `ui` extra entry uses the new schema
        and lists every runtime-required module the web server imports."""
        meta = extras._EXTRAS['ui']
        assert 'check_modules' in meta
        # All these are imported transitively when `orquestrum web` starts;
        # if any is omitted, partial-install detection breaks.
        for required in ('fastapi', 'uvicorn', 'jinja2', 'mistune', 'multipart'):
            assert required in meta['check_modules'], (
                f'ui extra is missing {required!r} from check_modules — '
                f'partial installs without it would falsely report ui as installed'
            )


class TestAliases:
    def test_resolve_known_alias(self):
        assert extras._resolve('web') == 'ui'

    def test_resolve_unknown_returns_input(self):
        # Non-aliased names (canonical or invalid) pass through unchanged
        assert extras._resolve('ui') == 'ui'
        assert extras._resolve('webview') == 'webview'
        assert extras._resolve('made-up') == 'made-up'

    def test_all_choices_includes_aliases(self):
        choices = extras._all_choices()
        assert 'ui' in choices
        assert 'web' in choices
        assert 'webview' in choices

    def test_install_handler_resolves_web_to_ui(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """`extras install web` should drive the same install as `ui`
        — that's the whole point of the alias (user expectation: command
        is `orquestrum web` so the extra should be installable as `web`)."""
        called: list[list[str]] = []
        monkeypatch.setattr(extras, '_install', lambda names: called.append(names) or 0)
        ns = argparse.Namespace(extras_cmd='install', names=['web'])
        rc = extras._handler(ns)
        assert rc == 0
        assert called == [['ui']]   # alias resolved before _install

    def test_install_handler_dedups_alias_and_canonical(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """If the user types both `web` and `ui`, install once."""
        called: list[list[str]] = []
        monkeypatch.setattr(extras, '_install', lambda names: called.append(names) or 0)
        ns = argparse.Namespace(extras_cmd='install', names=['web', 'ui'])
        extras._handler(ns)
        assert called == [['ui']]   # deduped to single entry


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
