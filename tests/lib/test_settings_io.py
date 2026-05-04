"""Tests for orquestrum/lib/settings_io.py — the central settings.json
I/O + CRUD helpers. Covers behaviors the original `_merge_claude_settings`
had implicitly so the extraction can't silently drift.

Areas:
  - load/write round-trip + missing/malformed file handling
  - is_valid_json distinguishing missing from corrupted
  - mcpServers add / remove preserving user entries
  - hook detection (current + legacy forms)
  - merge_template_settings end-to-end
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.lib import settings_io


# ─── load / write ──────────────────────────────────────────────────────────


class TestLoad:
    def test_missing_returns_empty_dict(self, tmp_path: Path):
        assert settings_io.load_claude_settings(tmp_path / 'no.json') == {}

    def test_malformed_returns_empty_dict(self, tmp_path: Path):
        p = tmp_path / 'bad.json'
        p.write_text('not json', encoding='utf-8')
        assert settings_io.load_claude_settings(p) == {}

    def test_round_trip_preserves_unknown_keys(self, tmp_path: Path):
        p = tmp_path / 'settings.json'
        original = {'theme': 'dark', 'custom': {'a': 1, 'b': [True, False]}}
        settings_io.write_claude_settings(p, original)
        assert settings_io.load_claude_settings(p) == original


class TestIsValidJson:
    def test_missing_is_false(self, tmp_path: Path):
        assert settings_io.is_valid_json(tmp_path / 'no.json') is False

    def test_malformed_is_false(self, tmp_path: Path):
        p = tmp_path / 'bad.json'
        p.write_text('not json', encoding='utf-8')
        assert settings_io.is_valid_json(p) is False

    def test_valid_is_true(self, tmp_path: Path):
        p = tmp_path / 'good.json'
        p.write_text('{"k": 1}', encoding='utf-8')
        assert settings_io.is_valid_json(p) is True


class TestWrite:
    def test_creates_parent_dirs(self, tmp_path: Path):
        nested = tmp_path / 'a' / 'b' / 'c.json'
        settings_io.write_claude_settings(nested, {'x': 1})
        assert nested.exists()
        assert json.loads(nested.read_text()) == {'x': 1}

    def test_pretty_with_trailing_newline(self, tmp_path: Path):
        p = tmp_path / 'p.json'
        settings_io.write_claude_settings(p, {'a': 1, 'b': 2})
        text = p.read_text(encoding='utf-8')
        assert text.endswith('\n')
        # indent=2 produces multi-line output for non-trivial objects
        assert '\n' in text


# ─── mcpServers CRUD ───────────────────────────────────────────────────────


class TestMcpCrud:
    def test_add_creates_first_entry(self):
        settings = {}
        added = settings_io.add_mcp_server(
            settings, 'fs', command='mcp-fs', args=['/tmp'],
        )
        assert added is True
        assert settings == {
            'mcpServers': {'fs': {'command': 'mcp-fs', 'args': ['/tmp'], 'type': 'stdio'}}
        }

    def test_add_replaces_existing_returns_false(self):
        settings = {'mcpServers': {'fs': {'command': 'old', 'type': 'stdio'}}}
        replaced = settings_io.add_mcp_server(
            settings, 'fs', command='new', args=['x'],
        )
        assert replaced is False
        assert settings['mcpServers']['fs']['command'] == 'new'
        assert settings['mcpServers']['fs']['args'] == ['x']

    def test_add_preserves_other_servers(self):
        settings = {
            'mcpServers': {
                'github': {'command': 'mcp-gh', 'type': 'stdio'},
            },
            'theme': 'dark',
        }
        settings_io.add_mcp_server(settings, 'fs', command='mcp-fs')
        assert 'github' in settings['mcpServers']
        assert settings['theme'] == 'dark'

    def test_add_with_extra_fields(self):
        settings = {}
        settings_io.add_mcp_server(
            settings, 'http-mcp', command='', server_type='http',
            extra={'url': 'http://localhost:9000'},
        )
        assert settings['mcpServers']['http-mcp'] == {
            'command': '', 'type': 'http', 'url': 'http://localhost:9000',
        }

    def test_remove_present_returns_true(self):
        settings = {
            'mcpServers': {
                'fs': {'command': 'mcp-fs', 'type': 'stdio'},
                'gh': {'command': 'mcp-gh', 'type': 'stdio'},
            }
        }
        removed = settings_io.remove_mcp_server(settings, 'fs')
        assert removed is True
        assert 'fs' not in settings['mcpServers']
        assert 'gh' in settings['mcpServers']

    def test_remove_missing_returns_false(self):
        settings = {'mcpServers': {'gh': {'command': 'x'}}}
        assert settings_io.remove_mcp_server(settings, 'fs') is False

    def test_remove_last_drops_mcp_servers_key(self):
        settings = {'mcpServers': {'only': {'command': 'x'}}, 'theme': 'dark'}
        settings_io.remove_mcp_server(settings, 'only')
        assert 'mcpServers' not in settings
        assert settings == {'theme': 'dark'}

    def test_list_returns_copy(self):
        settings = {'mcpServers': {'a': {'command': 'x'}}}
        listed = settings_io.list_mcp_servers(settings)
        listed['b'] = {'command': 'y'}  # mutate copy
        # Original untouched
        assert 'b' not in settings['mcpServers']

    def test_list_returns_empty_dict_when_absent(self):
        assert settings_io.list_mcp_servers({}) == {}


# ─── hook detection ────────────────────────────────────────────────────────


class TestIsOrquestrumHook:
    @pytest.mark.parametrize('cmd', [
        'orquestrum hook',
        '/usr/bin/orquestrum hook --foo',
        'uv run .claude/sdd/scripts/hooks/emit_metrics.py',
        'python /Users/x/.claude/sdd/scripts/hooks/emit_metrics.py',
        'sdd/scripts/hooks/emit_metrics.py extra',
    ])
    def test_recognised_forms(self, cmd: str):
        assert settings_io.is_orquestrum_hook(cmd) is True

    @pytest.mark.parametrize('cmd', [
        '',
        None,
        'echo user-hook',
        'my-tool --arg',
        'orquestrum mcp',  # different subcommand
    ])
    def test_unrecognised_forms(self, cmd):
        assert settings_io.is_orquestrum_hook(cmd) is False


class TestRemoveOrquestrumHooks:
    def test_removes_orq_keeps_user(self):
        settings = {
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'type': 'command', 'command': 'orquestrum hook'},
                    {'type': 'command', 'command': 'echo user'},
                ]}],
            }
        }
        removed = settings_io.remove_orquestrum_hooks(settings)
        assert removed == 1
        cmds = [h['command'] for blk in settings['hooks']['Stop'] for h in blk['hooks']]
        assert cmds == ['echo user']

    def test_removes_block_entirely_when_only_orq(self):
        settings = {
            'hooks': {
                'SubagentStop': [{'matcher': '', 'hooks': [
                    {'type': 'command', 'command': 'orquestrum hook'},
                ]}],
            }
        }
        settings_io.remove_orquestrum_hooks(settings)
        assert 'SubagentStop' not in settings.get('hooks', {})

    def test_drops_empty_hooks_key(self):
        settings = {
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'type': 'command', 'command': 'orquestrum hook'},
                ]}],
            },
            'theme': 'dark',
        }
        settings_io.remove_orquestrum_hooks(settings)
        assert 'hooks' not in settings
        assert settings == {'theme': 'dark'}

    def test_handles_legacy_emit_metrics(self):
        settings = {
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'command': 'uv run .claude/sdd/scripts/hooks/emit_metrics.py'},
                ]}],
            }
        }
        removed = settings_io.remove_orquestrum_hooks(settings)
        assert removed == 1


# ─── merge_template_settings ───────────────────────────────────────────────


class TestMergeTemplate:
    def _template(self) -> dict:
        return {
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'type': 'command', 'command': 'orquestrum hook'},
                ]}],
                'SubagentStop': [{'matcher': '', 'hooks': [
                    {'type': 'command', 'command': 'orquestrum hook'},
                ]}],
            },
            'mcpServers': {
                'orquestrum': {
                    'command': 'orquestrum', 'args': ['mcp'], 'type': 'stdio',
                },
            },
        }

    def test_merge_into_empty(self):
        target = {}
        removed, added, mcp_added, mcp_replaced = (
            settings_io.merge_template_settings(self._template(), target)
        )
        assert removed == 0
        assert len(added) == 2
        assert mcp_added == ['orquestrum']
        assert mcp_replaced == []
        # User-facing structure intact
        assert 'orquestrum' in target['mcpServers']
        assert 'Stop' in target['hooks']

    def test_merge_preserves_user_mcp_and_theme(self):
        target = {
            'theme': 'dark',
            'mcpServers': {
                'filesystem': {'command': 'mcp-fs', 'args': ['/'], 'type': 'stdio'},
                'github': {'command': 'mcp-gh', 'type': 'stdio'},
            },
        }
        settings_io.merge_template_settings(self._template(), target)
        assert target['theme'] == 'dark'
        assert 'filesystem' in target['mcpServers']
        assert 'github' in target['mcpServers']
        assert 'orquestrum' in target['mcpServers']

    def test_merge_replaces_outdated_orquestrum_mcp(self):
        target = {
            'mcpServers': {
                'orquestrum': {'command': 'old-cmd', 'args': ['legacy']},
            },
        }
        _, _, mcp_added, mcp_replaced = (
            settings_io.merge_template_settings(self._template(), target)
        )
        assert mcp_added == []
        assert mcp_replaced == ['orquestrum']
        assert target['mcpServers']['orquestrum']['command'] == 'orquestrum'
        assert target['mcpServers']['orquestrum']['args'] == ['mcp']

    def test_merge_strips_legacy_hook_then_adds_new(self):
        target = {
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'type': 'command',
                     'command': 'uv run .claude/sdd/scripts/hooks/emit_metrics.py'},
                    {'type': 'command', 'command': 'echo user'},
                ]}],
            }
        }
        removed, added, _, _ = (
            settings_io.merge_template_settings(self._template(), target)
        )
        assert removed == 1
        cmds = [h['command'] for blk in target['hooks']['Stop'] for h in blk['hooks']]
        # User hook preserved; legacy emit_metrics replaced by orquestrum hook
        assert 'echo user' in cmds
        assert 'orquestrum hook' in cmds
        assert all('emit_metrics.py' not in c for c in cmds)

    def test_no_template_mcp_means_no_mcp_keys_added(self):
        template = {'hooks': {'Stop': [{'matcher': '', 'hooks': [
            {'command': 'orquestrum hook'},
        ]}]}}
        target = {}
        _, _, mcp_added, mcp_replaced = (
            settings_io.merge_template_settings(template, target)
        )
        assert mcp_added == []
        assert mcp_replaced == []
        assert 'mcpServers' not in target
