"""Tests for ui.lib.catalog_loader."""
import textwrap
import pytest
from pathlib import Path
from ui.lib.catalog_loader import list_agents, list_skills, AgentRow, SkillRow


def _write_agent(directory: Path, name: str = 'Test Agent') -> Path:
    content = textwrap.dedent(f"""\
        ---
        name: {name}
        description: A test agent.
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
        Body content.
    """)
    slug = name.lower().replace(' ', '-').replace('-', '-')
    f = directory / f'{slug}.md'
    f.write_text(content, encoding='utf-8')
    return f


def _write_skill(skills_dir: Path, slug: str = 'test-skill',
                 chain_next: str | None = None) -> Path:
    chain_block = f'chain:\n  next: {chain_next}\n' if chain_next else ''
    content = (
        '---\n'
        f'name: {slug}\n'
        'description: A test skill.\n'
        'inject_references: false\n'
        + chain_block +
        '---\nSkill body.\n'
    )
    d = skills_dir / slug
    d.mkdir(exist_ok=True)
    f = d / 'SKILL.md'
    f.write_text(content, encoding='utf-8')
    return f


class TestListAgents:
    def test_empty_dir_returns_empty(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        assert list_agents(agents_dir) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path):
        assert list_agents(tmp_path / 'no-such-dir') == []

    def test_returns_agent_rows(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        _write_agent(agents_dir, 'Forge - Dev Lead')
        rows = list_agents(agents_dir)
        assert len(rows) == 1
        assert isinstance(rows[0], AgentRow)

    def test_agent_name_parsed(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        _write_agent(agents_dir, 'Forge - Dev Lead')
        assert list_agents(agents_dir)[0].name == 'Forge - Dev Lead'

    def test_agent_slug_computed(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        _write_agent(agents_dir, 'Forge - Dev Lead')
        row = list_agents(agents_dir)[0]
        assert row.slug == 'forge-dev-lead'

    def test_multiple_agents_sorted(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        _write_agent(agents_dir, 'Zebra Agent')
        _write_agent(agents_dir, 'Alpha Agent')
        names = [r.name for r in list_agents(agents_dir)]
        assert names == sorted(names)

    def test_malformed_agent_skipped(self, tmp_path: Path):
        agents_dir = tmp_path / 'agents'
        agents_dir.mkdir()
        (agents_dir / 'bad.md').write_text('not yaml at all: {{{', encoding='utf-8')
        _write_agent(agents_dir, 'Good Agent')
        rows = list_agents(agents_dir)
        assert len(rows) == 1
        assert rows[0].name == 'Good Agent'


class TestListSkills:
    def test_empty_dir_returns_empty(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        assert list_skills(skills_dir) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path):
        assert list_skills(tmp_path / 'no-such-dir') == []

    def test_returns_skill_rows(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        _write_skill(skills_dir, 'my-skill')
        rows = list_skills(skills_dir)
        assert len(rows) == 1
        assert isinstance(rows[0], SkillRow)

    def test_skill_name_and_slug(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        _write_skill(skills_dir, 'task-manager')
        row = list_skills(skills_dir)[0]
        assert row.slug == 'task-manager'
        assert row.name == 'task-manager'

    def test_chain_next_parsed(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        _write_skill(skills_dir, 'spec-manager', chain_next='adr-manager')
        row = list_skills(skills_dir)[0]
        assert row.chain_next == 'adr-manager'

    def test_files_at_skills_root_ignored(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        (skills_dir / 'REGISTRY.md').write_text('# Registry', encoding='utf-8')
        assert list_skills(skills_dir) == []

    def test_dir_without_skill_md_ignored(self, tmp_path: Path):
        skills_dir = tmp_path / 'skills'
        skills_dir.mkdir()
        (skills_dir / 'empty-skill').mkdir()
        assert list_skills(skills_dir) == []
