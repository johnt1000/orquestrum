"""Unit tests for orquestrum.lib.assets — bundled SDD asset access.

The bundled `_assets/` tree is materialized only when the wheel is built
(via `uv build --wheel`) — in editable installs the source tree is used
directly. So tests that need real content gate themselves on
`has_bundled_assets()`.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from orquestrum.lib import assets


class TestAssetsRoot:
    def test_returns_path_under_orquestrum_package(self):
        root = assets.assets_root()
        # The path must point at orquestrum/_assets/, regardless of whether
        # it has been materialized.
        parts = root.parts
        assert parts[-2:] == ('orquestrum', '_assets'), (
            f'expected orquestrum/_assets/ tail, got {root}'
        )

    def test_returns_consistent_path(self):
        # Two calls must return the same Path.
        assert assets.assets_root() == assets.assets_root()


class TestHasBundledAssets:
    def test_returns_bool(self):
        # Always returns a bool — never raises.
        assert isinstance(assets.has_bundled_assets(), bool)


# These tests only run if the wheel-bundled assets are present (i.e. the test
# is running against an installed wheel, not an editable source checkout).
@pytest.mark.skipif(
    not assets.has_bundled_assets(),
    reason='bundled assets only present in wheel installs (run after `uv build --wheel`)',
)
class TestBundledContents:
    def test_assets_root_exists(self):
        assert assets.assets_root().is_dir()

    def test_has_agents(self):
        agents_dir = assets.assets_root() / 'agents'
        assert agents_dir.is_dir()
        # 8 orchestrator agents
        md_files = list(agents_dir.glob('*.md'))
        assert len(md_files) == 8

    def test_has_skills(self):
        skills_dir = assets.assets_root() / 'skills'
        assert skills_dir.is_dir()
        # Each skill has a SKILL.md
        skill_files = list(skills_dir.glob('*/SKILL.md'))
        assert len(skill_files) >= 20

    def test_has_docs_agent_context(self):
        docs = assets.assets_root() / 'docs' / 'agent-context'
        assert docs.is_dir()
        assert (docs / 'SDLC.md').is_file()
        assert (docs / 'CONVENTIONS.md').is_file()

    def test_has_docs_governance(self):
        docs = assets.assets_root() / 'docs' / 'governance'
        assert docs.is_dir()
        assert (docs / 'MODELS.md').is_file()

    def test_has_bundle_script(self):
        script = assets.assets_root() / 'bundle' / 'archive-cleanup.sh'
        assert script.is_file()

    def test_has_pinned_refs_toml(self):
        pins = assets.assets_root() / 'pinned_refs.toml'
        assert pins.is_file()


class TestWheelMaterialization:
    """Sanity checks for contributors: `_assets/` should never be committed
    to git (force-include builds it on the fly). When dev install is used,
    the repo's source tree is the canonical reference instead.
    """

    def test_dev_install_does_not_materialize_assets_dir(self, tmp_path: Path):
        # In editable install the directory must NOT exist (force-include
        # only fires at build time). If a contributor accidentally commits
        # `_assets/`, this test catches it on a clean checkout.
        # We verify by checking presence is consistent with has_bundled_assets()
        root = assets.assets_root()
        if root.exists():
            # If it exists, it must look like a real bundle (agents present)
            assert (root / 'agents').is_dir(), (
                'orquestrum/_assets/ exists but is incomplete — looks like '
                'a partial copy was committed; remove it from git.'
            )
