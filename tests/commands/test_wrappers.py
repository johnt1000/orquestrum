"""Unit tests for the thin wrapper subcommands.

Each wrapper registers with the parent argparse and forwards args.passthrough
to the wrapped main(). We patch the wrapped target so we can assert routing
and exit code without invoking the real subsystem.
"""
from __future__ import annotations
import argparse

import pytest

from orquestrum.commands import (
    audit, compact, convert, dashboard, deps, install, lint, version,
)
from orquestrum.commands._passthrough import passthrough_handler


def _make_parent() -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    return parser, sub


class TestPassthroughHandler:
    def test_calls_wrapped_with_passthrough_list(self):
        seen: dict = {}

        def wrapped(argv):
            seen['argv'] = list(argv or [])
            return 0

        handler = passthrough_handler(wrapped)
        ns = argparse.Namespace(passthrough=['--foo', '--bar'])
        assert handler(ns) == 0
        assert seen['argv'] == ['--foo', '--bar']

    def test_calls_wrapped_with_empty_when_passthrough_missing(self):
        seen: dict = {}

        def wrapped(argv):
            seen['argv'] = list(argv or [])

        handler = passthrough_handler(wrapped)
        ns = argparse.Namespace()
        handler(ns)
        assert seen['argv'] == []


class TestConvertWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        convert.register(sub)
        assert 'convert' in sub.choices

    def test_handler_forwards_to_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core import convert as core_convert
        captured = {}
        monkeypatch.setattr(core_convert, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--all'])
        assert convert._handler(ns) == 0
        assert captured['argv'] == ['--all']


class TestInstallWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        install.register(sub)
        assert 'install' in sub.choices

    def test_handler_forwards_to_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core import install as core_install
        captured = {}
        monkeypatch.setattr(core_install, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--auto', '--target', '/tmp/x'])
        assert install._handler(ns) == 0
        assert captured['argv'] == ['--auto', '--target', '/tmp/x']


class TestLintWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        lint.register(sub)
        assert 'lint' in sub.choices

    def test_handler_calls_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core import lint as core_lint
        called = {'count': 0}
        monkeypatch.setattr(core_lint, 'main', lambda: called.__setitem__('count', called['count'] + 1))
        ns = argparse.Namespace(passthrough=[])
        assert lint._handler(ns) == 0
        assert called['count'] == 1


class TestDepsWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        deps.register(sub)
        assert 'deps' in sub.choices

    def test_handler_forwards_to_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core import deps as core_deps
        captured = {}
        monkeypatch.setattr(core_deps, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--target', '/tmp/y', '--only', 'agency'])
        assert deps._handler(ns) == 0
        assert captured['argv'] == ['--target', '/tmp/y', '--only', 'agency']


class TestDashboardWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        dashboard.register(sub)
        assert 'dashboard' in sub.choices

    def test_handler_forwards_to_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core.dashboard import render as render_mod
        captured = {}
        monkeypatch.setattr(render_mod, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--format', 'md'])
        assert dashboard._handler(ns) == 0
        assert captured['argv'] == ['--format', 'md']


class TestCompactWrapper:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        compact.register(sub)
        assert 'compact' in sub.choices

    def test_handler_forwards_to_core(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core.build import compress_refs as compress_mod
        captured = {}
        monkeypatch.setattr(compress_mod, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--dry-run'])
        assert compact._handler(ns) == 0
        assert captured['argv'] == ['--dry-run']


class TestAuditWrapper:
    def test_register_adds_audit_subparsers(self):
        parser, sub = _make_parent()
        audit.register(sub)
        assert 'audit' in sub.choices

    def test_payload_forwards(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core.audit import payload as payload_mod
        captured = {}
        monkeypatch.setattr(payload_mod, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--threshold', '20'])
        assert audit._payload(ns) == 0
        assert captured['argv'] == ['--threshold', '20']

    def test_parity_forwards_and_uses_return_value(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core.tests.parity import run as parity_run
        captured = {}

        def fake_main(argv):
            captured['argv'] = argv
            return 7  # non-zero rc to verify propagation

        monkeypatch.setattr(parity_run, 'main', fake_main)
        ns = argparse.Namespace(passthrough=['--provider', 'glm'])
        assert audit._parity(ns) == 7
        assert captured['argv'] == ['--provider', 'glm']

    def test_attention_forwards(self, monkeypatch: pytest.MonkeyPatch):
        from orquestrum.core.audit import attention_distribution as attn_mod
        captured = {}
        monkeypatch.setattr(attn_mod, 'main', lambda argv: captured.setdefault('argv', argv))
        ns = argparse.Namespace(passthrough=['--top', '5'])
        assert audit._attention(ns) == 0
        assert captured['argv'] == ['--top', '5']


class TestVersionCommand:
    def test_register_adds_subparser(self):
        parser, sub = _make_parent()
        version.register(sub)
        assert 'version' in sub.choices

    def test_handler_prints_version_and_python(self, capsys: pytest.CaptureFixture):
        from orquestrum import __version__
        ns = argparse.Namespace()
        assert version._handler(ns) == 0
        out = capsys.readouterr().out
        assert __version__ in out
        assert 'Python' in out
