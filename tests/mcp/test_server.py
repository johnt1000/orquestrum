"""Tests for orquestrum.mcp.server — the orq_* MCP tools.

The tools are decorated with `@mcp.tool` but FastMCP preserves the
underlying function, so we call them directly. Project resolution
(`paths.find_project_root`, `registry.load_registry`) is monkeypatched
to point at fixture directories.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.lib import paths, registry
from orquestrum.lib.metrics import append_event, now_iso
from orquestrum.mcp import server


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def project_with_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Project root with .orquestrum/metrics/ and a few seeded events."""
    root = tmp_path / 'sample-project'
    metrics = root / '.orquestrum' / 'metrics'
    metrics.mkdir(parents=True)
    events = metrics / 'events.jsonl'

    # 3 llm_call events from different agents/tiers
    seed_events = [
        {
            'ts': '2026-05-03T10:00:00Z', 'kind': 'llm_call',
            'agent': 'Helm - The Architect', 'skill': '(no-skill)',
            'tier': 'deep', 'model': 'anthropic/claude-opus-4-7',
            'in_tokens': 1000, 'out_tokens': 500,
            'cached_tokens': 0, 'cost_usd': 0.05,
        },
        {
            'ts': '2026-05-03T10:01:00Z', 'kind': 'llm_call',
            'agent': 'Forge - Dev Lead', 'skill': 'task-manager',
            'tier': 'balanced', 'model': 'anthropic/claude-sonnet-4-6',
            'in_tokens': 2000, 'out_tokens': 800,
            'cached_tokens': 500, 'cost_usd': 0.018,
        },
        {
            'ts': '2026-05-03T10:02:00Z', 'kind': 'skill_completion',
            'agent': 'Forge - Dev Lead', 'skill': 'task-manager',
            'status': 'completed',
            'gates_passed': 2, 'gates_failed': 0,
        },
    ]
    for e in seed_events:
        append_event(events, e)

    # Pin find_project_root to this root, regardless of cwd
    monkeypatch.setattr(paths, 'find_project_root', lambda *a, **kw: root)
    return root


@pytest.fixture()
def empty_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Project with .orquestrum/ but no events.jsonl yet."""
    root = tmp_path / 'fresh-project'
    (root / '.orquestrum' / 'metrics').mkdir(parents=True)
    monkeypatch.setattr(paths, 'find_project_root', lambda *a, **kw: root)
    return root


@pytest.fixture()
def no_project(monkeypatch: pytest.MonkeyPatch):
    """Cwd is outside any orquestrum project."""
    monkeypatch.setattr(paths, 'find_project_root', lambda *a, **kw: None)


@pytest.fixture()
def isolated_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sandbox ORQUESTRUM_HOME so registry writes go to tmp."""
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    return home


# ─── orq_record_event ───────────────────────────────────────────────────────


class TestRecordEvent:
    def test_appends_event_to_events_jsonl(self, project_with_metrics: Path):
        result = server.orq_record_event(
            agent='Forge - Dev Lead',
            model='anthropic/claude-sonnet-4-6',
            in_tokens=100, out_tokens=50,
            skill='task-manager', tier='balanced',
        )
        assert result['ok'] is True
        assert 'written_event' in result
        # File grew by one line
        events_path = project_with_metrics / '.orquestrum' / 'metrics' / 'events.jsonl'
        lines = events_path.read_text().strip().splitlines()
        assert len(lines) == 4  # 3 seeded + 1 new
        last = json.loads(lines[-1])
        assert last['agent'] == 'Forge - Dev Lead'
        assert last['source'] == 'mcp'  # distinguishes from hook events
        assert last['cost_usd'] > 0  # estimate_cost ran

    def test_rejects_invalid_tier(self, project_with_metrics: Path):
        result = server.orq_record_event(
            agent='X', model='foo', in_tokens=1, out_tokens=1, tier='bogus',
        )
        assert result['ok'] is False
        assert 'tier' in result['error'].lower()

    def test_rejects_negative_tokens(self, project_with_metrics: Path):
        result = server.orq_record_event(
            agent='X', model='foo', in_tokens=-1, out_tokens=1,
        )
        assert result['ok'] is False
        assert 'in_tokens' in result['error']

    def test_returns_actionable_error_when_no_project(self, no_project):
        result = server.orq_record_event(
            agent='X', model='foo', in_tokens=1, out_tokens=1,
        )
        assert result['ok'] is False
        assert 'orquestrum init' in result['error']


