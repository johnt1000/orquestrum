"""Tests for `orquestrum web` — the local FastAPI console launcher.

We don't actually start uvicorn or pywebview. Network code paths are
swapped out with stubs; the test asserts dispatch + error handling.
"""
from __future__ import annotations
import argparse
import builtins
from pathlib import Path

import pytest

from orquestrum.commands import web


class TestRegister:
    def test_register_adds_subparser_with_flags(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        web.register(sub)
        assert 'web' in sub.choices
        web_parser = sub.choices['web']
        flags = {a.dest for a in web_parser._actions}
        for expected in ('target', 'mode', 'port', 'host', 'no_browser'):
            assert expected in flags


class TestHandlerWithoutUiExtras:
    def test_returns_2_when_fastapi_missing(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            # Block the lazy uvicorn import that web does
            if name == 'uvicorn':
                raise ImportError('No module named uvicorn')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)

        ns = argparse.Namespace(target=None, mode='auto', port=None,
                                host='127.0.0.1', no_browser=True)
        rc = web._handler(ns)
        assert rc == 2
        err = capsys.readouterr().err
        assert '[ui] extras' in err


class TestHandlerHappyPath:
    def test_no_browser_runs_uvicorn_directly(
        self, monkeypatch: pytest.MonkeyPatch, project_root: Path,
        capsys: pytest.CaptureFixture,
    ):
        # Stub uvicorn.run so no actual server starts
        import uvicorn
        captured: dict = {}

        def fake_run(app, host, port, log_level):
            captured['ran'] = True
            captured['host'] = host
            captured['port'] = port

        monkeypatch.setattr(uvicorn, 'run', fake_run)

        # Stub config + create_app
        from ui import config as ui_config
        from ui import server as ui_server

        class _Cfg:
            mode = 'project'
            root = project_root
            metrics_dir = None
            port = 7700

        monkeypatch.setattr(ui_config, 'resolve', lambda **kw: _Cfg())
        monkeypatch.setattr(ui_server, 'create_app', lambda cfg: 'fake-app')

        ns = argparse.Namespace(target=str(project_root), mode='auto', port=None,
                                host='127.0.0.1', no_browser=True)
        rc = web._handler(ns)
        assert rc == 0
        assert captured == {'ran': True, 'host': '127.0.0.1', 'port': 7700}

    def test_invalid_config_returns_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        from ui import config as ui_config

        def boom(**kw):
            raise ValueError('bad config')

        monkeypatch.setattr(ui_config, 'resolve', boom)
        ns = argparse.Namespace(target=None, mode='auto', port=None,
                                host='127.0.0.1', no_browser=True)
        rc = web._handler(ns)
        assert rc == 2
        err = capsys.readouterr().err
        assert 'config error' in err


class TestWaitReady:
    def test_returns_false_when_endpoint_never_responds(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        import urllib.request

        def fake_open(url, timeout):
            raise OSError('refused')

        monkeypatch.setattr(urllib.request, 'urlopen', fake_open)
        # Tight deadline so the test runs fast
        assert web._wait_ready('http://127.0.0.1:9', timeout=0.05) is False

    def test_returns_true_when_endpoint_responds(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        import urllib.request

        class _Resp:
            def read(self):
                return b''

        monkeypatch.setattr(urllib.request, 'urlopen', lambda url, timeout: _Resp())
        assert web._wait_ready('http://127.0.0.1:9', timeout=0.5) is True
