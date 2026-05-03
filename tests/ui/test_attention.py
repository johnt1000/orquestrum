"""Tests for ui.lib.attention.attention_bands."""
from __future__ import annotations
from pathlib import Path

import pytest

from ui.lib.attention import attention_bands


@pytest.fixture()
def quality_dir(tmp_path: Path) -> Path:
    d = tmp_path / 'docs' / '03-quality' / 'review'
    d.mkdir(parents=True)
    return d


class TestAttentionBands:
    def test_no_root_returns_none(self):
        assert attention_bands(None) is None

    def test_missing_dir_returns_none(self, tmp_path: Path):
        assert attention_bands(tmp_path) is None

    def test_no_artifacts_returns_none(self, quality_dir: Path, tmp_path: Path):
        # dir exists but no .md files with attention_score
        (quality_dir / 'README.md').write_text('# nothing\n', encoding='utf-8')
        assert attention_bands(tmp_path) is None

    def test_buckets_into_three_bands(self, quality_dir: Path, tmp_path: Path):
        for i, score in enumerate([20, 40, 60, 70, 80, 90]):
            (quality_dir / f'r{i}.md').write_text(
                f'---\nattention_score: {score}\n---\n# x\n',
                encoding='utf-8',
            )
        rep = attention_bands(tmp_path)
        assert rep is not None
        assert rep.green == 3   # 70, 80, 90
        assert rep.yellow == 2  # 40, 60
        assert rep.red == 1     # 20
        assert rep.total == 6
        assert 0 <= rep.avg <= 100
        assert rep.score == rep.avg

    def test_invalid_scores_skipped(self, quality_dir: Path, tmp_path: Path):
        (quality_dir / 'a.md').write_text('---\nattention_score: bogus\n---\n', encoding='utf-8')
        (quality_dir / 'b.md').write_text('---\nattention_score: 999\n---\n', encoding='utf-8')
        (quality_dir / 'c.md').write_text('---\nattention_score: 50\n---\n', encoding='utf-8')
        rep = attention_bands(tmp_path)
        assert rep is not None
        assert rep.total == 1
        assert rep.yellow == 1
