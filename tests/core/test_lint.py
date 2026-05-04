"""Integration tests for orquestrum lint (subprocess-based).

Lint is hardwired to the canonical repo root via __file__, so these tests
call it as a subprocess and verify exit codes and output patterns.
"""
import subprocess
import sys
import pytest


def _run_lint() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m', 'orquestrum.core.lint'],
        capture_output=True,
        text=True,
    )


class TestLintOnRealRepo:
    def test_exits_0_on_clean_repo(self):
        result = _run_lint()
        assert result.returncode == 0, f'lint failed:\n{result.stdout}\n{result.stderr}'

    def test_success_line_contains_counts(self):
        result = _run_lint()
        assert '8 agents' in result.stdout
        assert '26 skills' in result.stdout   # bumped when schema-manager landed
        assert '0 errors' in result.stdout

    def test_success_line_contains_asset_count(self):
        result = _run_lint()
        assert 'assets' in result.stdout

    def test_no_tool_specific_paths_in_stdout(self):
        result = _run_lint()
        # These would appear in ✗ error lines if found in source files
        for forbidden in ('.opencode/', '.sdd/'):
            assert forbidden not in result.stdout

    def test_all_agents_pass(self):
        result = _run_lint()
        assert result.returncode == 0
        # Each agent listed under === Agents === should show ✓
        in_agents_section = False
        for line in result.stdout.splitlines():
            if '=== Agents ===' in line:
                in_agents_section = True
            elif line.startswith('==='):
                in_agents_section = False
            elif in_agents_section and 'agents/' in line:
                assert '✓' in line, f'Agent did not pass: {line}'
