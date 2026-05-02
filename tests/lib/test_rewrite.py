"""Tests for orquestrum.lib.rewrite."""
import textwrap
import pytest
from pathlib import Path
from orquestrum.lib.rewrite import (
    name_to_kebab,
    rewrite_paths,
    extract_inject_blocks,
    skill_reference_content,
)


class TestNameToKebab:
    def test_helm(self):
        assert name_to_kebab('Helm - The Architect') == 'helm-the-architect'

    def test_cast(self):
        assert name_to_kebab('Cast - Ship Lead') == 'cast-ship-lead'

    def test_forge(self):
        assert name_to_kebab('Forge - Dev Lead') == 'forge-dev-lead'

    def test_em_dash(self):
        assert name_to_kebab('Foo — Bar') == 'foo-bar'

    def test_en_dash(self):
        assert name_to_kebab('Foo – Bar') == 'foo-bar'

    def test_ampersand(self):
        assert name_to_kebab('Search & Replace') == 'search-and-replace'

    def test_no_double_dashes(self):
        assert '--' not in name_to_kebab('A  -  B')

    def test_no_leading_or_trailing_dash(self):
        assert not name_to_kebab('- Leading').startswith('-')

    def test_special_chars_removed(self):
        result = name_to_kebab('Hello! World?')
        assert '!' not in result
        assert '?' not in result

    def test_all_agents_produce_valid_slug(self):
        agents = [
            'Helm - The Architect', 'Lore - Product Strategist', 'Forge - Dev Lead',
            'Cipher - Security Lead', 'Ward - Quality Lead', 'Cast - Ship Lead',
            'Flux - Support Lead', 'Trace - Onboarding Lead',
        ]
        for name in agents:
            slug = name_to_kebab(name)
            assert slug and slug == slug.lower()
            assert not slug.startswith('-') and not slug.endswith('-')
            assert '--' not in slug


class TestRewritePaths:
    def test_rewrites_docs_path(self):
        content = 'See docs/agent-context/SDLC.md for details.'
        result = rewrite_paths(content, docs_prefix='.sdd/docs', skills_prefix='.sdd/skills')
        assert '.sdd/docs/agent-context/SDLC.md' in result

    def test_rewrites_skills_path(self):
        content = 'Read skills/task-manager/SKILL.md'
        result = rewrite_paths(content, docs_prefix='.sdd/docs', skills_prefix='.sdd/skills')
        assert '.sdd/skills/task-manager/SKILL.md' in result

    def test_rewrites_skill_assets(self):
        content = 'Use skills/task-manager/assets/task-template.md'
        result = rewrite_paths(content, docs_prefix='.sdd/docs', skills_prefix='.sdd/skills')
        assert '.sdd/skills/task-manager/assets/' in result

    def test_rewrites_governance_doc(self):
        content = 'See docs/governance/MODELS.md'
        result = rewrite_paths(content, docs_prefix='.sdd/docs', skills_prefix='.sdd/skills')
        assert '.sdd/docs/governance/MODELS.md' in result

    def test_no_change_when_no_patterns_match(self):
        content = 'Nothing to rewrite here.'
        assert rewrite_paths(content, '.sdd/docs', '.sdd/skills') == content

    def test_opencode_prefix(self):
        content = 'See docs/agent-context/CONVENTIONS.md'
        result = rewrite_paths(content, '__OPENCODE_ROOT__/docs', '__OPENCODE_ROOT__/skills')
        assert '__OPENCODE_ROOT__/docs/agent-context/CONVENTIONS.md' in result


class TestExtractInjectBlocks:
    def test_extracts_single_block(self):
        content = 'before\n<!-- inject:start -->\nmy content\n<!-- inject:end -->\nafter'
        result = extract_inject_blocks(content)
        assert 'my content' in result
        assert 'before' not in result

    def test_extracts_multiple_blocks(self):
        content = (
            '<!-- inject:start -->block one<!-- inject:end -->'
            '\n\n'
            '<!-- inject:start -->block two<!-- inject:end -->'
        )
        result = extract_inject_blocks(content)
        assert 'block one' in result
        assert 'block two' in result

    def test_no_blocks_returns_empty(self):
        assert extract_inject_blocks('no markers here') == ''

    def test_multiline_block(self):
        content = '<!-- inject:start -->\nline 1\nline 2\n<!-- inject:end -->'
        result = extract_inject_blocks(content)
        assert 'line 1' in result and 'line 2' in result


class TestSkillReferenceContent:
    def _write_skill(self, skill_dir: Path, inject_refs: str = 'false',
                     inject_fewshot: str = 'false') -> None:
        fm = textwrap.dedent(f"""\
            ---
            name: test-skill
            description: Test skill.
            inject_references: {inject_refs}
            inject_fewshot: {inject_fewshot}
            ---
            Body.
        """)
        (skill_dir / 'SKILL.md').write_text(fm, encoding='utf-8')

    def test_missing_skill_file_returns_empty(self, tmp_path: Path):
        result = skill_reference_content(tmp_path / 'no-skill')
        assert result == ''

    def test_inject_refs_false_returns_empty(self, tmp_path: Path):
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        self._write_skill(skill_dir, inject_refs='false')
        result = skill_reference_content(skill_dir)
        assert result == ''

    def test_inject_refs_full_includes_references(self, tmp_path: Path):
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir()
        (refs_dir / 'my-references.md').write_text('## Refs\nsome reference', encoding='utf-8')
        self._write_skill(skill_dir, inject_refs='full')
        result = skill_reference_content(skill_dir)
        assert 'Reference Knowledge' in result
        assert 'some reference' in result

    def test_inject_refs_compact_extracts_inject_blocks(self, tmp_path: Path):
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir()
        (refs_dir / 'my-references.md').write_text(
            'preamble\n<!-- inject:start -->\ncompact content\n<!-- inject:end -->\npostamble',
            encoding='utf-8',
        )
        self._write_skill(skill_dir, inject_refs='compact')
        result = skill_reference_content(skill_dir)
        assert 'compact content' in result
        assert 'preamble' not in result

    def test_inject_fewshot_includes_examples(self, tmp_path: Path):
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir()
        (refs_dir / 'my-fewshot.md').write_text('## Examples\nexample A', encoding='utf-8')
        self._write_skill(skill_dir, inject_fewshot='full')
        result = skill_reference_content(skill_dir)
        assert 'Examples' in result
        assert 'example A' in result

    def test_no_references_dir_returns_empty(self, tmp_path: Path):
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        self._write_skill(skill_dir, inject_refs='full')
        # No references/ dir at all
        result = skill_reference_content(skill_dir)
        assert result == ''
