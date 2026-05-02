"""Tests for ui.lib.edit_validator."""
import pytest
from ui.lib.edit_validator import (
    validate_agent_frontmatter,
    validate_skill_frontmatter,
    errors_by_field,
    diff_frontmatter,
    MAX_TOKENS_CEILING,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

VALID_AGENT_FM = {
    'name': 'My Agent',
    'description': 'Does things.',
    'mode': 'primary',
    'temperature': 0.2,
    'emoji': '🤖',
    'max_tokens': 4096,
    'tools': {'write': True, 'edit': True, 'bash': False, 'question': True},
}

VALID_SKILL_FM = {
    'name': 'my-skill',
    'description': 'Does skill things.',
}


# ─── Agent validation ─────────────────────────────────────────────────────────

class TestValidateAgentFrontmatter:
    def test_valid_returns_empty(self):
        assert validate_agent_frontmatter(VALID_AGENT_FM) == []

    def test_missing_name(self):
        fm = {**VALID_AGENT_FM}
        del fm['name']
        errors = validate_agent_frontmatter(fm)
        assert any('name' in e for e in errors)

    def test_empty_name(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'name': '   '})
        assert any('name' in e for e in errors)

    def test_missing_description(self):
        fm = {**VALID_AGENT_FM}
        del fm['description']
        errors = validate_agent_frontmatter(fm)
        assert any('description' in e for e in errors)

    def test_invalid_mode(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'mode': 'flying'})
        assert any('mode' in e for e in errors)

    def test_valid_modes(self):
        for mode in ('primary', 'agent', 'subagent'):
            errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'mode': mode})
            assert errors == []

    def test_temperature_out_of_range(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'temperature': 3.0})
        assert any('temperature' in e for e in errors)

    def test_temperature_non_numeric(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'temperature': 'hot'})
        assert any('temperature' in e for e in errors)

    def test_max_tokens_missing(self):
        fm = {**VALID_AGENT_FM}
        del fm['max_tokens']
        errors = validate_agent_frontmatter(fm)
        assert any('max_tokens' in e for e in errors)

    def test_max_tokens_zero(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'max_tokens': 0})
        assert any('max_tokens' in e for e in errors)

    def test_max_tokens_exceeds_ceiling(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'max_tokens': MAX_TOKENS_CEILING + 1})
        assert any('max_tokens' in e for e in errors)

    def test_max_tokens_bool_rejected(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'max_tokens': True})
        assert any('max_tokens' in e for e in errors)

    def test_missing_emoji(self):
        fm = {**VALID_AGENT_FM}
        del fm['emoji']
        errors = validate_agent_frontmatter(fm)
        assert any('emoji' in e for e in errors)

    def test_tools_not_dict(self):
        errors = validate_agent_frontmatter({**VALID_AGENT_FM, 'tools': 'all'})
        assert any('tools' in e for e in errors)

    def test_tools_missing_key(self):
        fm = {**VALID_AGENT_FM, 'tools': {'write': True, 'edit': True, 'bash': False}}
        errors = validate_agent_frontmatter(fm)
        assert any('tools.question' in e for e in errors)

    def test_tools_non_bool_value(self):
        fm = {**VALID_AGENT_FM, 'tools': {**VALID_AGENT_FM['tools'], 'bash': 'yes'}}
        errors = validate_agent_frontmatter(fm)
        assert any('tools.bash' in e for e in errors)


# ─── Skill validation ─────────────────────────────────────────────────────────

