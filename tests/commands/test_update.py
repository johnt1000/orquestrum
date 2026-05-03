"""End-user/developer update flow: `orquestrum update`."""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

import pytest

from orquestrum.commands import update as update_cmd
from orquestrum.commands import update_impl
from orquestrum.lib import registry, manifest


@pytest.fixture()
def stub_install_tool(monkeypatch: pytest.MonkeyPatch):
    """Patch the heavy install path so update_one runs deterministically."""
    calls: list = []
    monkeypatch.setattr(update_impl, '_install_tool',
                        lambda root, tool, provider: calls.append((str(root), tool, provider)) or True)
    return calls


@pytest.fixture()
def project_with_tool(initialized_project: Path) -> Path:
    """Same as initialized_project but with a tool=claude-code in config.toml."""
    cfg = initialized_project / '.orquestrum' / 'config.toml'
    cfg.write_text(
        '[project]\nname = "sample"\ntool = "claude-code"\nprovider = "claude"\n',
        encoding='utf-8',
    )
    return initialized_project


class TestReadProjectConfig:
    def test_returns_empty_dict_when_missing(self, project_root: Path):
        assert update_impl._read_project_config(project_root) == {}

    def test_returns_parsed_dict(self, project_with_tool: Path):
        data = update_impl._read_project_config(project_with_tool)
        assert data['project']['tool'] == 'claude-code'

    def test_returns_empty_on_invalid_toml(self, project_root: Path):
        (project_root / '.orquestrum').mkdir(exist_ok=True)
        (project_root / '.orquestrum' / 'config.toml').write_text('not = valid = toml=', encoding='utf-8')
        assert update_impl._read_project_config(project_root) == {}


class TestProjectTool:
    def test_returns_tool_and_provider(self, project_with_tool: Path):
        tool, provider = update_impl._project_tool(project_with_tool)
        assert tool == 'claude-code'
        assert provider == 'claude'

    def test_returns_none_when_unconfigured(self, initialized_project: Path):
        tool, provider = update_impl._project_tool(initialized_project)
        assert tool is None and provider is None


class TestOrquestrumAgentFilenames:
    def test_returns_eight_kebab_filenames(self):
        names = update_impl._orquestrum_agent_filenames()
        assert len(names) == 8
        assert all(n.endswith('.md') for n in names)
        assert all(n.islower() for n in names)


class TestUpdateOneCheckMode:
    def test_uninitialized_returns_false(self, project_root: Path):
        ok, msg = update_impl._update_one(project_root, new_tool=None, check=True)
        assert ok is False
        assert 'not initialized' in msg

    def test_check_mode_describes_switch(self, project_with_tool: Path):
        ok, msg = update_impl._update_one(project_with_tool, new_tool='opencode', check=True)
        assert ok is True
        assert "'claude-code'" in msg and "'opencode'" in msg

    def test_check_mode_describes_reinstall(self, project_with_tool: Path):
        ok, msg = update_impl._update_one(project_with_tool, new_tool=None, check=True)
        assert ok is True
        assert 're-install' in msg

    def test_check_mode_no_tool_does_nothing(self, initialized_project: Path):
        ok, msg = update_impl._update_one(initialized_project, new_tool=None, check=True)
        assert ok is True
        assert 'no tool configured' in msg


