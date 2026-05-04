"""Tests for `orquestrum mcp` — the MCP management hub.

Coverage:
  - argparse subcommand registration (run/list/tools/add/remove/validate)
  - backward compat: `orquestrum mcp` (no subcommand) defaults to run
  - list: empty + populated + missing settings.json
  - tools: introspection of orq_* via mcp.registry
  - add: first registration + replacement
  - remove: protection of `orquestrum`, --force escape hatch, missing entries
  - validate: PATH lookup + binary spawn + timeout = healthy
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

import pytest

from orquestrum.commands import mcp as mcp_cmd
from orquestrum.lib import settings_io


# ─── argparse registration ─────────────────────────────────────────────────


class TestRegister:
    def test_register_creates_subparsers(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        mcp_cmd.register(sub)
        assert 'mcp' in sub.choices
        # The mcp parser itself has subcommands
        mcp_p = sub.choices['mcp']
        # Walk to find the SubParsersAction we attached
        sub_actions = [a for a in mcp_p._actions
                       if isinstance(a, argparse._SubParsersAction)]
        assert len(sub_actions) == 1
        names = set(sub_actions[0].choices)
        assert names == {'run', 'list', 'tools', 'add', 'remove', 'validate'}


class TestBackwardCompat:
    def test_no_subcommand_defaults_to_run(self, monkeypatch: pytest.MonkeyPatch):
        """settings.json in the wild is `{"command": "orquestrum", "args": ["mcp"]}` —
        bare `mcp` must keep launching the server."""
        called: list[bool] = []
        # Stub the FastMCP server entry point so we don't actually launch it
        from orquestrum.mcp import server as srv
        monkeypatch.setattr(srv, 'main', lambda: called.append(True))

        # Simulate dispatch: build the parser, parse just `mcp`, call handler
        from orquestrum import cli
        parser = cli._build_parser()
        args, _ = parser.parse_known_args(['mcp'])
        args.handler(args)
        assert called == [True]


# ─── list ──────────────────────────────────────────────────────────────────


class TestList:
    def test_missing_settings_returns_1(self, tmp_path: Path,
                                         capsys: pytest.CaptureFixture):
        rc = mcp_cmd._list(argparse.Namespace(target=str(tmp_path)))
        assert rc == 1
        err = capsys.readouterr().err
        assert 'No settings.json' in err

    def test_empty_servers(self, tmp_path: Path,
                            capsys: pytest.CaptureFixture):
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'theme': 'dark'}), encoding='utf-8')
        rc = mcp_cmd._list(argparse.Namespace(target=str(tmp_path)))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No MCP servers' in out

    def test_lists_servers_with_owner_column(self, tmp_path: Path,
                                              capsys: pytest.CaptureFixture):
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({
            'mcpServers': {
                'orquestrum': {'command': 'orquestrum', 'args': ['mcp'], 'type': 'stdio'},
                'filesystem': {'command': 'mcp-fs', 'args': ['/tmp'], 'type': 'stdio'},
            }
        }), encoding='utf-8')
        rc = mcp_cmd._list(argparse.Namespace(target=str(tmp_path)))
        assert rc == 0
        out = capsys.readouterr().out
        assert 'orquestrum' in out
        assert 'filesystem' in out
        # owner column distinguishes them
        assert out.count('orquestrum') >= 1
        assert 'user' in out
        assert '2 server(s) registered' in out


# ─── tools (introspection) ─────────────────────────────────────────────────


class TestTools:
    def test_tools_lists_all_orq_tools(self, capsys: pytest.CaptureFixture):
        rc = mcp_cmd._tools(argparse.Namespace())
        assert rc == 0
        out = capsys.readouterr().out
        # Must include both read and write tools
        assert 'orq_session_summary' in out
        assert 'orq_record_event' in out
        # Resources too
        assert 'orq://projects' in out
        # Mode separation
        assert 'Read-only' in out
        assert 'Write' in out


# ─── add ───────────────────────────────────────────────────────────────────


class TestAdd:
    def test_add_creates_first_entry_and_settings_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        ns = argparse.Namespace(
            name='filesystem',
            command='npx',
            args=['-y', '@modelcontextprotocol/server-filesystem', '/tmp'],
            server_type='stdio',
            target=str(tmp_path),
        )
        rc = mcp_cmd._add(ns)
        assert rc == 0
        path = tmp_path / '.claude' / 'settings.json'
        assert path.exists()
        data = json.loads(path.read_text())
        assert data['mcpServers']['filesystem']['command'] == 'npx'
        assert data['mcpServers']['filesystem']['type'] == 'stdio'
        assert 'registered' in capsys.readouterr().out

    def test_add_replaces_existing(self, tmp_path: Path,
                                    capsys: pytest.CaptureFixture):
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({
            'mcpServers': {
                'fs': {'command': 'old', 'type': 'stdio'},
            }
        }), encoding='utf-8')
        ns = argparse.Namespace(
            name='fs', command='new', args=None,
            server_type='stdio', target=str(tmp_path),
        )
        rc = mcp_cmd._add(ns)
        assert rc == 0
        data = json.loads(path.read_text())
        assert data['mcpServers']['fs']['command'] == 'new'
        assert 'updated' in capsys.readouterr().out

    def test_add_preserves_other_servers(self, tmp_path: Path):
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({
            'mcpServers': {
                'github': {'command': 'mcp-gh', 'type': 'stdio'},
            },
            'theme': 'dark',
        }), encoding='utf-8')
        ns = argparse.Namespace(
            name='fs', command='mcp-fs', args=['/'], server_type='stdio',
            target=str(tmp_path),
        )
        mcp_cmd._add(ns)
        data = json.loads(path.read_text())
        assert 'github' in data['mcpServers']
        assert 'fs' in data['mcpServers']
        assert data['theme'] == 'dark'


# ─── remove ────────────────────────────────────────────────────────────────


class TestRemove:
    def _seed(self, tmp_path: Path) -> Path:
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({
            'mcpServers': {
                'orquestrum': {'command': 'orquestrum', 'args': ['mcp']},
                'filesystem': {'command': 'mcp-fs'},
            }
        }), encoding='utf-8')
        return path

    def test_remove_user_entry(self, tmp_path: Path,
                                 capsys: pytest.CaptureFixture):
        path = self._seed(tmp_path)
        ns = argparse.Namespace(name='filesystem', force=False,
                                target=str(tmp_path))
        rc = mcp_cmd._remove(ns)
        assert rc == 0
        data = json.loads(path.read_text())
        assert 'filesystem' not in data['mcpServers']
        assert 'orquestrum' in data['mcpServers']

    def test_remove_orquestrum_refused_without_force(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        path = self._seed(tmp_path)
        ns = argparse.Namespace(name='orquestrum', force=False,
                                target=str(tmp_path))
        rc = mcp_cmd._remove(ns)
        assert rc == 2
        err = capsys.readouterr().err
        assert '--force' in err
        # File untouched
        data = json.loads(path.read_text())
        assert 'orquestrum' in data['mcpServers']

    def test_remove_orquestrum_with_force(self, tmp_path: Path):
        path = self._seed(tmp_path)
        ns = argparse.Namespace(name='orquestrum', force=True,
                                target=str(tmp_path))
        rc = mcp_cmd._remove(ns)
        assert rc == 0
        data = json.loads(path.read_text())
        assert 'orquestrum' not in data.get('mcpServers', {})

    def test_remove_missing_returns_1(self, tmp_path: Path,
                                       capsys: pytest.CaptureFixture):
        self._seed(tmp_path)
        ns = argparse.Namespace(name='nope', force=False,
                                target=str(tmp_path))
        rc = mcp_cmd._remove(ns)
        assert rc == 1
        err = capsys.readouterr().err
        assert "no MCP server named" in err


# ─── validate ──────────────────────────────────────────────────────────────


class TestValidate:
    def _seed(self, tmp_path: Path, servers: dict) -> Path:
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'mcpServers': servers}), encoding='utf-8')
        return path

    def test_missing_settings_returns_1(self, tmp_path: Path):
        ns = argparse.Namespace(target=str(tmp_path), timeout=2.0)
        assert mcp_cmd._validate(ns) == 1

    def test_no_servers_is_ok(self, tmp_path: Path,
                               capsys: pytest.CaptureFixture):
        self._seed(tmp_path, {})
        ns = argparse.Namespace(target=str(tmp_path), timeout=2.0)
        rc = mcp_cmd._validate(ns)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No MCP servers' in out

    def test_path_lookup_failure_marks_failed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        self._seed(tmp_path, {
            'made-up': {'command': 'definitely-not-on-path-xyz', 'type': 'stdio'},
        })
        ns = argparse.Namespace(target=str(tmp_path), timeout=2.0)
        rc = mcp_cmd._validate(ns)
        assert rc == 1
        out = capsys.readouterr().out
        assert '✗' in out
        assert 'made-up' in out

    def test_resolvable_command_passes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Use a real OS command (`echo`) that's guaranteed on PATH."""
        self._seed(tmp_path, {
            'echo-test': {'command': 'echo', 'args': ['hi'], 'type': 'stdio'},
        })
        ns = argparse.Namespace(target=str(tmp_path), timeout=2.0)
        rc = mcp_cmd._validate(ns)
        # echo --help may exit 0 or 1 depending on platform; either way
        # the binary resolved → counted as passing
        assert rc == 0
        out = capsys.readouterr().out
        assert '✓' in out
        assert 'echo-test' in out
