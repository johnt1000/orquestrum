"""End-user installation flow: `orquestrum init` (v0.5).

The new init bootstraps `<project>/.orquestrum/` and asks 3 prompts about
optional integrations. Tests use `interactive=False` so the prompt
helpers return their defaults silently — equivalent to `init --yes`.

Optional installs (metrics hook, MCP, agents) are stubbed at the
boundary (`_install_metrics_hook`, `_install_agents_global`) so the heavy
convert/install paths don't have to run during init unit tests — they're
covered separately in tests/core/test_install.py.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pytest

from orquestrum.commands import init as init_cmd
from orquestrum.commands import init_impl
from orquestrum.lib import registry, manifest


@pytest.fixture()
def stub_optional_installs(monkeypatch: pytest.MonkeyPatch):
    """Replace the heavy install paths so init unit tests stay fast and
    don't depend on a populated cache. Returns a dict of call lists."""
    calls = {'metrics': [], 'agents': []}
    monkeypatch.setattr(init_impl, '_install_metrics_hook',
                        lambda root, scope: calls['metrics'].append((str(root), scope)))
    monkeypatch.setattr(init_impl, '_install_agents_global',
                        lambda root: calls['agents'].append(str(root)))
    return calls


# ─── Bootstrap (always-runs) ────────────────────────────────────────────────