# ─── orq_skill_completed ────────────────────────────────────────────────────


class TestSkillCompleted:
    def test_appends_skill_completion(self, project_with_metrics: Path):
        result = server.orq_skill_completed(
            skill='spec-manager',
            agent='Lore - Product Strategist',
            status='completed',
            gates_passed=3,
            gates_failed=0,
            artifacts_emitted=['spec-v1.md'],
            confidence_avg=0.92,
        )
        assert result['ok'] is True
        assert result['written_event']['kind'] == 'skill_completion'
        assert result['written_event']['confidence_avg'] == 0.92
        assert result['written_event']['artifacts_emitted'] == ['spec-v1.md']

    def test_rejects_invalid_status(self, project_with_metrics: Path):
        result = server.orq_skill_completed(
            skill='X', agent='Y', status='bogus',
        )
        assert result['ok'] is False

    def test_rejects_confidence_out_of_range(self, project_with_metrics: Path):
        result = server.orq_skill_completed(
            skill='X', agent='Y', status='completed', confidence_avg=1.5,
        )
        assert result['ok'] is False
        assert 'confidence_avg' in result['error']


# ─── orq_session_summary ────────────────────────────────────────────────────


class TestSessionSummary:
    def test_aggregates_seeded_events(self, project_with_metrics: Path):
        result = server.orq_session_summary()
        assert result['ok'] is True
        totals = result['totals']
        # 2 llm_calls from the seed
        assert totals['calls'] == 2
        assert totals['skill_calls'] == 1
        assert totals['input_tokens'] == 3000   # 1000 + 2000
        assert totals['output_tokens'] == 1300  # 500 + 800
        assert round(totals['cost_usd'], 3) == 0.068

    def test_empty_project_returns_zeros(self, empty_project: Path):
        result = server.orq_session_summary()
        assert result['ok'] is True
        assert result['totals']['calls'] == 0
        assert result['totals']['cost_usd'] == 0.0

    def test_no_project_returns_actionable_error(self, no_project):
        result = server.orq_session_summary()
        assert result['ok'] is False
        assert 'orquestrum init' in result['error']


# ─── orq_budget_status ──────────────────────────────────────────────────────


class TestBudgetStatus:
    def test_returns_thresholds_and_pct(self, project_with_metrics: Path):
        result = server.orq_budget_status(tier='balanced')
        assert result['ok'] is True
        assert result['tier'] == 'balanced'
        assert result['input_threshold'] == 100_000
        assert result['output_threshold'] == 8_000
        # 3000 / 100000 = 0.03
        assert result['pct_input'] == 0.03
        assert result['over_input'] is False

    def test_rejects_unknown_tier_for_budget(self, project_with_metrics: Path):
        result = server.orq_budget_status(tier='unknown')
        assert result['ok'] is False
        assert 'unknown' in result['error'].lower()

    def test_rejects_invalid_tier(self, project_with_metrics: Path):
        result = server.orq_budget_status(tier='foo')
        assert result['ok'] is False


# ─── orq_recent_events ──────────────────────────────────────────────────────


class TestRecentEvents:
    def test_returns_all_when_no_filter(self, project_with_metrics: Path):
        result = server.orq_recent_events()
        assert result['ok'] is True
        assert result['count'] == 3

    def test_filter_by_kind(self, project_with_metrics: Path):
        result = server.orq_recent_events(kind='skill_completion')
        assert result['count'] == 1
        assert result['events'][0]['kind'] == 'skill_completion'

    def test_filter_by_agent(self, project_with_metrics: Path):
        result = server.orq_recent_events(agent='Forge - Dev Lead')
        assert result['count'] == 2

    def test_since_iso_excludes_older(self, project_with_metrics: Path):
        result = server.orq_recent_events(since_iso='2026-05-03T10:00:30Z')
        # excludes the 10:00:00 event, keeps 10:01:00 and 10:02:00
        assert result['count'] == 2

    def test_limit_caps_results(self, project_with_metrics: Path):
        result = server.orq_recent_events(limit=1)
        assert result['count'] == 1

    def test_results_sorted_descending(self, project_with_metrics: Path):
        result = server.orq_recent_events()
        timestamps = [e['ts'] for e in result['events']]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_limit_validation(self, project_with_metrics: Path):
        result = server.orq_recent_events(limit=0)
        assert result['ok'] is False


