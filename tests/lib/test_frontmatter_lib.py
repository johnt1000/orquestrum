"""Tests for orquestrum.lib.frontmatter (parse_agent, parse_skill)."""
import textwrap
import pytest
from pathlib import Path
from orquestrum.lib.frontmatter import parse_agent, parse_skill, AgentConfig, SkillConfig


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding='utf-8')
    return p


class TestParseAgent:
    def test_parses_required_fields(self, tmp_agent: Path):
        agent = parse_agent(tmp_agent)
        assert isinstance(agent, AgentConfig)
        assert agent.name == 'Test Agent'
        assert agent.description == 'A test agent for unit testing.'

    def test_mode_parsed(self, tmp_agent: Path):
        assert parse_agent(tmp_agent).mode == 'primary'

    def test_temperature_as_float(self, tmp_agent: Path):
        assert parse_agent(tmp_agent).temperature == pytest.approx(0.2)

    def test_max_tokens_parsed(self, tmp_agent: Path):
        assert parse_agent(tmp_agent).max_tokens == 4096

    def test_tools_parsed(self, tmp_agent: Path):
        agent = parse_agent(tmp_agent)
        assert agent.write is True
        assert agent.edit is True
        assert agent.bash is False

    def test_body_non_empty(self, tmp_agent: Path):
        assert parse_agent(tmp_agent).body.strip() != ''

    def test_missing_max_tokens_returns_none(self, tmp_path: Path):
        f = _write(tmp_path, 'agent.md', """\
            ---
            name: Minimal
            description: No max_tokens.
            mode: agent
            temperature: 0.1
            emoji: 🔧
            tools:
              write: false
              edit: false
              bash: false
              question: false
            ---
            Body.
        """)
        agent = parse_agent(f)
        assert agent.max_tokens is None


class TestParseSkill:
    def test_parses_required_fields(self, tmp_skill: Path):
        skill = parse_skill(tmp_skill)
        assert isinstance(skill, SkillConfig)
        assert skill.name == 'test-skill'

    def test_inject_refs_default_false(self, tmp_skill: Path):
        assert parse_skill(tmp_skill).inject_refs == 'false'

    def test_chain_next_none_when_absent(self, tmp_skill: Path):
        assert parse_skill(tmp_skill).chain_next is None

    def test_depends_on_list(self, tmp_path: Path):
        f = _write(tmp_path, 'SKILL.md', """\
            ---
            name: chained-skill
            description: Has deps.
            depends_on: [skill-a, skill-b]
            ---
            Body.
        """)
        skill = parse_skill(f)
        assert skill.depends_on == ['skill-a', 'skill-b']

    def test_depends_on_comma_string(self, tmp_path: Path):
        f = _write(tmp_path, 'SKILL.md', """\
            ---
            name: chained-skill
            description: Has deps.
            depends_on: "skill-a, skill-b"
            ---
            Body.
        """)
        skill = parse_skill(f)
        assert skill.depends_on == ['skill-a', 'skill-b']

    def test_chain_next_parsed(self, tmp_path: Path):
        f = _write(tmp_path, 'SKILL.md', """\
            ---
            name: chained-skill
            description: Has chain.
            chain:
              next: other-skill
            ---
            Body.
        """)
        skill = parse_skill(f)
        assert skill.chain_next == 'other-skill'