class TestValidateSkillFrontmatter:
    def test_valid_returns_empty(self):
        assert validate_skill_frontmatter(VALID_SKILL_FM, []) == []

    def test_missing_name(self):
        errors = validate_skill_frontmatter({'description': 'x'}, [])
        assert any('name' in e for e in errors)

    def test_invalid_inject_references(self):
        fm = {**VALID_SKILL_FM, 'inject_references': 'maybe'}
        errors = validate_skill_frontmatter(fm, [])
        assert any('inject_references' in e for e in errors)

    def test_valid_inject_values(self):
        for val in ('false', 'full', 'compact'):
            errors = validate_skill_frontmatter({**VALID_SKILL_FM, 'inject_references': val}, [])
            assert errors == []

    def test_emits_confidence_non_bool(self):
        fm = {**VALID_SKILL_FM, 'emits_confidence': 'yes'}
        errors = validate_skill_frontmatter(fm, [])
        assert any('emits_confidence' in e for e in errors)

    def test_chain_next_not_in_skills(self):
        fm = {**VALID_SKILL_FM, 'chain': {'next': 'nonexistent-skill'}}
        errors = validate_skill_frontmatter(fm, skills_dir_existing=['other-skill'])
        assert any('chain.next' in e for e in errors)

    def test_chain_next_valid_when_in_skills(self):
        fm = {**VALID_SKILL_FM, 'chain': {'next': 'real-skill'}}
        errors = validate_skill_frontmatter(fm, skills_dir_existing=['real-skill'])
        assert errors == []

    def test_depends_on_unknown_skill(self):
        fm = {**VALID_SKILL_FM, 'depends_on': ['ghost-skill']}
        errors = validate_skill_frontmatter(fm, skills_dir_existing=[])
        assert any('depends_on' in e for e in errors)


# ─── errors_by_field ──────────────────────────────────────────────────────────

class TestErrorsByField:
    def test_field_colon_pattern(self):
        grouped = errors_by_field(['mode: must be one of [...]'])
        assert 'mode' in grouped

    def test_missing_required_pattern(self):
        grouped = errors_by_field(["missing required field: 'name'"])
        assert 'name' in grouped
        assert grouped['name'] == ['required field is missing']

    def test_global_bucket_for_unrecognized(self):
        grouped = errors_by_field(['something went wrong'])
        assert '_global' in grouped

    def test_multi_word_head_goes_to_global(self):
        # "tools.write" has a dot but no space; "missing tools write" has space → global
        grouped = errors_by_field(['missing tools write'])
        assert '_global' in grouped

    def test_tools_dot_key_stays_as_field(self):
        grouped = errors_by_field(['tools.bash: must be boolean'])
        assert 'tools.bash' in grouped

    def test_empty_input_returns_empty(self):
        assert errors_by_field([]) == {}


# ─── diff_frontmatter ─────────────────────────────────────────────────────────

class TestDiffFrontmatter:
    def test_no_changes_returns_empty(self):
        fm = {'name': 'A', 'mode': 'primary'}
        assert diff_frontmatter(fm, fm) == []

    def test_detects_scalar_change(self):
        old = {'name': 'Old', 'mode': 'primary'}
        new = {'name': 'New', 'mode': 'primary'}
        changes = diff_frontmatter(old, new)
        assert len(changes) == 1
        assert changes[0] == ('name', 'Old', 'New')

    def test_detects_added_key(self):
        changes = diff_frontmatter({'a': 1}, {'a': 1, 'b': 2})
        assert any(k == 'b' for k, _, _ in changes)

    def test_detects_removed_key(self):
        changes = diff_frontmatter({'a': 1, 'b': 2}, {'a': 1})
        assert any(k == 'b' for k, _, _ in changes)

    def test_tools_expanded_to_dotted_keys(self):
        old = {'tools': {'write': True, 'bash': False}}
        new = {'tools': {'write': True, 'bash': True}}
        changes = diff_frontmatter(old, new)
        assert any(k == 'tools.bash' for k, _, _ in changes)

    def test_chain_expanded_to_dotted_keys(self):
        old = {'chain': {'next': 'skill-a'}}
        new = {'chain': {'next': 'skill-b'}}
        changes = diff_frontmatter(old, new)
        assert any(k == 'chain.next' for k, _, _ in changes)
