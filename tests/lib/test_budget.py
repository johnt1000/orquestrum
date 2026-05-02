"""Tests for orquestrum.lib.budget."""
import json
import pytest
from pathlib import Path
from orquestrum.lib.budget import (
    SOFT_THRESHOLDS,
    BudgetReport,
    check_session_budget,
)


def _write_session(path: Path, in_tokens: int, out_tokens: int, by_skill: dict | None = None) -> None:
    data = {
        'tier': 'balanced',
        'totals': {'input_tokens': in_tokens, 'output_tokens': out_tokens},
        'by_skill': by_skill or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


class TestSoftThresholds:
    def test_all_tiers_present(self):
        for tier in ('deep', 'balanced', 'mechanical', 'sharp'):
            assert tier in SOFT_THRESHOLDS

    def test_deep_threshold_higher_than_balanced(self):
        assert SOFT_THRESHOLDS['deep'][0] > SOFT_THRESHOLDS['balanced'][0]


class TestBudgetReportHasWarning:
    def test_no_warning_when_under(self):
        report = BudgetReport(
            tier='balanced', input_tokens=100, output_tokens=100,
            input_threshold=100_000, output_threshold=8_000,
            over_input=False, over_output=False,
            top_contributor=None, top_contributor_in=0,
        )
        assert not report.has_warning

    def test_warning_when_over_input(self):
        report = BudgetReport(
            tier='balanced', input_tokens=200_000, output_tokens=100,
            input_threshold=100_000, output_threshold=8_000,
            over_input=True, over_output=False,
            top_contributor=None, top_contributor_in=0,
        )
        assert report.has_warning

    def test_format_includes_tier_and_threshold(self):
        report = BudgetReport(
            tier='balanced', input_tokens=200_000, output_tokens=100,
            input_threshold=100_000, output_threshold=8_000,
            over_input=True, over_output=False,
            top_contributor='review-manager', top_contributor_in=80_000,
        )
        text = report.format()
        assert 'balanced' in text
        assert '100,000' in text
        assert 'review-manager' in text


class TestCheckSessionBudget:
    def test_missing_file_returns_no_warning(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        report = check_session_budget(session, 'balanced')
        assert not report.has_warning
        assert report.input_tokens == 0

    def test_malformed_json_returns_no_warning(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        session.write_text('not json', encoding='utf-8')
        report = check_session_budget(session, 'balanced')
        assert not report.has_warning

    def test_under_threshold_no_warning(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        _write_session(session, in_tokens=1_000, out_tokens=100)
        report = check_session_budget(session, 'balanced')
        assert not report.has_warning

    def test_over_input_threshold_fires_warning(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        thr = SOFT_THRESHOLDS['balanced'][0]
        _write_session(session, in_tokens=thr + 1, out_tokens=0)
        report = check_session_budget(session, 'balanced')
        assert report.over_input
        assert report.has_warning

    def test_over_output_threshold_fires_warning(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        thr = SOFT_THRESHOLDS['balanced'][1]
        _write_session(session, in_tokens=0, out_tokens=thr + 1)
        report = check_session_budget(session, 'balanced')
        assert report.over_output

    def test_top_contributor_identified(self, tmp_path: Path):
        session = tmp_path / 'session.json'
        _write_session(session, in_tokens=50_000, out_tokens=500, by_skill={
            'review-manager': {'input_tokens': 30_000},
            'qa-manager':     {'input_tokens': 20_000},
        })
        report = check_session_budget(session, 'balanced')
        assert report.top_contributor == 'review-manager'
        assert report.top_contributor_in == 30_000
