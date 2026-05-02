"""Tests for orquestrum.lib.metrics."""
import json
import pytest
from pathlib import Path
from orquestrum.lib.metrics import (
    append_event,
    read_events,
    aggregate,
    update_session,
    rebuild_session,
    SessionAggregate,
    now_iso,
)


class TestNowIso:
    def test_returns_string(self):
        ts = now_iso()
        assert isinstance(ts, str)
        assert 'T' in ts
        assert ts.endswith('Z')


class TestAppendEvent:
    def test_creates_file_and_appends(self, tmp_path: Path):
        events = tmp_path / 'sub' / 'events.jsonl'
        append_event(events, {'kind': 'test', 'value': 1})
        assert events.exists()
        lines = events.read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])['kind'] == 'test'

    def test_appends_multiple_events(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        for i in range(3):
            append_event(events, {'seq': i})
        assert len(events.read_text().splitlines()) == 3

    def test_auto_injects_ts_if_missing(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        append_event(events, {'kind': 'no_ts'})
        data = json.loads(events.read_text().splitlines()[0])
        assert 'ts' in data

    def test_preserves_existing_ts(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        append_event(events, {'ts': '2026-01-01T00:00:00Z', 'kind': 'x'})
        data = json.loads(events.read_text().splitlines()[0])
        assert data['ts'] == '2026-01-01T00:00:00Z'


class TestReadEvents:
    def test_returns_empty_list_when_missing(self, tmp_path: Path):
        assert read_events(tmp_path / 'no_events.jsonl') == []

    def test_reads_back_appended_events(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        append_event(events, {'kind': 'a'})
        append_event(events, {'kind': 'b'})
        result = read_events(events)
        assert len(result) == 2
        assert result[0]['kind'] == 'a'

    def test_skips_blank_lines(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        events.write_text('{"k":1}\n\n{"k":2}\n', encoding='utf-8')
        assert len(read_events(events)) == 2

    def test_skips_invalid_json_lines(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        events.write_text('{"k":1}\nnot json\n{"k":2}\n', encoding='utf-8')
        assert len(read_events(events)) == 2


class TestAggregate:
    def test_empty_events_returns_zero_totals(self):
        sess = aggregate([])
        assert sess.totals['input_tokens'] == 0
        assert sess.totals['calls'] == 0

    def test_llm_call_accumulates_tokens(self):
        ev = {
            'kind': 'llm_call', 'ts': '2026-01-01T00:00:00Z',
            'agent': 'Forge - Dev Lead', 'skill': 'task-manager',
            'in_tokens': 1000, 'out_tokens': 200, 'cached_tokens': 400,
            'cost_usd': 0.005,
        }
        sess = aggregate([ev])
        assert sess.totals['input_tokens'] == 1000
        assert sess.totals['output_tokens'] == 200
        assert sess.totals['cached_tokens'] == 400
        assert sess.totals['calls'] == 1

    def test_multiple_llm_calls_sum_correctly(self):
        events = [
            {'kind': 'llm_call', 'in_tokens': 500, 'out_tokens': 100,
             'cached_tokens': 0, 'cost_usd': 0.001},
            {'kind': 'llm_call', 'in_tokens': 300, 'out_tokens': 50,
             'cached_tokens': 0, 'cost_usd': 0.0005},
        ]
        sess = aggregate(events)
        assert sess.totals['input_tokens'] == 800
        assert sess.totals['calls'] == 2

    def test_by_skill_bucketed(self):
        ev = {
            'kind': 'llm_call', 'skill': 'review-manager',
            'in_tokens': 1000, 'out_tokens': 200, 'cached_tokens': 0, 'cost_usd': 0.0,
        }
        sess = aggregate([ev])
        assert 'review-manager' in sess.by_skill
        assert sess.by_skill['review-manager']['input_tokens'] == 1000

    def test_by_agent_bucketed(self):
        ev = {
            'kind': 'llm_call', 'agent': 'Ward - Quality Lead',
            'in_tokens': 500, 'out_tokens': 100, 'cached_tokens': 0, 'cost_usd': 0.0,
        }
        sess = aggregate([ev])
        assert 'Ward - Quality Lead' in sess.by_agent

    def test_no_skill_uses_fallback_key(self):
        ev = {'kind': 'llm_call', 'in_tokens': 100, 'out_tokens': 10,
              'cached_tokens': 0, 'cost_usd': 0.0}
        sess = aggregate([ev])
        assert '(no-skill)' in sess.by_skill

    def test_skill_completion_increments_skill_calls(self):
        ev = {'kind': 'skill_completion', 'skill': 'qa-manager', 'status': 'completed'}
        sess = aggregate([ev])
        assert sess.totals['skill_calls'] == 1

    def test_skill_completion_failure_tracked(self):
        ev = {'kind': 'skill_completion', 'skill': 'qa-manager', 'status': 'failed'}
        sess = aggregate([ev])
        assert sess.by_skill['qa-manager'].get('failures', 0) == 1

    def test_timestamps_set(self):
        events = [
            {'kind': 'llm_call', 'ts': '2026-01-01T10:00:00Z',
             'in_tokens': 0, 'out_tokens': 0, 'cached_tokens': 0, 'cost_usd': 0.0},
            {'kind': 'llm_call', 'ts': '2026-01-01T12:00:00Z',
             'in_tokens': 0, 'out_tokens': 0, 'cached_tokens': 0, 'cost_usd': 0.0},
        ]
        sess = aggregate(events)
        assert sess.started_at == '2026-01-01T10:00:00Z'
        assert sess.ended_at == '2026-01-01T12:00:00Z'

    def test_tier_stored(self):
        sess = aggregate([], tier='balanced')
        assert sess.tier == 'balanced'

    def test_to_dict_has_all_keys(self):
        sess = aggregate([], tier='deep')
        d = sess.to_dict()
        for key in ('tier', 'started_at', 'ended_at', 'totals', 'by_skill', 'by_agent'):
            assert key in d


class TestUpdateSession:
    def test_writes_json_file(self, tmp_path: Path):
        sess = aggregate([], tier='balanced')
        path = tmp_path / 'session.json'
        update_session(path, sess)
        data = json.loads(path.read_text())
        assert data['tier'] == 'balanced'

    def test_overwrites_existing_file(self, tmp_path: Path):
        path = tmp_path / 'session.json'
        path.write_text('old content', encoding='utf-8')
        sess = aggregate([], tier='mechanical')
        update_session(path, sess)
        data = json.loads(path.read_text())
        assert data['tier'] == 'mechanical'

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / 'deep' / 'nested' / 'session.json'
        update_session(path, aggregate([]))
        assert path.exists()


class TestRebuildSession:
    def test_reads_events_and_writes_session(self, tmp_path: Path):
        metrics_dir = tmp_path / 'metrics'
        metrics_dir.mkdir()
        append_event(metrics_dir / 'events.jsonl', {
            'kind': 'llm_call', 'in_tokens': 500, 'out_tokens': 100,
            'cached_tokens': 0, 'cost_usd': 0.001,
        })
        sess = rebuild_session(metrics_dir, tier='balanced')
        assert sess.totals['input_tokens'] == 500
        assert (metrics_dir / 'session.json').exists()

    def test_empty_metrics_dir_produces_zero_session(self, tmp_path: Path):
        metrics_dir = tmp_path / 'metrics'
        metrics_dir.mkdir()
        sess = rebuild_session(metrics_dir)
        assert sess.totals['calls'] == 0
