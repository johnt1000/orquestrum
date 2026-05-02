"""End-user installation flow: `orquestrum init`.

Validates the integration between init_impl, the manifest, and the global
registry. The `_run_install` heavy path is patched out — convert/install
are tested separately at the core layer.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pytest

from orquestrum.commands import init as init_cmd
from orquestrum.commands import init_impl
from orquestrum.lib import registry, manifest


@pytest.fixture()
def stub_install(monkeypatch: pytest.MonkeyPatch):
    """Stub the heavy install path so init can run without canonical/integrations."""
    calls: list = []
    monkeypatch.setattr(init_impl, '_run_install', lambda root, tool, provider: calls.append((str(root), tool, provider)) or True)
    return calls


class TestRunInitFreshProject:
    def test_creates_orquestrum_dir_and_files(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        rc = init_impl.run_init(tool=None, provider=None, name=None)
        assert rc == 0
        assert (project_root / '.orquestrum' / 'config.toml').is_file()
        assert (project_root / '.orquestrum' / '.gitignore').is_file()
        assert (project_root / '.orquestrum' / 'metrics').is_dir()
        assert (project_root / 'ORQUESTRUM.md').is_file()

    def test_uses_directory_name_when_no_name_given(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool=None, provider=None, name=None)
        text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert f'name      = "{project_root.name}"' in text

    def test_explicit_name_overrides_dirname(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool=None, provider=None, name='custom')
        text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert 'name      = "custom"' in text

    def test_registers_in_global_registry(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool=None, provider=None, name='alpha')
        entry = registry.find_by_name('alpha')
        assert entry is not None
        assert entry['path'] == str(project_root.resolve())

    def test_writes_manifest_with_history_entry(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool=None, provider=None, name=None)
        state = manifest.read_manifest_state(project_root)
        assert state is not None
        assert any('initialized' in entry for entry in state.history)

    def test_skips_install_when_no_tool(
        self, project_root: Path, isolated_home: Path, stub_install,
        capsys: pytest.CaptureFixture,
    ):
        init_impl.run_init(tool=None, provider=None, name=None)
        assert stub_install == []
        out = capsys.readouterr().out
        assert 'Next: run `orquestrum init --tool' in out

    def test_runs_install_when_tool_provided(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool='claude-code', provider='claude', name=None)
        assert stub_install == [(str(project_root), 'claude-code', 'claude')]


class TestReinit:
    def test_appends_history_when_tool_changes(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool='claude-code', provider=None, name='proj')
        init_impl.run_init(tool='opencode', provider=None, name='proj')
        state = manifest.read_manifest_state(project_root)
        assert state is not None
        assert any('switched' in entry for entry in state.history)

    def test_emits_reinit_message(
        self, project_root: Path, isolated_home: Path, stub_install,
        capsys: pytest.CaptureFixture,
    ):
        init_impl.run_init(tool=None, provider=None, name=None)
        capsys.readouterr()  # discard
        init_impl.run_init(tool=None, provider=None, name=None)
        out = capsys.readouterr().out
        assert 'Re-initialized' in out

    def test_updates_config_in_place(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        init_impl.run_init(tool=None, provider=None, name=None)
        init_impl.run_init(tool='cursor', provider='claude', name=None)
        cfg_text = (project_root / '.orquestrum' / 'config.toml').read_text(encoding='utf-8')
        assert 'tool      = "cursor"' in cfg_text
        assert 'provider  = "claude"' in cfg_text


class TestRunInstallSafety:
    def test_returns_false_when_canonical_missing(
        self, project_root: Path, isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        monkeypatch.setattr('orquestrum.lib.paths.canonical_root', lambda: None)
        ok = init_impl._run_install(project_root, 'claude-code', None)
        assert ok is False
        err = capsys.readouterr().err
        assert 'canonical' in err.lower()


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        init_cmd.register(sub)
        assert 'init' in sub.choices

    def test_handler_dispatches_to_run_init(
        self, project_root: Path, isolated_home: Path, stub_install,
    ):
        ns = argparse.Namespace(tool=None, provider=None, name='dispatch-test')
        rc = init_cmd._handler(ns)
        assert rc == 0
        assert registry.find_by_name('dispatch-test') is not None
