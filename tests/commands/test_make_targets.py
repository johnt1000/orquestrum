"""Developer-flow integration tests: end-to-end `make` targets.

These tests exercise the same code paths a contributor hits when running
`make lint`, `make convert-dry`, `make doctor`, `make audit`, `make help`,
and ad-hoc `orquestrum --version`. They prove the CLI works against the
real canonical repo without delegating to a subagent or external service.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess from the canonical repo root."""
    env = os.environ.copy()
    # Sandbox the registry — never touch the user's real ~/.orquestrum/.
    env['ORQUESTRUM_HOME'] = str(REPO_ROOT / '.pytest_cache' / 'orq-home-make-tests')
    return subprocess.run(
        [sys.executable, '-m', 'orquestrum.cli', *args],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env, **kw,
    )


class TestVersion:
    def test_version_flag_prints_version(self):
        result = _run(['--version'])
        assert result.returncode == 0
        assert 'orquestrum' in result.stdout

    def test_version_subcommand_prints_python(self):
        result = _run(['version'])
        assert result.returncode == 0
        assert 'orquestrum' in result.stdout
        assert 'Python' in result.stdout


class TestMakeLint:
    """Mirrors `make lint`."""

    def test_exits_zero_on_clean_repo(self):
        result = _run(['lint'])
        assert result.returncode == 0, f'lint failed:\n{result.stdout}\n{result.stderr}'
        assert '0 errors' in result.stdout

    def test_output_lists_agents_and_skills(self):
        result = _run(['lint'])
        assert '=== Agents ===' in result.stdout
        assert '=== Skills ===' in result.stdout


class TestMakeConvertDry:
    """Mirrors `make convert-dry`."""

    def test_dry_run_does_not_write_files(self, tmp_path: Path):
        before = sorted((REPO_ROOT / 'integrations').rglob('*'))
        result = _run(['convert', '--all', '--dry-run'])
        assert result.returncode == 0, result.stderr
        after = sorted((REPO_ROOT / 'integrations').rglob('*'))
        assert before == after, 'dry-run should not change integrations/'

    def test_dry_run_emits_summary(self):
        result = _run(['convert', '--all', '--dry-run'])
        assert result.returncode == 0
        # The summary mentions tools or inventory keywords
        assert 'tool' in result.stdout.lower() or 'agent' in result.stdout.lower()


class TestMakeDoctor:
    """Mirrors `make doctor` — JSON mode for assertable output."""

    def test_doctor_json_returns_summary(self):
        result = _run(['doctor', '--json'])
        # Doctor may exit 0 or 1 depending on the environment, but stdout must
        # always contain the summary.
        assert result.returncode in (0, 1)
        import json
        out = result.stdout
        start = out.index('{')
        end = out.rindex('}') + 1
        summary = json.loads(out[start:end])
        assert 'errors' in summary
        assert 'warnings' in summary
        assert 'results' in summary

    def test_doctor_human_output_contains_sections(self):
        result = _run(['doctor'])
        assert 'Runtime' in result.stdout
        assert 'Optional extras' in result.stdout
        assert 'Framework artifacts' in result.stdout


class TestMakeAudit:
    """Mirrors `make audit` (payload audit is the default)."""

    def test_audit_payload_runs(self):
        result = _run(['audit', 'payload'])
        # Should run cleanly on the canonical source. May print warnings but
        # the exit code must be 0.
        assert result.returncode == 0, f'{result.stdout}\n{result.stderr}'


class TestExtras:
    def test_extras_list_runs(self):
        result = _run(['extras'])
        assert result.returncode == 0
        assert 'ui' in result.stdout
        assert 'webview' in result.stdout


class TestRepos:
    def test_repos_list_with_isolated_home(self):
        result = _run(['repos', 'list'])
        assert result.returncode == 0
        # Either empty or has projects — both prints something
        assert result.stdout.strip()


class TestHelp:
    @pytest.mark.parametrize('subcmd', ['lint', 'doctor', 'repos', 'extras', 'init', 'update'])
    def test_subcommand_help_does_not_crash(self, subcmd: str):
        result = _run([subcmd, '--help'])
        assert result.returncode == 0
        assert subcmd in result.stdout.lower() or 'usage' in result.stdout.lower()
