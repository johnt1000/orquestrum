"""Unit tests for ui/lib/doc_loader.py — classify, search, render."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch

import pytest

from ui.lib.doc_loader import (
    DocEntry,
    SearchHit,
    _classify,
    _read_title,
    list_docs,
    render_markdown,
    search,
)


# ─── _classify ───────────────────────────────────────────────────────────────

class TestClassify:
    def test_agent_context(self):
        assert _classify('docs/agent-context/SDLC.md') == 'agent-context'

    def test_governance(self):
        assert _classify('docs/governance/MODELS.md') == 'governance'

    def test_baselines(self):
        assert _classify('docs/baselines/payload-audit.md') == 'baselines'

    def test_other_for_root_file(self):
        assert _classify('README.md') == 'other'

    def test_other_for_claude_md(self):
        assert _classify('CLAUDE.md') == 'other'

    def test_other_for_unknown_subdir(self):
        assert _classify('docs/misc/notes.md') == 'other'

    def test_agent_context_nested(self):
        assert _classify('docs/agent-context/sub/FOO.md') == 'agent-context'


# ─── _read_title ─────────────────────────────────────────────────────────────

class TestReadTitle:
    def test_reads_first_h1(self, tmp_path: Path):
        f = tmp_path / 'doc.md'
        f.write_text('# My Title\n\nSome body.', encoding='utf-8')
        assert _read_title(f) == 'My Title'

    def test_skips_non_h1_lines(self, tmp_path: Path):
        f = tmp_path / 'doc.md'
        f.write_text('Some text\n\n# Real Title\n', encoding='utf-8')
        assert _read_title(f) == 'Real Title'

    def test_returns_stem_when_no_h1(self, tmp_path: Path):
        f = tmp_path / 'no-h1.md'
        f.write_text('just some text\n', encoding='utf-8')
        assert _read_title(f) == 'no-h1'

    def test_returns_stem_for_empty_file(self, tmp_path: Path):
        f = tmp_path / 'empty.md'
        f.write_text('', encoding='utf-8')
        assert _read_title(f) == 'empty'

    def test_returns_stem_for_missing_file(self, tmp_path: Path):
        f = tmp_path / 'ghost.md'
        assert _read_title(f) == 'ghost'

    def test_strips_title_whitespace(self, tmp_path: Path):
        f = tmp_path / 'doc.md'
        f.write_text('#   Padded Title   \n', encoding='utf-8')
        assert _read_title(f) == 'Padded Title'


# ─── list_docs ───────────────────────────────────────────────────────────────

class TestListDocs:
    def test_empty_root_returns_empty(self, tmp_path: Path):
        assert list_docs(tmp_path) == []

    def test_finds_docs_in_subdir(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'governance'
        d.mkdir(parents=True)
        (d / 'FOO.md').write_text('# Foo\n', encoding='utf-8')
        entries = list_docs(tmp_path)
        assert len(entries) == 1
        assert entries[0].audience == 'governance'
        assert entries[0].title == 'Foo'

    def test_finds_readme_at_root(self, tmp_path: Path):
        (tmp_path / 'README.md').write_text('# Readme\n', encoding='utf-8')
        entries = list_docs(tmp_path)
        assert any(e.rel == 'README.md' for e in entries)

    def test_finds_claude_md_at_root(self, tmp_path: Path):
        (tmp_path / 'CLAUDE.md').write_text('# Claude\n', encoding='utf-8')
        entries = list_docs(tmp_path)
        assert any(e.rel == 'CLAUDE.md' for e in entries)

    def test_include_root_files_false(self, tmp_path: Path):
        (tmp_path / 'README.md').write_text('# Readme\n', encoding='utf-8')
        entries = list_docs(tmp_path, include_root_files=False)
        assert not any(e.rel == 'README.md' for e in entries)

    def test_classifies_agent_context(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'agent-context'
        d.mkdir(parents=True)
        (d / 'SDLC.md').write_text('# SDLC\n', encoding='utf-8')
        entries = list_docs(tmp_path)
        assert entries[0].audience == 'agent-context'

    def test_doc_entry_badge(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'baselines'
        d.mkdir(parents=True)
        (d / 'audit.md').write_text('# Audit\n', encoding='utf-8')
        entries = list_docs(tmp_path)
        assert entries[0].badge == '📊'

    def test_size_b_is_correct(self, tmp_path: Path):
        content = '# Hello\n'
        (tmp_path / 'README.md').write_text(content, encoding='utf-8')
        entries = list_docs(tmp_path)
        readme = next(e for e in entries if e.rel == 'README.md')
        assert readme.size_b == len(content.encode('utf-8'))


# ─── search ──────────────────────────────────────────────────────────────────

class TestSearch:
    def test_empty_query_returns_empty(self, tmp_path: Path):
        assert search(tmp_path, '') == []

    def test_blank_query_returns_empty(self, tmp_path: Path):
        assert search(tmp_path, '   ') == []

    def test_no_targets_returns_empty(self, tmp_path: Path):
        # No docs/, README.md, or CLAUDE.md
        assert search(tmp_path, 'hello') == []

    def test_python_fallback_finds_match(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'governance'
        d.mkdir(parents=True)
        (d / 'TEST.md').write_text('# Heading\nThis has findme in it.\n', encoding='utf-8')
        with patch('shutil.which', return_value=None):
            hits = search(tmp_path, 'findme')
        assert len(hits) == 1
        assert hits[0].line_no == 2
        assert 'findme' in hits[0].line

    def test_python_fallback_case_insensitive(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'governance'
        d.mkdir(parents=True)
        (d / 'TEST.md').write_text('FINDME HERE\n', encoding='utf-8')
        with patch('shutil.which', return_value=None):
            hits = search(tmp_path, 'findme')
        assert len(hits) == 1

    def test_python_fallback_no_match_returns_empty(self, tmp_path: Path):
        (tmp_path / 'README.md').write_text('nothing relevant\n', encoding='utf-8')
        with patch('shutil.which', return_value=None):
            hits = search(tmp_path, 'xyz_not_here')
        assert hits == []

    def test_search_hit_truncation(self):
        long_line = 'x' * 300
        hit = SearchHit(rel='a.md', line_no=1, line=long_line)
        assert len(hit.line_truncated) == 200
        assert hit.line_truncated.endswith('...')

    def test_search_hit_no_truncation_short(self):
        hit = SearchHit(rel='a.md', line_no=1, line='short line')
        assert hit.line_truncated == 'short line'

    def test_max_hits_respected(self, tmp_path: Path):
        d = tmp_path / 'docs' / 'governance'
        d.mkdir(parents=True)
        content = '\n'.join(f'match line {i}' for i in range(50))
        (d / 'big.md').write_text(content, encoding='utf-8')
        with patch('shutil.which', return_value=None):
            hits = search(tmp_path, 'match', max_hits=5)
        assert len(hits) == 5


# ─── render_markdown ─────────────────────────────────────────────────────────

class TestRenderMarkdown:
    def test_renders_heading(self):
        html = render_markdown('# Hello\n')
        assert '<h1>' in html
        assert 'Hello' in html

    def test_renders_paragraph(self):
        html = render_markdown('Some text here.\n')
        assert '<p>' in html
        assert 'Some text here.' in html

    def test_escapes_raw_html(self):
        html = render_markdown('<script>alert(1)</script>')
        assert '<script>' not in html

    def test_returns_string(self):
        assert isinstance(render_markdown('hello'), str)

    def test_renders_table(self):
        md = '| a | b |\n|---|---|\n| 1 | 2 |\n'
        html = render_markdown(md)
        assert '<table' in html

    def test_renders_strikethrough(self):
        html = render_markdown('~~strike~~')
        assert 'strike' in html
