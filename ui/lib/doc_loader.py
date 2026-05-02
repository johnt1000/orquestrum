"""doc_loader.py — discover and classify markdown docs by audience.

Each document gets a category based on its location:
  - agent-context  → consumed by LLMs at runtime
  - governance     → consumed by humans (cost, observability, planning)
  - baselines      → auto-generated audits (read-only, machine-produced)
  - other          → anything outside docs/ (CLAUDE.md, README.md)

Includes a ripgrep-backed search; falls back to plain Python regex if rg is absent.
"""
from __future__ import annotations
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Audience = Literal['agent-context', 'governance', 'baselines', 'other']

AUDIENCE_BADGES: dict[Audience, str] = {
    'agent-context': '🧠',
    'governance':    '👤',
    'baselines':     '📊',
    'other':         '📄',
}


@dataclass(frozen=True)
class DocEntry:
    path:      Path           # absolute
    rel:       str            # e.g. "docs/agent-context/SDLC.md"
    title:     str            # H1 if present, else filename stem
    audience:  Audience
    size_b:    int

    @property
    def badge(self) -> str:
        return AUDIENCE_BADGES[self.audience]


def _classify(rel: str) -> Audience:
    if rel.startswith('docs/agent-context/'):
        return 'agent-context'
    if rel.startswith('docs/governance/'):
        return 'governance'
    if rel.startswith('docs/baselines/'):
        return 'baselines'
    return 'other'


def _read_title(path: Path) -> str:
    try:
        with path.open('r', encoding='utf-8') as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                stripped = line.strip()
                if stripped.startswith('# '):
                    return stripped[2:].strip()
    except OSError:
        pass
    return path.stem


def list_docs(root: Path, include_root_files: bool = True) -> list[DocEntry]:
    """List every markdown doc relevant to the UI.

    `include_root_files` adds CLAUDE.md and README.md when they exist at root.
    """
    out: list[DocEntry] = []
    docs_dir = root / 'docs'
    if docs_dir.is_dir():
        for f in sorted(docs_dir.rglob('*.md')):
            rel = f.relative_to(root).as_posix()
            out.append(DocEntry(
                path=f,
                rel=rel,
                title=_read_title(f),
                audience=_classify(rel),
                size_b=f.stat().st_size,
            ))
    if include_root_files:
        for name in ('README.md', 'CLAUDE.md'):
            f = root / name
            if f.is_file():
                out.append(DocEntry(
                    path=f,
                    rel=name,
                    title=_read_title(f),
                    audience='other',
                    size_b=f.stat().st_size,
                ))
    return out


@dataclass(frozen=True)
class SearchHit:
    rel:        str
    line_no:    int
    line:       str

    @property
    def line_truncated(self) -> str:
        return self.line if len(self.line) <= 200 else self.line[:197] + '...'


def search(root: Path, query: str, max_hits: int = 200) -> list[SearchHit]:
    """Search across docs/, README.md, CLAUDE.md. Use ripgrep when available."""
    if not query.strip():
        return []
    targets = ['docs', 'README.md', 'CLAUDE.md']
    existing = [t for t in targets if (root / t).exists()]
    if not existing:
        return []

    if shutil.which('rg'):
        cmd = ['rg', '--no-heading', '--line-number', '--max-count', str(max_hits), '--', query, *existing]
        try:
            result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            return []
        hits: list[SearchHit] = []
        for raw in result.stdout.splitlines():
            # format: path:line:content
            parts = raw.split(':', 2)
            if len(parts) < 3:
                continue
            rel, lineno, content = parts
            try:
                hits.append(SearchHit(rel=rel, line_no=int(lineno), line=content))
            except ValueError:
                continue
            if len(hits) >= max_hits:
                break
        return hits

    # Fallback: plain Python re
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[SearchHit] = []
    for entry in list_docs(root):
        try:
            with entry.path.open('r', encoding='utf-8') as f:
                for i, line in enumerate(f, start=1):
                    if pattern.search(line):
                        hits.append(SearchHit(rel=entry.rel, line_no=i, line=line.rstrip()))
                        if len(hits) >= max_hits:
                            return hits
        except OSError:
            continue
    return hits


def render_markdown(text: str) -> str:
    """Render md → HTML using mistune; safe defaults (no raw HTML, no JS)."""
    import mistune
    md = mistune.create_markdown(
        escape=True,
        plugins=['strikethrough', 'table', 'task_lists', 'url'],
    )
    return md(text)
