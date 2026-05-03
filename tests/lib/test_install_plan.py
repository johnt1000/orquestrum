"""Tests for orquestrum.lib.install_plan — pre-flight install classifier."""
from __future__ import annotations
from pathlib import Path

import pytest

from orquestrum.lib import install_plan


# ─── detect_user_owned_files ────────────────────────────────────────────────


class TestDetectUserOwnedFiles:
    def test_returns_empty_when_no_files_present(self, tmp_path: Path):
        target = tmp_path / 'fresh-project'
        target.mkdir()
        assert install_plan.detect_user_owned_files('aider', target) == []
        assert install_plan.detect_user_owned_files('windsurf', target) == []

    def test_aider_user_conventions_md_detected(self, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        # User's own CONVENTIONS.md (no orquestrum marker)
        (target / 'CONVENTIONS.md').write_text(
            '# My project conventions\nUse 2-space indentation.\n',
            encoding='utf-8',
        )
        result = install_plan.detect_user_owned_files('aider', target)
        assert len(result) == 1
        assert result[0].name == 'CONVENTIONS.md'

    def test_aider_orquestrum_conventions_md_not_flagged(self, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        # Orquestrum-generated CONVENTIONS.md (has marker)
        (target / 'CONVENTIONS.md').write_text(
            '# Orquestrum — Agent Conventions\n\n> Auto-generated.\n',
            encoding='utf-8',
        )
        assert install_plan.detect_user_owned_files('aider', target) == []

    def test_windsurf_user_windsurfrules_detected(self, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        (target / '.windsurfrules').write_text(
            'My personal windsurf rules\nrule 1\nrule 2\n', encoding='utf-8',
        )
        result = install_plan.detect_user_owned_files('windsurf', target)
        assert len(result) == 1
        assert result[0].name == '.windsurfrules'

    def test_windsurf_orquestrum_windsurfrules_not_flagged(self, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        (target / '.windsurfrules').write_text(
            '# Orquestrum — Agent Rules\n\n> Auto-generated.\n',
            encoding='utf-8',
        )
        assert install_plan.detect_user_owned_files('windsurf', target) == []

    def test_other_tools_have_no_single_owner_files(self, tmp_path: Path):
        target = tmp_path / 'project'
        target.mkdir()
        # claude-code, opencode, cursor have no single-owner conflict files
        # because their content lives in dedicated subdirs.
        for tool in ('claude-code', 'opencode', 'cursor'):
            assert install_plan.detect_user_owned_files(tool, target) == []

    def test_unknown_tool_returns_empty(self, tmp_path: Path):
        assert install_plan.detect_user_owned_files('made-up', tmp_path) == []


# ─── classify_install ───────────────────────────────────────────────────────


class TestClassifyInstall:
    def test_all_new_when_target_empty(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        (src / 'sub').mkdir(parents=True)
        target.mkdir()
        (src / 'a.md').write_text('hello', encoding='utf-8')
        (src / 'sub' / 'b.md').write_text('world', encoding='utf-8')
        plan = install_plan.classify_install(src, target)
        assert len(plan.new) == 2
        assert plan.update == []
        assert plan.unchanged == []

    def test_unchanged_for_identical_content(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        src.mkdir()
        target.mkdir()
        (src / 'a.md').write_text('hello', encoding='utf-8')
        (target / 'a.md').write_text('hello', encoding='utf-8')
        plan = install_plan.classify_install(src, target)
        assert plan.new == []
        assert plan.unchanged == [target / 'a.md']

    def test_update_for_different_content(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        src.mkdir()
        target.mkdir()
        (src / 'a.md').write_text('new version', encoding='utf-8')
        (target / 'a.md').write_text('old version', encoding='utf-8')
        plan = install_plan.classify_install(src, target)
        assert plan.update == [target / 'a.md']

    def test_mixed_classification(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        src.mkdir()
        target.mkdir()
        # 1 new, 1 unchanged, 1 update
        (src / 'new.md').write_text('new', encoding='utf-8')
        (src / 'same.md').write_text('same', encoding='utf-8')
        (src / 'changed.md').write_text('v2', encoding='utf-8')
        (target / 'same.md').write_text('same', encoding='utf-8')
        (target / 'changed.md').write_text('v1', encoding='utf-8')
        plan = install_plan.classify_install(src, target)
        assert len(plan.new) == 1
        assert len(plan.unchanged) == 1
        assert len(plan.update) == 1
        assert plan.total == 3

    def test_ignore_filenames_skipped(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        src.mkdir()
        target.mkdir()
        (src / 'a.md').write_text('a', encoding='utf-8')
        (src / 'settings.json').write_text('{}', encoding='utf-8')
        plan = install_plan.classify_install(src, target,
                                             ignore_filenames={'settings.json'})
        # Only a.md should be classified
        assert len(plan.new) == 1
        assert plan.new[0].name == 'a.md'

    def test_recurses_into_subdirs(self, tmp_path: Path):
        src = tmp_path / 'src'
        target = tmp_path / 'target'
        (src / 'deep' / 'tree').mkdir(parents=True)
        target.mkdir()
        (src / 'deep' / 'tree' / 'leaf.md').write_text('x', encoding='utf-8')
        plan = install_plan.classify_install(src, target)
        assert len(plan.new) == 1
        assert plan.new[0] == target / 'deep' / 'tree' / 'leaf.md'

    def test_missing_src_returns_empty_plan(self, tmp_path: Path):
        plan = install_plan.classify_install(tmp_path / 'nope', tmp_path / 'tgt')
        assert plan.total == 0


# ─── InstallPlan rendering ──────────────────────────────────────────────────


class TestPlanRender:
    def test_empty_plan_renders_nothing_to_do(self):
        plan = install_plan.InstallPlan()
        assert 'nothing to do' in plan.render()

    def test_render_lists_each_category(self, tmp_path: Path):
        plan = install_plan.InstallPlan(
            new=[tmp_path / 'a'],
            update=[tmp_path / 'b'],
            unchanged=[tmp_path / 'c'],
            user_owned=[tmp_path / 'd'],
        )
        rendered = plan.render()
        assert '1 new' in rendered
        assert '1 update' in rendered
        assert '1 unchanged' in rendered
        assert '1 conflict' in rendered

    def test_user_owned_paths_listed_individually(self, tmp_path: Path):
        plan = install_plan.InstallPlan(
            user_owned=[tmp_path / 'CONVENTIONS.md'],
        )
        rendered = plan.render()
        assert 'CONVENTIONS.md' in rendered


class TestPlanProperties:
    def test_has_conflicts_true_when_user_owned_present(self):
        plan = install_plan.InstallPlan(user_owned=[Path('/x')])
        assert plan.has_conflicts is True

    def test_has_conflicts_false_when_only_safe_changes(self):
        plan = install_plan.InstallPlan(new=[Path('/a')], update=[Path('/b')])
        assert plan.has_conflicts is False


# ─── Error rendering ────────────────────────────────────────────────────────


class TestRenderUserConflictError:
    def test_includes_each_path_and_resolution_options(self, tmp_path: Path):
        conflicts = [tmp_path / 'CONVENTIONS.md']
        msg = install_plan.render_user_conflict_error('aider', conflicts)
        assert 'CONVENTIONS.md' in msg
        assert '--force' in msg
        assert 'rename' in msg.lower()
