"""Unit tests for orquestrum.lib.verify — convert/install post-action verifiers."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.lib import verify


# ── Fixture builders that fake a "good" output for each tool ────────────────


def _build_claude_code(out: Path) -> None:
    """Build a complete claude-code integration tree under `out`."""
    agents = out / '.claude' / 'agents'
    agents.mkdir(parents=True)
    for n in (
        'helm-the-architect', 'lore-product-strategist', 'forge-dev-lead',
        'cipher-security-lead', 'ward-quality-lead', 'cast-ship-lead',
        'flux-support-lead', 'trace-onboarding-lead',
    ):
        (agents / f'{n}.md').write_text('---\nname: x\n---\nbody', encoding='utf-8')
    (out / '.claude' / 'settings.json').write_text(
        json.dumps({'hooks': {}}), encoding='utf-8',
    )
    (out / '.sdd' / 'docs').mkdir(parents=True)
    (out / '.sdd' / 'skills').mkdir(parents=True)
    (out / '.sdd' / 'scripts' / 'hooks').mkdir(parents=True)
    (out / '.sdd' / 'scripts' / 'lib').mkdir(parents=True)
    (out / '.sdd' / 'scripts' / 'archive-cleanup.sh').write_text(
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
        shutil.rmtree(out / '.sdd' / 'scripts' / 'hooks')
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