# ─── orq_list_projects ──────────────────────────────────────────────────────


class TestListProjects:
    def test_empty_registry_returns_empty(
        self, isolated_registry: Path,
    ):
        result = server.orq_list_projects()
        assert result['ok'] is True
        assert result['count'] == 0
        assert result['projects'] == []

    def test_lists_registered_projects_with_summary(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics,
                                  tool='claude-code')
        result = server.orq_list_projects()
        assert result['count'] == 1
        proj = result['projects'][0]
        assert proj['name'] == 'alpha'
        assert proj['total_calls'] == 2
        assert proj['total_cost_usd'] == 0.068
        assert proj['path_exists'] is True

    def test_marks_ghost_paths(
        self, isolated_registry: Path, tmp_path: Path,
    ):
        ghost = tmp_path / 'ghost'
        ghost.mkdir()
        registry.register_project(name='ghost', path=ghost)
        ghost.rmdir()
        result = server.orq_list_projects()
        proj = next(p for p in result['projects'] if p['name'] == 'ghost')
        assert proj['path_exists'] is False
        assert proj['total_calls'] == 0


# ─── orq_project_summary ────────────────────────────────────────────────────


class TestProjectSummary:
    def test_summary_for_named_project(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics)
        result = server.orq_project_summary(project='alpha')
        assert result['ok'] is True
        assert result['totals']['calls'] == 2

    def test_unknown_project_actionable_error(self, isolated_registry: Path):
        result = server.orq_project_summary(project='nonexistent')
        assert result['ok'] is False
        assert 'registry' in result['error'].lower()


# ─── orq_cost_today ─────────────────────────────────────────────────────────


class TestCostToday:
    def test_explicit_date_sums_correctly(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics)
        result = server.orq_cost_today(date_iso='2026-05-03')
        assert result['ok'] is True
        assert result['date'] == '2026-05-03'
        assert round(result['total_cost_usd'], 3) == 0.068
        assert result['total_calls'] == 2
        assert len(result['per_project']) == 1

    def test_different_date_returns_zero(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics)
        result = server.orq_cost_today(date_iso='2025-01-01')
        assert result['total_cost_usd'] == 0.0
        assert result['total_calls'] == 0

    def test_scoped_to_single_project(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics)
        result = server.orq_cost_today(project='alpha', date_iso='2026-05-03')
        assert result['ok'] is True
        assert len(result['per_project']) == 1


# ─── resources ──────────────────────────────────────────────────────────────


class TestResources:
    def test_session_resource_returns_json(self, project_with_metrics: Path):
        result = server._resource_current_session()
        data = json.loads(result)
        assert 'totals' in data
        assert data['totals']['calls'] == 2

    def test_session_resource_when_no_project(self, no_project):
        result = server._resource_current_session()
        data = json.loads(result)
        assert data['project'] is None
        assert 'message' in data

    def test_projects_resource(
        self, isolated_registry: Path, project_with_metrics: Path,
    ):
        registry.register_project(name='alpha', path=project_with_metrics)
        result = server._resource_projects()
        data = json.loads(result)
        assert data['count'] == 1
        assert data['projects'][0]['name'] == 'alpha'


# ─── helpers ────────────────────────────────────────────────────────────────


class TestEstimateCostSafe:
    def test_returns_zero_for_unknown_model(self):
        cost = server._estimate_cost_safe('unknown-model', 1000, 500)
        assert cost == 0.0

    def test_computes_for_known_model(self):
        cost = server._estimate_cost_safe('anthropic/claude-sonnet-4-6',
                                          10_000, 5_000)
        # sonnet-4-6: input $3/1M, output $15/1M
        # 10000 * 3/1M + 5000 * 15/1M = 0.03 + 0.075 = 0.105
        assert round(cost, 3) == 0.105


class TestServerMetadata:
    def test_server_has_8_tools(self):
        # Sanity: every planned tool registered
        tool_names = sorted(t.name for t in server.mcp._tool_manager.list_tools())
        assert tool_names == [
            'orq_budget_status',
            'orq_cost_today',
            'orq_list_projects',
            'orq_project_summary',
            'orq_recent_events',
            'orq_record_event',
            'orq_session_summary',
            'orq_skill_completed',
        ]
