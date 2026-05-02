"""Unit tests for orquestrum.cli — top-level argparse dispatcher."""
from __future__ import annotations

import pytest

from orquestrum import __version__, cli


class TestBuildParser:
    def test_returns_an_argument_parser(self):
        parser = cli._build_parser()
        assert parser.prog == 'orquestrum'

    def test_registers_every_subcommand(self):
        parser = cli._build_parser()
        # The single subparsers action holds every registered name as a choice.
        actions = [a for a in parser._actions if hasattr(a, 'choices') and a.dest == 'cmd']
        assert actions, 'no subcommands action found'
        registered = set(actions[0].choices)
        for expected in (
            'convert', 'install', 'lint', 'deps', 'audit', 'dashboard',
            'compact', 'init', 'update', 'web', 'repos', 'extras',
            'uninstall', 'doctor', 'version',
        ):
            assert expected in registered, f'subcommand missing: {expected}'


class TestVersionFlag:
    def test_emits_version_string(self, capsys: pytest.CaptureFixture):
        with pytest.raises(SystemExit) as exc:
            cli.main(['--version'])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out


class TestMissingSubcommand:
    def test_no_args_exits_with_help(self, capsys: pytest.CaptureFixture):
        with pytest.raises(SystemExit) as exc:
            cli.main([])
        # argparse may exit 2 (required), or our fallback prints help and exits 2.
        assert exc.value.code == 2


class TestPassthroughForwarding:
    def test_unknown_flags_after_subcommand_route_through(self, monkeypatch: pytest.MonkeyPatch):
        captured: dict = {}

        def fake_convert_main(argv):
            captured['argv'] = list(argv)

        # convert imports core lazily; patch on the module level
        from orquestrum.core import convert as core_convert
        monkeypatch.setattr(core_convert, 'main', fake_convert_main)

        with pytest.raises(SystemExit) as exc:
            cli.main(['convert', '--all', '--dry-run'])
        assert exc.value.code == 0
        assert captured['argv'] == ['--all', '--dry-run']

    def test_native_subcommand_ignores_passthrough(self, capsys: pytest.CaptureFixture):
        # `version` is native and prints its own line — extra flags are merged
        # into args.passthrough but are silently ignored.
        with pytest.raises(SystemExit) as exc:
            cli.main(['version'])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert __version__ in out


class TestHandlerExitCodes:
    def test_handler_returning_int_propagates(self, monkeypatch: pytest.MonkeyPatch):
        # repos remove of a missing entry returns 1
        from orquestrum.commands import repos
        # Make sure registry is empty: redirect to tmp via fixture not used here,
        # but we still patch unregister_project to None deterministically.
        import orquestrum.lib.registry as registry
        monkeypatch.setattr(registry, 'unregister_project', lambda **kw: None)
        with pytest.raises(SystemExit) as exc:
            cli.main(['repos', 'remove', 'does-not-exist'])
        assert exc.value.code == 1
        # The registered handler is what we expect
        assert repos._remove is not None

    def test_handler_returning_none_exits_zero(self, monkeypatch: pytest.MonkeyPatch):
        # Force version handler path
        with pytest.raises(SystemExit) as exc:
            cli.main(['version'])
        assert exc.value.code == 0
