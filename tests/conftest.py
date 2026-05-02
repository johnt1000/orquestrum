"""Shared pytest fixtures for the Orquestrum test suite."""
from __future__ import annotations
import textwrap
from pathlib import Path
import pytest


MINIMAL_AGENT_FM = textwrap.dedent("""\
    ---
    name: Test Agent
    description: A test agent for unit testing.
    mode: primary
    temperature: 0.2
    emoji: 🤖
    max_tokens: 4096
    tools:
      write: true
      edit: true
      bash: false
      question: true
    ---

    # Body content here.
""")

MINIMAL_SKILL_FM = textwrap.dedent("""\
    ---
    name: test-skill
    description: A test skill for unit testing.
    inject_references: false
    ---

    # Skill body here.
""")


@pytest.fixture()
def tmp_agent(tmp_path: Path) -> Path:
    """Write a minimal valid agent file and return its path."""
    f = tmp_path / 'test-agent.md'
    f.write_text(MINIMAL_AGENT_FM, encoding='utf-8')
    return f


@pytest.fixture()
def tmp_skill(tmp_path: Path) -> Path:
    """Write a minimal valid skill file and return its path."""
    d = tmp_path / 'test-skill'
    d.mkdir()
    f = d / 'SKILL.md'
    f.write_text(MINIMAL_SKILL_FM, encoding='utf-8')
    return f