class TestUpdateOneApply:
    def test_no_tool_configured_returns_error(self, initialized_project: Path):
        ok, msg = update_impl._update_one(initialized_project, new_tool=None, check=False)
        assert ok is False
        assert 'no tool configured' in msg

    def test_reinstall_same_tool_succeeds(
        self, project_with_tool: Path, isolated_home: Path, stub_install_tool,
    ):
        ok, msg = update_impl._update_one(project_with_tool, new_tool=None, check=False)
        assert ok is True
        assert 're-installed' in msg
        assert stub_install_tool, 'install_tool should have been called'

    def test_tool_switch_writes_history(
        self, project_with_tool: Path, isolated_home: Path, stub_install_tool,
    ):
        ok, msg = update_impl._update_one(project_with_tool, new_tool='opencode', check=False)
        assert ok is True
        state = manifest.read_manifest_state(project_with_tool)
        assert state is not None
        assert any('switched' in entry for entry in state.history)

    def test_tool_switch_updates_config_toml(
        self, project_with_tool: Path, isolated_home: Path, stub_install_tool,
    ):
        update_impl._update_one(project_with_tool, new_tool='cursor', check=False)
        text = (project_with_tool / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert 'tool      = "cursor"' in text


class TestRunUpdate:
    def test_outside_project_returns_1(
        self, project_root: Path, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        rc = update_impl.run_update(tool=None, all_=False, check=False, self_update=False)
        assert rc == 1
        err = capsys.readouterr().err
        assert 'not in an Orquestrum project' in err

    def test_check_in_current_project(
        self, project_with_tool: Path, isolated_home: Path,
        capsys: pytest.CaptureFixture,
    ):
        rc = update_impl.run_update(tool=None, all_=False, check=True, self_update=False)
        assert rc == 0
        out = capsys.readouterr().out
        assert 're-install' in out

    def test_all_with_no_projects_short_circuits(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        rc = update_impl.run_update(tool=None, all_=True, check=False, self_update=False)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No projects registered' in out

    def test_all_iterates_projects(
        self, project_with_tool: Path, isolated_home: Path,
        stub_install_tool, capsys: pytest.CaptureFixture,
    ):
        registry.register_project(name='sample', path=project_with_tool,
                                  tool='claude-code', provider='claude')
        rc = update_impl.run_update(tool=None, all_=False, check=False, self_update=False)
        assert rc == 0
        out = capsys.readouterr().out
        assert 're-installed' in out

    def test_self_update_routes(self, monkeypatch: pytest.MonkeyPatch):
        called = {'count': 0}
        monkeypatch.setattr(update_impl, '_run_self_upgrade',
                            lambda: called.__setitem__('count', called['count'] + 1) or 0)
        rc = update_impl.run_update(tool=None, all_=False, check=False, self_update=True)
        assert rc == 0
        assert called['count'] == 1


class TestSelfUpgrade:
    def test_unknown_mode_prints_help(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        monkeypatch.setattr(update_impl, '_detect_install_mode', lambda: 'unknown')
        rc = update_impl._run_self_upgrade()
        assert rc == 0
        out = capsys.readouterr().out
        assert 'uv tool upgrade orquestrum' in out

    def test_uv_tool_runs_upgrade_command(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(update_impl, '_detect_install_mode', lambda: 'uv-tool')
        captured: dict = {}

        def fake_run(cmd, **kw):
            captured['cmd'] = cmd
            class _Ret:
                returncode = 0
            return _Ret()

        monkeypatch.setattr(subprocess, 'run', fake_run)
        rc = update_impl._run_self_upgrade()
        assert rc == 0
        assert captured['cmd'] == ['uv', 'tool', 'upgrade', 'orquestrum']


class TestScrubClaudeSettingsHooks:
    def test_removes_orquestrum_hooks_only(self, tmp_path: Path):
        import json
        settings = tmp_path / 'settings.json'
        settings.write_text(json.dumps({
            'theme': 'dark',
            'hooks': {
                'Stop': [
                    {'matcher': '', 'hooks': [
                        {'type': 'command', 'command': 'uv run .sdd/scripts/hooks/emit_metrics.py'},
                        {'type': 'command', 'command': 'echo user-hook'},
                    ]},
                ],
                'SubagentStop': [
                    {'matcher': '', 'hooks': [
                        {'type': 'command', 'command': 'uv run .sdd/scripts/hooks/emit_metrics.py'},
                    ]},
                ],
            },
        }), encoding='utf-8')

        update_impl._scrub_claude_settings_hooks(settings)
        out = json.loads(settings.read_text(encoding='utf-8'))
        # User keys preserved
        assert out['theme'] == 'dark'
        # SubagentStop block removed entirely (only orquestrum hook lived there)
        assert 'SubagentStop' not in out.get('hooks', {})
        # Stop block kept the user hook
        stop_cmds = [h['command']
                     for blk in out['hooks']['Stop']
                     for h in blk['hooks']]
        assert 'echo user-hook' in stop_cmds
        assert all('emit_metrics.py' not in c for c in stop_cmds)

    def test_handles_invalid_json_gracefully(self, tmp_path: Path):
        settings = tmp_path / 'settings.json'
        settings.write_text('not json', encoding='utf-8')
        # Should not raise
        update_impl._scrub_claude_settings_hooks(settings)


class TestCleanupOldTool:
    def test_claude_code_removes_agent_files_and_sdd(self, project_root: Path):
        # Set up a claude-code installation
        agents = project_root / '.claude' / 'agents'
        agents.mkdir(parents=True)
        for name in update_impl._orquestrum_agent_filenames():
            (agents / name).write_text('---\nname: x\n---', encoding='utf-8')
        # User-owned file should NOT be removed
        (agents / 'user-agent.md').write_text('---\nname: user\n---', encoding='utf-8')
        sdd = project_root / '.sdd' / 'docs'
        sdd.mkdir(parents=True)
        (sdd / 'SDLC.md').write_text('# SDLC', encoding='utf-8')

        removed = update_impl._cleanup_old_tool(project_root, 'claude-code')

        # Orquestrum agents removed; user agent preserved
        for name in update_impl._orquestrum_agent_filenames():
            assert not (agents / name).exists()
        assert (agents / 'user-agent.md').exists()
        # .sdd/ entirely gone
        assert not (project_root / '.sdd').is_dir()
        assert any('.sdd' in r for r in removed)

    def test_opencode_removes_agents_and_docs(self, project_root: Path):
        agents = project_root / '.opencode' / 'agents'
        agents.mkdir(parents=True)
        for name in update_impl._orquestrum_agent_filenames():
            (agents / name).write_text('---\nname: x\n---', encoding='utf-8')
        (project_root / '.opencode' / 'docs').mkdir(parents=True)
        (project_root / '.opencode' / 'docs' / 'X.md').write_text('x', encoding='utf-8')

        removed = update_impl._cleanup_old_tool(project_root, 'opencode')
        for name in update_impl._orquestrum_agent_filenames():
            assert not (agents / name).exists()
        assert not (project_root / '.opencode' / 'docs').is_dir()
        assert removed

    def test_cursor_removes_rules_dir(self, project_root: Path):
        rules = project_root / '.cursor' / 'rules'
        rules.mkdir(parents=True)
        (rules / 'sdlc.mdc').write_text('rules', encoding='utf-8')
        removed = update_impl._cleanup_old_tool(project_root, 'cursor')
        assert not rules.is_dir()
        assert removed

    def test_aider_removes_conventions(self, project_root: Path):
        (project_root / 'CONVENTIONS.md').write_text('# c', encoding='utf-8')
        removed = update_impl._cleanup_old_tool(project_root, 'aider')
        assert not (project_root / 'CONVENTIONS.md').exists()
        assert removed == ['CONVENTIONS.md']

    def test_windsurf_removes_windsurfrules(self, project_root: Path):
        (project_root / '.windsurfrules').write_text('rules', encoding='utf-8')
        removed = update_impl._cleanup_old_tool(project_root, 'windsurf')
        assert not (project_root / '.windsurfrules').exists()
        assert removed == ['.windsurfrules']

    def test_unknown_tool_returns_empty_list(self, project_root: Path):
        assert update_impl._cleanup_old_tool(project_root, 'made-up') == []


class TestCleanupOldToolWithManifest:
    """When an install manifest exists, cleanup must use it as source of
    truth — never blanket-rmtree shared directories that could contain
    user content."""

    def test_manifest_path_preserves_user_files_in_sdd(
        self, project_root: Path, isolated_home: Path,
    ):
        from orquestrum.lib import installs_manifest

        # Simulate a real install state: orquestrum's files + user file
        # placed inside .sdd/ (e.g. user added their own notes).
        sdd = project_root / '.sdd'
        sdd.mkdir(parents=True)
        (sdd / 'docs').mkdir()
        orq_doc = sdd / 'docs' / 'SDLC.md'
        orq_doc.write_text('# orquestrum SDLC', encoding='utf-8')

        agents = project_root / '.claude' / 'agents'
        agents.mkdir(parents=True)
        orq_agent = agents / 'helm-the-architect.md'
        orq_agent.write_text('---\nname: x\n---', encoding='utf-8')

        # User dropped a personal file inside orquestrum's .sdd/
        user_note = sdd / 'my-personal-notes.md'
        user_note.write_text('private notes', encoding='utf-8')

        # Manifest records ONLY orquestrum's files
        installs_manifest.record_install(
            'claude-code', project_root,
            files=[orq_doc, orq_agent],
            directories=[
                project_root / '.claude' / 'agents',
                project_root / '.claude',
                project_root / '.sdd' / 'docs',
                project_root / '.sdd',
            ],
        )

        update_impl._cleanup_old_tool(project_root, 'claude-code')

        # Orquestrum files gone
        assert not orq_doc.exists()
        assert not orq_agent.exists()
        # User file PRESERVED
        assert user_note.is_file()
        # .sdd/ NOT removed (still has user content)
        assert sdd.is_dir()
        # Manifest entry cleaned up
        assert installs_manifest.get_install('claude-code', project_root) is None

    def test_manifest_path_removes_dirs_when_orquestrum_only(
        self, project_root: Path, isolated_home: Path,
    ):
        from orquestrum.lib import installs_manifest

        rules = project_root / '.cursor' / 'rules'
        rules.mkdir(parents=True)
        f1 = rules / 'helm.mdc'
        f1.write_text('rules', encoding='utf-8')
        installs_manifest.record_install(
            'cursor', project_root,
            files=[f1],
            directories=[rules, project_root / '.cursor'],
        )

        update_impl._cleanup_old_tool(project_root, 'cursor')

        # All gone — directories were orquestrum-only
        assert not f1.exists()
        assert not rules.exists()
        assert not (project_root / '.cursor').exists()

    def test_falls_back_to_heuristic_without_manifest(
        self, project_root: Path, isolated_home: Path,
    ):
        """Pre-manifest installs still cleanup correctly via legacy heuristic."""
        agents = project_root / '.claude' / 'agents'
        agents.mkdir(parents=True)
        for name in update_impl._orquestrum_agent_filenames():
            (agents / name).write_text('---\nname: x\n---', encoding='utf-8')
        sdd = project_root / '.sdd' / 'docs'
        sdd.mkdir(parents=True)
        (sdd / 'X.md').write_text('x', encoding='utf-8')

        # No manifest record → falls back to heuristic (blanket rmtree of .sdd)
        update_impl._cleanup_old_tool(project_root, 'claude-code')
        for name in update_impl._orquestrum_agent_filenames():
            assert not (agents / name).exists()
        assert not (project_root / '.sdd').exists()


class TestDetectInstallMode:
    def test_returns_source_when_canonical_repo_has_git(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        canonical = tmp_path / 'repo'
        (canonical / '.git').mkdir(parents=True)
        monkeypatch.setattr('orquestrum.lib.paths.canonical_root', lambda: canonical)
        assert update_impl._detect_install_mode() == 'source'

    def test_returns_uv_tool_when_exe_under_uv_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        # No source repo
        monkeypatch.setattr('orquestrum.lib.paths.canonical_root', lambda: None)
        fake_home = tmp_path / 'home'
        exe = fake_home / '.local' / 'share' / 'uv' / 'tools' / 'orquestrum' / 'bin' / 'orquestrum'
        exe.parent.mkdir(parents=True)
        exe.write_text('#!/bin/sh\n', encoding='utf-8')
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        import shutil
        monkeypatch.setattr(shutil, 'which', lambda name: str(exe))
        assert update_impl._detect_install_mode() == 'uv-tool'

    def test_returns_unknown_when_neither(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.setattr('orquestrum.lib.paths.canonical_root', lambda: None)
        fake_home = tmp_path / 'home'
        fake_home.mkdir()
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        import shutil
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        assert update_impl._detect_install_mode() == 'unknown'


class TestInstallTool:
    def test_runs_convert_when_cache_missing(
        self, project_root: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Empty cache → convert must run before install.
        empty_cache = tmp_path / 'empty-cache'
        empty_cache.mkdir()
        monkeypatch.setattr('orquestrum.lib.paths.convert_output_root',
                            lambda: empty_cache)
        from orquestrum.core import convert as core_convert
        from orquestrum.core import install as core_install
        convert_calls: list = []
        install_calls: list = []
        monkeypatch.setattr(core_convert, 'main', lambda argv: convert_calls.append(argv))
        monkeypatch.setattr(core_install, 'main', lambda argv: install_calls.append(argv))
        ok = update_impl._install_tool(project_root, 'cursor', 'claude')
        assert ok is True
        assert convert_calls == [['--tool', 'cursor', '--provider', 'claude']]
        assert install_calls and install_calls[0][:2] == ['--tool', 'cursor']

    def test_skips_convert_when_cache_already_populated(
        self, project_root: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        cache = tmp_path / 'cache'
        (cache / 'cursor').mkdir(parents=True)
        monkeypatch.setattr('orquestrum.lib.paths.convert_output_root',
                            lambda: cache)
        from orquestrum.core import convert as core_convert
        from orquestrum.core import install as core_install
        convert_calls: list = []
        install_calls: list = []
        monkeypatch.setattr(core_convert, 'main', lambda argv: convert_calls.append(argv))
        monkeypatch.setattr(core_install, 'main', lambda argv: install_calls.append(argv))
        update_impl._install_tool(project_root, 'cursor', None)
        assert convert_calls == []
        assert install_calls


class TestUpdateAllIntegration:
    def test_iterates_and_summarizes_results(
        self, isolated_home: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.lib import registry

        # Create two registered projects, one valid, one ghost
        valid = tmp_path / 'valid'
        (valid / '.orquestrum').mkdir(parents=True)
        (valid / '.orquestrum' / 'config.toml').write_text(
            '[project]\nname = "valid"\ntool = "claude-code"\n', encoding='utf-8',
        )
        registry.register_project(name='valid', path=valid, tool='claude-code')

        ghost = tmp_path / 'ghost'
        ghost.mkdir()
        registry.register_project(name='ghost', path=ghost)
        ghost.rmdir()

        # Stub install_tool so we don't hit the canonical repo
        monkeypatch.setattr(update_impl, '_install_tool',
                            lambda root, tool, provider: True)

        rc = update_impl.run_update(tool=None, all_=False, check=False, self_update=False) \
            if False else update_impl.run_update(tool=None, all_=True, check=False, self_update=False)
        # 1 success + 1 skipped = exit 0
        assert rc == 0
        out = capsys.readouterr().out
        assert 'succeeded' in out
        assert 'skipped' in out


class TestSetProjectTool:
    def test_replaces_existing_tool_line(self, project_root: Path):
        (project_root / '.orquestrum').mkdir()
        cfg = project_root / '.orquestrum' / 'config.toml'
        cfg.write_text('[project]\nname = "x"\ntool = "claude-code"\n', encoding='utf-8')
        update_impl._set_project_tool(project_root, 'opencode', None)
        text = cfg.read_text(encoding='utf-8')
        assert 'opencode' in text and 'claude-code' not in text

    def test_inserts_when_missing(self, project_root: Path):
        (project_root / '.orquestrum').mkdir()
        cfg = project_root / '.orquestrum' / 'config.toml'
        cfg.write_text('[project]\nname = "x"\n', encoding='utf-8')
        update_impl._set_project_tool(project_root, 'cursor', None)
        text = cfg.read_text(encoding='utf-8')
        assert 'cursor' in text

    def test_no_config_is_noop(self, project_root: Path):
        # Should not raise
        update_impl._set_project_tool(project_root, 'cursor', None)


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        update_cmd.register(sub)
        assert 'update' in sub.choices

    def test_handler_dispatches_to_run_update(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict = {}
        monkeypatch.setattr(update_impl, 'run_update',
                            lambda **kw: captured.update(kw) or 0)
        ns = argparse.Namespace(tool='claude-code', all=True, check=True, self_update=False)
        rc = update_cmd._handler(ns)
        assert rc == 0
        assert captured == {'tool': 'claude-code', 'all_': True, 'check': True, 'self_update': False}
