"""Tests for `orquestrum setup` — the global-install wizard.

The wizard is pure orchestration over `convert.main` + `install.main`.
We monkeypatch those so the tests stay fast and don't actually drop
files into the user's real ~/.claude/. State detection is verified via
a fake manifest in an isolated `~/.orquestrum/`.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pytest

from orquestrum.commands import setup


@pytest.fixture()
def isolated_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sandbox ORQUESTRUM_HOME so installs_manifest reads/writes go to tmp."""
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    return home


@pytest.fixture()
def stub_install_pipeline(monkeypatch: pytest.MonkeyPatch):
    """Patch convert.main + install.main + convert_output_root so the wizard
    runs end-to-end without actually touching the user's home dir."""
    calls: dict[str, list] = {'convert': [], 'install': []}

    from orquestrum.core import convert as core_convert
    from orquestrum.core import install as core_install
    from orquestrum.lib import paths

    def fake_convert(argv):
        calls['convert'].append(list(argv or []))

    def fake_install(argv):
        calls['install'].append(list(argv or []))

    monkeypatch.setattr(core_convert, 'main', fake_convert)
    monkeypatch.setattr(core_install, 'main', fake_install)
    # Pretend the cache directory always exists so convert is skipped —
    # individual tests can override this via `cache_missing` if needed.
    fake_cache = Path('/tmp/orq-cache-stub')
    fake_cache.mkdir(exist_ok=True)
    (fake_cache / 'claude-code').mkdir(exist_ok=True)
    (fake_cache / 'opencode').mkdir(exist_ok=True)
    monkeypatch.setattr(paths, 'convert_output_root', lambda: fake_cache)
    return calls


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override Path.home() so the wizard targets a temp dir, not the
    user's real home — avoids polluting ~/.claude/ during tests."""
    fake = tmp_path / 'fake-home'
    fake.mkdir()
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake))
    return fake


# ─── state detection ───────────────────────────────────────────────────────


class TestDetectState:
    def test_empty_manifest_reports_nothing_installed(
        self, isolated_manifest: Path, fake_home: Path,
    ):
        state = setup._detect_state()
        assert state['claude-code']['installed'] is False
        assert state['opencode']['installed'] is False

    def test_records_claude_code_install(
        self, isolated_manifest: Path, fake_home: Path,
    ):
        from orquestrum.lib import installs_manifest
        installs_manifest.record_install(
            'claude-code', fake_home,
            files=[fake_home / '.claude' / 'agents' / 'helm.md'],
            directories=[fake_home / '.claude'],
        )
        state = setup._detect_state()
        assert state['claude-code']['installed'] is True
        assert state['claude-code']['files'] == 1
        assert state['claude-code']['target'] == fake_home

    def test_ignores_install_at_unrelated_target(
        self, isolated_manifest: Path, fake_home: Path, tmp_path: Path,
    ):
        """A claude-code install at a project-level path (not ~) shouldn't
        confuse the global state detector — setup only cares about the
        canonical global locations."""
        from orquestrum.lib import installs_manifest
        unrelated = tmp_path / 'some-project'
        unrelated.mkdir()
        installs_manifest.record_install(
            'claude-code', unrelated,
            files=[], directories=[],
        )
        state = setup._detect_state()
        assert state['claude-code']['installed'] is False


# ─── --yes (non-interactive) flow ──────────────────────────────────────────


