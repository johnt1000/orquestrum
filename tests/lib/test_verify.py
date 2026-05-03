"""Unit tests for orquestrum.lib.verify — convert/install post-action verifiers."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.lib import verify


# ── Fixture builders that fake a "good" output for each tool ────────────────


def _build_claude_code(out: Path) -> None:
    """Build a complete claude-code integration tree under `out`.

    Reflects the v0.3.1 layout: everything under .claude/ for total
    isolation. Skills at .claude/skills/ (Claude Code's discovery path);
    governance docs + hook scripts at .claude/sdd/ (orquestrum-internal
    but still inside .claude/ so a single uninstall reclaims it cleanly).
    """
    agents = out / '.claude' / 'agents'
    agents.mkdir(parents=True)
    for n in (
        'helm-the-architect', 'lore-product-strategist', 'forge-dev-lead',
        'cipher-security-lead', 'ward-quality-lead', 'cast-ship-lead',
        'flux-support-lead', 'trace-onboarding-lead',
    ):
        (agents / f'{n}.md').write_text('---\nname: x\n---\nbody', encoding='utf-8')
    (out / '.claude' / 'skills').mkdir(parents=True)
    (out / '.claude' / 'settings.json').write_text(
        json.dumps({'hooks': {}}), encoding='utf-8',
    )
    sdd = out / '.claude' / 'sdd'
    (sdd / 'docs').mkdir(parents=True)
    (sdd / 'scripts' / 'hooks').mkdir(parents=True)
    (sdd / 'scripts' / 'lib').mkdir(parents=True)
    (sdd / 'scripts' / 'archive-cleanup.sh').write_text(
        '#!/usr/bin/env bash\n' + 'echo cleanup\n' * 10, encoding='utf-8',
    )


def _build_opencode(out: Path, *, with_placeholder: bool = True) -> None:
    agents = out / 'agents'
    agents.mkdir(parents=True)
    for n in (
        'helm-the-architect', 'lore-product-strategist', 'forge-dev-lead',
        'cipher-security-lead', 'ward-quality-lead', 'cast-ship-lead',
        'flux-support-lead', 'trace-onboarding-lead',
    ):
        body = 'See __OPENCODE_ROOT__/docs/SDLC.md\n' if with_placeholder else 'body\n'
        (agents / f'{n}.md').write_text(body, encoding='utf-8')
    (out / 'docs').mkdir()
    (out / 'skills').mkdir()
    (out / 'scripts').mkdir()
    (out / 'scripts' / 'archive-cleanup.sh').write_text(
        '#!/usr/bin/env bash\n' + 'echo cleanup\n' * 10, encoding='utf-8',
    )


def _build_cursor(out: Path, skill_count: int = 25) -> None:
    rules = out / '.cursor' / 'rules'
    rules.mkdir(parents=True)
    for i in range(8):
        (rules / f'agent-{i}.mdc').write_text('rules', encoding='utf-8')
    for i in range(skill_count):
        (rules / f'skill-{i}.mdc').write_text('rules', encoding='utf-8')
    (out / '.sdd' / 'scripts').mkdir(parents=True)
    (out / '.sdd' / 'scripts' / 'archive-cleanup.sh').write_text(
        '#!/usr/bin/env bash\n' + 'echo cleanup\n' * 10, encoding='utf-8',
    )


def _build_aider(out: Path) -> None:
    out.mkdir(parents=True)
    (out / 'CONVENTIONS.md').write_text('x' * 1000, encoding='utf-8')
    (out / 'scripts').mkdir()
    (out / 'scripts' / 'archive-cleanup.sh').write_text(
        '#!/usr/bin/env bash\n' + 'echo cleanup\n' * 10, encoding='utf-8',
    )


def _build_windsurf(out: Path) -> None:
    out.mkdir(parents=True)
    (out / '.windsurfrules').write_text('x' * 1000, encoding='utf-8')
    (out / 'scripts').mkdir()
    (out / 'scripts' / 'archive-cleanup.sh').write_text(
        '#!/usr/bin/env bash\n' + 'echo cleanup\n' * 10, encoding='utf-8',
    )


# ─── verify_convert_output ──────────────────────────────────────────────────


class TestConvertVerifierClaudeCode:
    def test_passes_for_complete_integration(self, tmp_path: Path):
        out = tmp_path / 'claude-code'
        _build_claude_code(out)
        report = verify.verify_convert_output('claude-code', out)
        assert report.passed, report.render()

    def test_fails_when_agent_count_short(self, tmp_path: Path):
        out = tmp_path / 'claude-code'
        _build_claude_code(out)
        # Drop one agent
        next((out / '.claude' / 'agents').glob('*.md')).unlink()
        report = verify.verify_convert_output('claude-code', out)
        assert not report.passed
        assert any('expected 8' in c.detail for c in report.checks if not c.ok)

    def test_fails_when_settings_missing(self, tmp_path: Path):
        out = tmp_path / 'claude-code'
        _build_claude_code(out)
        (out / '.claude' / 'settings.json').unlink()
        report = verify.verify_convert_output('claude-code', out)
        assert not report.passed

    def test_fails_when_sdd_scripts_missing(self, tmp_path: Path):
        out = tmp_path / 'claude-code'
        _build_claude_code(out)
        import shutil
        shutil.rmtree(out / '.claude' / 'sdd' / 'scripts' / 'hooks')
        report = verify.verify_convert_output('claude-code', out)
        assert not report.passed


class TestConvertVerifierOpenCode:
    def test_passes_for_complete_integration(self, tmp_path: Path):
        out = tmp_path / 'opencode'
        _build_opencode(out)
        report = verify.verify_convert_output('opencode', out)
        assert report.passed, report.render()

    def test_does_not_check_placeholder_at_convert_stage(self, tmp_path: Path):
        # convert intentionally leaves __OPENCODE_ROOT__ unresolved — install
        # is the stage that resolves it. So the convert verifier must NOT
        # fail when the placeholder is present.
        out = tmp_path / 'opencode'
        _build_opencode(out, with_placeholder=True)
        report = verify.verify_convert_output('opencode', out)
        assert report.passed


class TestConvertVerifierCursor:
    def test_uses_skill_count_for_minimum(self, tmp_path: Path):
        out = tmp_path / 'cursor'
        _build_cursor(out, skill_count=25)
        report = verify.verify_convert_output('cursor', out, expected_skill_count=25)
        assert report.passed

    def test_passes_when_skill_count_higher_than_expected(self, tmp_path: Path):
        out = tmp_path / 'cursor'
        _build_cursor(out, skill_count=30)
        report = verify.verify_convert_output('cursor', out, expected_skill_count=25)
        assert report.passed  # extras allowed

    def test_fails_when_under_minimum(self, tmp_path: Path):
        out = tmp_path / 'cursor'
        _build_cursor(out, skill_count=2)
        report = verify.verify_convert_output('cursor', out, expected_skill_count=25)
        assert not report.passed


class TestConvertVerifierAider:
    def test_passes(self, tmp_path: Path):
        out = tmp_path / 'aider'
        _build_aider(out)
        report = verify.verify_convert_output('aider', out)
        assert report.passed

    def test_fails_when_conventions_too_small(self, tmp_path: Path):
        out = tmp_path / 'aider'
        _build_aider(out)
        (out / 'CONVENTIONS.md').write_text('tiny', encoding='utf-8')
        report = verify.verify_convert_output('aider', out)
        assert not report.passed


class TestConvertVerifierWindsurf:
    def test_passes(self, tmp_path: Path):
        out = tmp_path / 'windsurf'
        _build_windsurf(out)
        report = verify.verify_convert_output('windsurf', out)
        assert report.passed


class TestConvertVerifierMissingDir:
    def test_reports_failure_when_output_dir_does_not_exist(self, tmp_path: Path):
        out = tmp_path / 'never-created'
        report = verify.verify_convert_output('claude-code', out)
        assert not report.passed
        assert report.checks[0].label == 'output directory exists'


class TestConvertVerifierUnknownTool:
    def test_unknown_tool_returns_failure(self, tmp_path: Path):
        out = tmp_path / 'something'
        out.mkdir()
        report = verify.verify_convert_output('made-up-tool', out)
        assert not report.passed


# ─── verify_install_target ──────────────────────────────────────────────────


class TestInstallVerifierClaudeCode:
    def test_passes_for_complete_install(self, tmp_path: Path):
        target = tmp_path / 'project'
        _build_claude_code(target)
        report = verify.verify_install_target('claude-code', target)
        assert report.passed, report.render()


class TestInstallVerifierOpenCode:
    def test_fails_when_placeholder_unresolved(self, tmp_path: Path):
        target = tmp_path / 'project'
        _build_opencode(target, with_placeholder=True)
        report = verify.verify_install_target('opencode', target)
        assert not report.passed
        assert any('__OPENCODE_ROOT__' in c.label for c in report.checks if not c.ok)

    def test_passes_when_placeholder_resolved(self, tmp_path: Path):
        target = tmp_path / 'project'
        _build_opencode(target, with_placeholder=False)
        report = verify.verify_install_target('opencode', target)
        assert report.passed, report.render()


class TestInstallVerifierMissingTarget:
    def test_reports_failure(self, tmp_path: Path):
        target = tmp_path / 'never-created'
        report = verify.verify_install_target('cursor', target)
        assert not report.passed


# ─── render helpers ─────────────────────────────────────────────────────────


class TestReportRender:
    def test_render_includes_each_check(self, tmp_path: Path):
        out = tmp_path / 'aider'
        _build_aider(out)
        report = verify.verify_convert_output('aider', out)
        rendered = report.render()
        assert 'verify: convert:aider' in rendered
        assert 'CONVENTIONS.md' in rendered

    def test_summary_counts_passes_and_fails(self, tmp_path: Path):
        a = tmp_path / 'aider'
        _build_aider(a)
        b = tmp_path / 'cursor'
        _build_cursor(b, skill_count=2)  # too few skills → fail
        reports = [
            verify.verify_convert_output('aider', a),
            verify.verify_convert_output('cursor', b, expected_skill_count=25),
        ]
        out = verify.render_summary(reports)
        assert '1/2 verifications passed' in out


class TestReportProperties:
    def test_passed_true_when_all_checks_ok(self):
        r = verify.VerifyReport(target='t', root=Path('/tmp'))
        r.add('one', True)
        r.add('two', True)
        assert r.passed
        assert r.fail_count == 0

    def test_passed_false_when_any_fails(self):
        r = verify.VerifyReport(target='t', root=Path('/tmp'))
        r.add('one', True)
        r.add('two', False, 'missing')
        assert not r.passed
        assert r.fail_count == 1


# ─── target shape detection (preflight) ─────────────────────────────────────


class TestDetectTargetMisuse:
    def test_claude_code_with_target_dot_claude_is_rejected(self, tmp_path: Path):
        """Catch the canonical user mistake: `--target ~/.claude` for claude-code.
        Without this guard the install creates ~/.claude/.claude/agents/ —
        files are written but in the wrong place."""
        target = tmp_path / '.claude'
        target.mkdir()
        msg = verify.detect_target_misuse('claude-code', target)
        assert msg is not None
        assert 'double-nested' in msg
        # The error must suggest the parent path as the right answer
        assert str(tmp_path) in msg

    def test_cursor_with_target_dot_cursor_is_rejected(self, tmp_path: Path):
        target = tmp_path / '.cursor'
        target.mkdir()
        msg = verify.detect_target_misuse('cursor', target)
        assert msg is not None
        assert '.cursor' in msg

    def test_claude_code_with_project_root_is_ok(self, tmp_path: Path):
        target = tmp_path / 'myproject'
        target.mkdir()
        assert verify.detect_target_misuse('claude-code', target) is None

    def test_claude_code_with_home_is_ok(self, tmp_path: Path):
        # --target ~ is valid: it creates ~/.claude/agents/ (global install)
        # because basename is the home dir name, not '.claude'
        target = tmp_path / 'home'
        target.mkdir()
        assert verify.detect_target_misuse('claude-code', target) is None

    def test_opencode_no_nesting_check(self, tmp_path: Path):
        # opencode integration has no top-level dot-dir; --target opencode
        # is the canonical install path.
        target = tmp_path / 'opencode'
        target.mkdir()
        assert verify.detect_target_misuse('opencode', target) is None

    def test_unknown_tool_returns_none(self, tmp_path: Path):
        assert verify.detect_target_misuse('made-up', tmp_path) is None


# ─── render_listing ─────────────────────────────────────────────────────────


class TestRenderListing:
    def test_lists_top_level_dirs_and_files(self, tmp_path: Path):
        out = tmp_path / 'cache' / 'claude-code'
        _build_claude_code(out)
        rendered = verify.render_listing(out)
        # claude-code is now fully under .claude/ — single top-level entry
        assert '.claude/' in rendered
        # Sub-entries shown with count
        assert 'items' in rendered

    def test_handles_missing_directory(self, tmp_path: Path):
        out = tmp_path / 'never-created'
        rendered = verify.render_listing(out)
        assert 'not present' in rendered

    def test_truncates_long_listings(self, tmp_path: Path):
        out = tmp_path / 'big'
        out.mkdir()
        sub = out / 'huge'
        sub.mkdir()
        for i in range(50):
            (sub / f'file-{i:02d}.md').write_text('x', encoding='utf-8')
        rendered = verify.render_listing(out, max_per_dir=5)
        # Truncation marker visible
        assert '+45 more' in rendered or '… +' in rendered

    def test_only_filter_focuses_on_named_entries(self, tmp_path: Path):
        out = tmp_path / 'home'
        out.mkdir()
        # Simulate a busy home dir: orquestrum dirs + lots of unrelated stuff
        (out / '.claude').mkdir()
        (out / '.sdd').mkdir()
        (out / 'Documents').mkdir()
        (out / 'Downloads').mkdir()
        (out / '.zshrc').write_text('x', encoding='utf-8')
        rendered = verify.render_listing(out, only=['.claude', '.sdd'])
        assert '.claude/' in rendered
        assert '.sdd/' in rendered
        # Unrelated user dirs filtered out
        assert 'Documents' not in rendered
        assert 'Downloads' not in rendered

    def test_skips_unlistable_subdir_without_crashing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """If a subdirectory raises PermissionError on iterdir
        (e.g. ~/.Trash on macOS), the listing must continue, not abort."""
        out = tmp_path / 'home'
        out.mkdir()
        (out / 'good').mkdir()
        (out / 'good' / 'file.md').write_text('x', encoding='utf-8')
        bad = out / 'bad'
        bad.mkdir()

        original_iterdir = Path.iterdir

        def fake_iterdir(self):
            if self == bad:
                raise PermissionError(1, 'Operation not permitted', str(self))
            return original_iterdir(self)

        monkeypatch.setattr(Path, 'iterdir', fake_iterdir)
        # Must not raise
        rendered = verify.render_listing(out)
        # Reports the failure inline instead of crashing
        assert 'good' in rendered
        assert 'bad' in rendered
        assert 'not listable' in rendered or 'Operation not permitted' in rendered

    def test_top_level_iterdir_failure_returns_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        out = tmp_path / 'restricted'
        out.mkdir()
        original_iterdir = Path.iterdir

        def fake_iterdir(self):
            if self == out:
                raise PermissionError(1, 'denied', str(self))
            return original_iterdir(self)

        monkeypatch.setattr(Path, 'iterdir', fake_iterdir)
        rendered = verify.render_listing(out)
        assert 'cannot list' in rendered


class TestRenderInstallListing:
    def test_focuses_on_tool_specific_top_level_entries(self, tmp_path: Path):
        target = tmp_path / 'home'
        target.mkdir()
        (target / '.claude').mkdir()
        (target / 'Documents').mkdir()
        rendered = verify.render_install_listing('claude-code', target)
        # claude-code is fully under .claude/ now — only that root surfaces
        assert '.claude/' in rendered
        assert 'Documents' not in rendered


class TestVerifyInstallTolerantOfUserAgents:
    """Regression for the 'expected 8, found 12' false negative when the
    user has their own agents in .claude/agents/ alongside orquestrum's."""

    def test_claude_code_passes_with_extra_user_agent_files(self, tmp_path: Path):
        target = tmp_path / 'project'
        _build_claude_code(target)
        # User agents in the same dir
        agents = target / '.claude' / 'agents'
        (agents / 'my-personal-agent.md').write_text(
            '---\nname: mine\n---\n', encoding='utf-8',
        )
        (agents / 'team-reviewer.md').write_text(
            '---\nname: team\n---\n', encoding='utf-8',
        )
        report = verify.verify_install_target('claude-code', target)
        assert report.passed, report.render()

    def test_claude_code_fails_when_orquestrum_agent_missing(self, tmp_path: Path):
        target = tmp_path / 'project'
        _build_claude_code(target)
        # Drop a known-orquestrum agent
        (target / '.claude' / 'agents' / 'helm-the-architect.md').unlink()
        report = verify.verify_install_target('claude-code', target)
        assert not report.passed
        assert any('helm-the-architect' in c.detail
                   for c in report.checks if not c.ok)

    def test_opencode_passes_with_extra_user_agents(self, tmp_path: Path):
        target = tmp_path / 'opencode-config'
        _build_opencode(target, with_placeholder=False)
        (target / 'agents' / 'my-extra.md').write_text('x', encoding='utf-8')
        report = verify.verify_install_target('opencode', target)
        assert report.passed, report.render()