class TestBootstrap:
    def test_creates_orquestrum_dir_and_files(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        rc = init_impl.run_init(name=None, interactive=False)
        assert rc == 0
        assert (project_root / '.orquestrum' / 'config.toml').is_file()
        assert (project_root / '.orquestrum' / '.gitignore').is_file()
        assert (project_root / '.orquestrum' / 'metrics').is_dir()
        # Manifest is now under .orquestrum/, NOT at the project root
        assert (project_root / '.orquestrum' / 'manifest.md').is_file()
        assert not (project_root / 'ORQUESTRUM.md').exists()

    def test_uses_directory_name_when_no_name_given(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert f'name      = "{project_root.name}"' in text

    def test_explicit_name_overrides_dirname(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name='custom', interactive=False)
        text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert 'name      = "custom"' in text

    def test_registers_in_global_registry(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name='alpha', interactive=False)
        entry = registry.find_by_name('alpha')
        assert entry is not None
        assert entry['path'] == str(project_root.resolve())

    def test_writes_manifest_with_history_entry(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        state = manifest.read_manifest_state(project_root)
        assert state is not None
        assert any('initialized' in entry for entry in state.history)

    def test_gitignore_blocks_metrics_and_integrations(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        gi = (project_root / '.orquestrum' / '.gitignore').read_text(encoding='utf-8')
        for blocked in ('metrics/', 'integrations/', 'services/', 'plugins/',
                        'events.jsonl', 'session.json'):
            assert blocked in gi


# ─── Default choices (interactive=False == --yes) ──────────────────────────


class TestDefaultChoices:
    def test_metrics_default_global_enabled(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        assert stub_optional_installs['metrics'] == [(str(project_root), 'global')]

    def test_agents_default_not_installed(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        assert stub_optional_installs['agents'] == []

    def test_config_records_default_choices(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert 'enabled = true' in text   # metrics + mcp on by default
        assert 'installed = false' in text  # agents off by default
        assert 'scope   = "global"' in text


# ─── Re-init ───────────────────────────────────────────────────────────────


class TestReinit:
    def test_emits_reinit_message(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
        capsys: pytest.CaptureFixture,
    ):
        init_impl.run_init(name=None, interactive=False)
        capsys.readouterr()  # discard
        init_impl.run_init(name=None, interactive=False)
        out = capsys.readouterr().out
        assert 'Re-initializing' in out

    def test_appends_history_on_reinit(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        init_impl.run_init(name=None, interactive=False)
        init_impl.run_init(name=None, interactive=False)
        state = manifest.read_manifest_state(project_root)
        assert state is not None
        assert any('re-initialized' in entry for entry in state.history)


# ─── Legacy ORQUESTRUM.md migration ────────────────────────────────────────


class TestLegacyMigration:
    def test_migrates_legacy_orquestrum_md_at_root(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
        capsys: pytest.CaptureFixture,
    ):
        # Pre-create a legacy ORQUESTRUM.md (≤v0.4 location)
        legacy_content = (
            '# Orquestrum — Project Manifest\n\n'
            '## Configuration\n\n'
            '| Field | Value |\n|-------|-------|\n'
            '| Project name | `legacy-name` |\n'
            '\n## Notes\n\nuser stuff\n'
        )
        (project_root / 'ORQUESTRUM.md').write_text(legacy_content, encoding='utf-8')

        init_impl.run_init(name=None, interactive=False)

        # Legacy file gone
        assert not (project_root / 'ORQUESTRUM.md').exists()
        # New file has content (migrated, then updated by re-render)
        new_path = project_root / '.orquestrum' / 'manifest.md'
        assert new_path.is_file()
        # Migration message printed
        out = capsys.readouterr().out
        assert 'Migrated legacy ORQUESTRUM.md' in out

    def test_does_nothing_when_no_legacy_file(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
        capsys: pytest.CaptureFixture,
    ):
        init_impl.run_init(name=None, interactive=False)
        out = capsys.readouterr().out
        assert 'Migrated legacy' not in out


# ─── CLI handler dispatch ──────────────────────────────────────────────────


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        init_cmd.register(sub)
        assert 'init' in sub.choices

    def test_handler_dispatches_to_run_init(
        self, project_root: Path, isolated_home: Path, stub_optional_installs,
    ):
        ns = argparse.Namespace(name='dispatch-test', non_interactive=True,
                                tool=None, provider=None)
        rc = init_cmd._handler(ns)
        assert rc == 0
        assert registry.find_by_name('dispatch-test') is not None

    def test_handler_rejects_legacy_tool_flag(
        self, project_root: Path, isolated_home: Path,
        capsys: pytest.CaptureFixture,
    ):
        ns = argparse.Namespace(name=None, non_interactive=True,
                                tool='claude-code', provider=None)
        rc = init_cmd._handler(ns)
        assert rc == 2
        err = capsys.readouterr().err
        assert '--tool/--provider were removed' in err

    def test_handler_rejects_legacy_provider_flag(
        self, project_root: Path, isolated_home: Path,
        capsys: pytest.CaptureFixture,
    ):
        ns = argparse.Namespace(name=None, non_interactive=True,
                                tool=None, provider='claude')
        rc = init_cmd._handler(ns)
        assert rc == 2


# ─── Optional install helpers (real path, integration with core/) ──────────


class TestOptionalInstallHelpers:
    """The three install helpers are thin wrappers; here we just confirm
    they invoke convert+install with the right targets. Heavy validation
    is in tests/core/test_install.py."""

    def test_metrics_hook_skip_is_noop(
        self, project_root: Path, isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        called = {'count': 0}
        from orquestrum.core import convert as core_convert
        monkeypatch.setattr(core_convert, 'main',
                            lambda argv: called.__setitem__('count', called['count'] + 1))
        init_impl._install_metrics_hook(project_root, 'skip')
        assert called['count'] == 0

    def test_install_agents_targets_home(
        self, project_root: Path, isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        from orquestrum.core import convert as core_convert
        from orquestrum.core import install as core_install
        # Pretend the cache already has the integration so convert is skipped
        from orquestrum.lib import paths
        monkeypatch.setattr(paths, 'convert_output_root',
                            lambda: project_root / 'cache')
        (project_root / 'cache' / 'claude-code').mkdir(parents=True)

        captured: list = []
        monkeypatch.setattr(core_convert, 'main', lambda argv: captured.append(('convert', argv)))
        monkeypatch.setattr(core_install, 'main',
                            lambda argv: captured.append(('install', argv)))
        init_impl._install_agents_global(project_root)
        # Convert NOT called (cache already populated)
        assert not any(c[0] == 'convert' for c in captured)
        # Install called with --target ~
        install_calls = [c for c in captured if c[0] == 'install']
        assert len(install_calls) == 1
        argv = install_calls[0][1]
        assert '--tool' in argv and 'claude-code' in argv
        assert '--target' in argv
        target_idx = argv.index('--target') + 1
        assert argv[target_idx] == str(Path.home())
