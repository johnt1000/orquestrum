"""Tests for orquestrum.lib.metrics (append_event, read_events)."""
import json
import pytest
from pathlib import Path
from orquestrum.lib.metrics import append_event, read_events, now_iso


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
        lines = events.read_text().splitlines()
        assert len(lines) == 3

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
        events = tmp_path / 'no_events.jsonl'
        assert read_events(events) == []

    def test_reads_back_appended_events(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        append_event(events, {'kind': 'a'})
        append_event(events, {'kind': 'b'})
        result = read_events(events)
        assert len(result) == 2
        assert result[0]['kind'] == 'a'
        assert result[1]['kind'] == 'b'

    def test_skips_blank_lines(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        events.write_text('{"k":1}\n\n{"k":2}\n', encoding='utf-8')
        result = read_events(events)
        assert len(result) == 2

    def test_skips_invalid_json_lines(self, tmp_path: Path):
        events = tmp_path / 'events.jsonl'
        events.write_text('{"k":1}\nnot json\n{"k":2}\n', encoding='utf-8')
        result = read_events(events)
        assert len(result) == 2