class TestNonInteractiveFlow:
    def test_yes_installs_claude_code_when_missing(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        rc = setup._run_setup(interactive=False)
        assert rc == 0
        # convert NOT called (cache stub pre-populated)
        assert stub_install_pipeline['convert'] == []
        # install called for claude-code with --target = fake home
        installs = stub_install_pipeline['install']
        assert len(installs) == 1
        assert installs[0][:2] == ['--tool', 'claude-code']
        target_idx = installs[0].index('--target') + 1
        assert installs[0][target_idx] == str(fake_home)

    def test_yes_skips_opencode_when_missing(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        # opencode default is N → not installed even with --yes
        setup._run_setup(interactive=False)
        installs = stub_install_pipeline['install']
        opencode_calls = [c for c in installs if 'opencode' in c]
        assert opencode_calls == []

    def test_yes_skips_claude_code_when_already_installed(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        from orquestrum.lib import installs_manifest
        installs_manifest.record_install(
            'claude-code', fake_home, files=[], directories=[],
        )
        rc = setup._run_setup(interactive=False)
        assert rc == 0
        # default for already-installed is N → install NOT called
        assert stub_install_pipeline['install'] == []

    def test_no_changes_message_when_nothing_selected(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.lib import installs_manifest
        installs_manifest.record_install(
            'claude-code', fake_home, files=[], directories=[],
        )
        setup._run_setup(interactive=False)
        out = capsys.readouterr().out
        assert 'No changes' in out


# ─── interactive flow (scripted input) ─────────────────────────────────────


class TestInteractiveFlow:
    def test_user_says_yes_to_both_runs_both_installs(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        # Force interactive + script the answers
        from orquestrum.lib import prompts
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
        answers = iter(['y', 'y'])
        monkeypatch.setattr(prompts, '_read_line',
                            lambda prompt: next(answers, ''))

        rc = setup._run_setup(interactive=True)
        assert rc == 0
        installs = stub_install_pipeline['install']
        tools = [c[c.index('--tool') + 1] for c in installs if '--tool' in c]
        assert sorted(tools) == ['claude-code', 'opencode']

    def test_user_says_no_to_both_runs_nothing(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        from orquestrum.lib import prompts
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
        answers = iter(['n', 'n'])
        monkeypatch.setattr(prompts, '_read_line',
                            lambda prompt: next(answers, ''))
        rc = setup._run_setup(interactive=True)
        assert rc == 0
        assert stub_install_pipeline['install'] == []


# ─── _install_one ──────────────────────────────────────────────────────────


class TestInstallOne:
    def test_runs_convert_when_cache_missing(
        self, isolated_manifest: Path, fake_home: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Override convert_output_root to a dir without claude-code subdir
        empty_cache = tmp_path / 'empty-cache'
        empty_cache.mkdir()
        from orquestrum.lib import paths
        monkeypatch.setattr(paths, 'convert_output_root', lambda: empty_cache)

        from orquestrum.core import convert as core_convert
        from orquestrum.core import install as core_install
        convert_calls: list = []
        install_calls: list = []
        monkeypatch.setattr(core_convert, 'main',
                            lambda argv: convert_calls.append(list(argv)))
        monkeypatch.setattr(core_install, 'main',
                            lambda argv: install_calls.append(list(argv)))

        ok = setup._install_one('claude-code', fake_home, provider='claude')
        assert ok is True
        assert convert_calls == [['--tool', 'claude-code', '--provider', 'claude']]
        assert install_calls and 'claude-code' in install_calls[0]

    def test_skips_convert_when_cache_present(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        ok = setup._install_one('claude-code', fake_home, provider=None)
        assert ok is True
        assert stub_install_pipeline['convert'] == []
        assert len(stub_install_pipeline['install']) == 1

    def test_returns_false_on_install_failure(
        self, isolated_manifest: Path, fake_home: Path, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Cache present so convert is skipped
        cache = tmp_path / 'cache'
        (cache / 'claude-code').mkdir(parents=True)
        from orquestrum.lib import paths
        monkeypatch.setattr(paths, 'convert_output_root', lambda: cache)

        from orquestrum.core import install as core_install

        def failing_install(argv):
            raise SystemExit(1)

        monkeypatch.setattr(core_install, 'main', failing_install)
        ok = setup._install_one('claude-code', fake_home)
        assert ok is False


# ─── argparse + handler ────────────────────────────────────────────────────


class TestRegister:
    def test_register_adds_subparser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        setup.register(sub)
        assert 'setup' in sub.choices

    def test_handler_dispatches_with_yes(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        ns = argparse.Namespace(non_interactive=True)
        rc = setup._handler(ns)
        assert rc == 0

    def test_handler_default_is_interactive(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        # Force non-tty so prompts.ask_yn falls back to defaults
        from orquestrum.lib import prompts
        monkeypatch.setattr(prompts, '_is_interactive', lambda: False)
        ns = argparse.Namespace(non_interactive=False)
        rc = setup._handler(ns)
        assert rc == 0


# ─── output/UX ─────────────────────────────────────────────────────────────


class TestOutput:
    def test_first_time_user_sees_welcome_banner(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
    ):
        setup._run_setup(interactive=False)
        out = capsys.readouterr().out
        assert 'Welcome' in out
        assert 'orquestrum init' in out  # references the project-level command

    def test_returning_user_sees_existing_install(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
    ):
        from orquestrum.lib import installs_manifest
        installs_manifest.record_install(
            'claude-code', fake_home,
            files=[fake_home / 'a.md'], directories=[],
        )
        setup._run_setup(interactive=False)
        out = capsys.readouterr().out
        assert 'claude-code' in out
        # The detected line marks installed entries
        assert '✓' in out


# ─── UI prompt (3rd prompt added in WSB) ───────────────────────────────────


class TestUIPrompt:
    def test_three_prompts_numbered_correctly(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Fast path now has 3 prompts; the labels [1/3], [2/3], [3/3]
        must appear in the question text passed to _read_line."""
        from orquestrum.lib import prompts
        seen_prompts: list[str] = []
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)

        def _capture(prompt: str) -> str:
            seen_prompts.append(prompt)
            return 'n'

        monkeypatch.setattr(prompts, '_read_line', _capture)
        setup._run_setup(interactive=True)
        all_prompts = ' '.join(seen_prompts)
        assert '[1/3]' in all_prompts
        assert '[2/3]' in all_prompts
        assert '[3/3]' in all_prompts

    def test_ui_prompt_default_yes_when_extras_missing(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """When fastapi is NOT importable, the UI prompt should default
        to Y so first-time users discover the dashboard. We mock the
        probe and the install function to verify the default takes effect."""
        called: list[bool] = []
        monkeypatch.setattr(setup, '_ui_extra_installed', lambda: False)
        monkeypatch.setattr(setup, '_install_ui_extra',
                            lambda: called.append(True) or True)
        # Non-interactive uses defaults silently
        setup._run_setup(interactive=False)
        # claude-code default Y + ui default Y → both invoked
        assert called == [True], 'UI extra should be installed on default-Y path'

    def test_ui_prompt_default_no_when_already_installed(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """When the ui extra is already installed, default flips to N to
        avoid pointless re-installs on every setup re-run."""
        called: list[bool] = []
        monkeypatch.setattr(setup, '_ui_extra_installed', lambda: True)
        monkeypatch.setattr(setup, '_install_ui_extra',
                            lambda: called.append(True) or True)
        setup._run_setup(interactive=False)
        assert called == [], 'UI extra should NOT be re-installed by default'

    def test_post_install_message_always_mentions_orquestrum_web(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """`orquestrum web` should appear in the next-steps regardless of
        whether the user installed the UI extra — discovery matters."""
        # Decline UI but accept claude-code
        monkeypatch.setattr(setup, '_ui_extra_installed', lambda: False)
        monkeypatch.setattr(setup, '_install_ui_extra', lambda: True)
        from orquestrum.lib import prompts
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
        # claude-code Y, opencode N, ui N
        answers = iter(['y', 'n', 'n'])
        monkeypatch.setattr(prompts, '_read_line',
                            lambda prompt: next(answers, ''))
        setup._run_setup(interactive=True)
        out = capsys.readouterr().out
        assert 'orquestrum web' in out, 'next-steps must mention web dashboard'
