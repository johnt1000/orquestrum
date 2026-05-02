#!/usr/bin/env python3
"""compress_refs.py — produce *.compact.md companions for large skill references.

Deterministic compression. NO LLM is called. The output is a smaller, structurally
similar version of the input that preserves the load-bearing content while
dropping noise.

Rules applied (in order):
  1. Strip everything between `<!-- compact:drop -->` and `<!-- /compact:drop -->`
  2. Trim each fenced code block to ≤ 40 lines (keep first 30, last 5, ellipsis)
  3. Keep at most 3 examples (heuristic: H2/H3 headers starting with "Example",
     "Sample", "Few-shot", "Ex.", or numbered like "Example 1:")
  4. Strip blockquote chains > 6 lines (keep first 3, ellipsis)

Output is written next to the input, with `.compact.md` extension. Hand-written
`*.compact.md` files take precedence — the script refuses to overwrite a
hand-written one without `--force`.

Usage:
    uv run scripts/build/compress_refs.py                    # compress all references > threshold
    uv run scripts/build/compress_refs.py --skill SKILL      # compress one skill only
    uv run scripts/build/compress_refs.py --threshold-kb 4   # custom threshold
    uv run scripts/build/compress_refs.py --dry-run          # report only, no writes
    uv run scripts/build/compress_refs.py --force            # overwrite hand-written .compact.md
"""
from __future__ import annotations
import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / 'skills'

DEFAULT_THRESHOLD_KB = 8

_DROP_BLOCK_RE = re.compile(
    r'<!--\s*compact:drop\s*-->.*?<!--\s*/compact:drop\s*-->',
    re.DOTALL | re.IGNORECASE,
)

_EXAMPLE_HEADER_RE = re.compile(
    r'^(##?#?)\s+(?:Example|Sample|Few-shot|Ex\.?|Example\s+\d+:?).*$',
    re.IGNORECASE | re.MULTILINE,
)

_FENCE_RE = re.compile(r'^```')


@dataclass
class CompressResult:
    skill:        str
    src_path:     Path
    dst_path:     Path
    src_bytes:    int
    dst_bytes:    int
    rules_fired:  list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def ratio(self) -> float:
        return (self.dst_bytes / self.src_bytes) if self.src_bytes else 1.0

    @property
    def saved_bytes(self) -> int:
        return self.src_bytes - self.dst_bytes


def _strip_drop_blocks(text: str, fired: list[str]) -> str:
    new = _DROP_BLOCK_RE.sub('', text)
    if new != text:
        fired.append('drop_blocks')
    return new


def _trim_fenced_blocks(text: str, fired: list[str], keep_head: int = 30, keep_tail: int = 5) -> str:
    lines = text.split('\n')
    out: list[str] = []
    in_fence = False
    fence_buf: list[str] = []
    fence_opener = ''

    def flush_fence() -> None:
        nonlocal in_fence, fence_buf, fence_opener
        if len(fence_buf) > (keep_head + keep_tail):
            head = fence_buf[:keep_head]
            tail = fence_buf[-keep_tail:]
            ellipsis = ['', f'/* … {len(fence_buf) - keep_head - keep_tail} lines elided … */', '']
            out.append(fence_opener)
            out.extend(head)
            out.extend(ellipsis)
            out.extend(tail)
            fired.append('fence_truncated')
        else:
            out.append(fence_opener)
            out.extend(fence_buf)
        fence_buf = []
        fence_opener = ''

    for line in lines:
        if not in_fence and _FENCE_RE.match(line):
            in_fence = True
            fence_opener = line
            fence_buf = []
            continue
        if in_fence and _FENCE_RE.match(line):
            flush_fence()
            out.append(line)
            in_fence = False
            continue
        if in_fence:
            fence_buf.append(line)
        else:
            out.append(line)

    if in_fence:
        # unclosed fence — emit as-is
        out.append(fence_opener)
        out.extend(fence_buf)

    return '\n'.join(out)


def _limit_examples(text: str, fired: list[str], max_examples: int = 3) -> str:
    """Keep the first max_examples sections whose header matches the example pattern.
    Drop subsequent example sections entirely (header + content up to next H2/H3 of same level).
    """
    matches = list(_EXAMPLE_HEADER_RE.finditer(text))
    if len(matches) <= max_examples:
        return text

    # Find drop ranges: start of (max+1)th example to start of next non-example header at same level
    keep_count = max_examples
    to_drop_ranges: list[tuple[int, int]] = []
    for i, m in enumerate(matches):
        if i < keep_count:
            continue
        start = m.start()
        level = len(m.group(1))
        # Find next header at same or higher level
        rest = text[m.end():]
        next_header = re.search(r'^#{1,' + str(level) + r'}\s+\S', rest, re.MULTILINE)
        end = m.end() + next_header.start() if next_header else len(text)
        to_drop_ranges.append((start, end))

    # Apply drops in reverse order to preserve indices
    new = text
    for start, end in reversed(to_drop_ranges):
        new = new[:start] + new[end:]
    if new != text:
        fired.append(f'examples_capped_at_{max_examples}')
    return new


def _trim_long_blockquotes(text: str, fired: list[str], keep_head: int = 3) -> str:
    """Replace blockquote chains > 6 lines with just the first keep_head + ellipsis."""
    lines = text.split('\n')
    out: list[str] = []
    bq_buf: list[str] = []
    fired_local = False

    def flush_bq() -> None:
        nonlocal bq_buf, fired_local
        if len(bq_buf) > 6:
            out.extend(bq_buf[:keep_head])
            out.append('> *(… blockquote elided …)*')
            fired_local = True
        else:
            out.extend(bq_buf)
        bq_buf = []

    for line in lines:
        if line.startswith('>'):
            bq_buf.append(line)
        else:
            if bq_buf:
                flush_bq()
            out.append(line)
    if bq_buf:
        flush_bq()
    if fired_local:
        fired.append('blockquote_trimmed')
    return '\n'.join(out)


def compress_one(src: Path, dst: Path, *, force: bool = False) -> CompressResult:
    src_bytes = src.stat().st_size
    if dst.exists() and not force:
        # Detect hand-written: check if it has a sentinel comment from us
        dst_text = dst.read_text(encoding='utf-8')
        if '<!-- compact:auto-generated -->' not in dst_text:
            return CompressResult(
                skill=src.stem, src_path=src, dst_path=dst,
                src_bytes=src_bytes, dst_bytes=dst.stat().st_size,
                skipped_reason='hand-written .compact.md exists; use --force to overwrite',
            )

    text   = src.read_text(encoding='utf-8')
    fired: list[str] = []
    text = _strip_drop_blocks(text, fired)
    text = _trim_fenced_blocks(text, fired)
    text = _limit_examples(text, fired)
    text = _trim_long_blockquotes(text, fired)

    sentinel = '<!-- compact:auto-generated -->\n'
    final = sentinel + text
    return CompressResult(
        skill=src.stem, src_path=src, dst_path=dst,
        src_bytes=src_bytes, dst_bytes=len(final.encode('utf-8')),
        rules_fired=fired,
    ), final  # type: ignore[return-value]


def find_candidates(threshold_bytes: int, only_skill: str | None = None) -> list[Path]:
    """Return list of references/*-references.md files above threshold."""
    out: list[Path] = []
    skills = [SKILLS_DIR / only_skill] if only_skill else sorted(SKILLS_DIR.iterdir())
    for d in skills:
        if not d.is_dir():
            continue
        refs_dir = d / 'references'
        if not refs_dir.is_dir():
            continue
        for f in refs_dir.glob('*-references.md'):
            if f.stat().st_size >= threshold_bytes:
                out.append(f)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog='orquestrum compact',
                                     description='Compress oversized skill references deterministically.')
    parser.add_argument('--threshold-kb', type=int, default=DEFAULT_THRESHOLD_KB,
                        help=f'Minimum size in KB to compress (default {DEFAULT_THRESHOLD_KB})')
    parser.add_argument('--skill', metavar='SLUG', default=None,
                        help='Compress only this skill (default: all candidates)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be compressed; do not write')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite hand-written .compact.md companions')
    args = parser.parse_args(argv)

    threshold_bytes = args.threshold_kb * 1024
    candidates = find_candidates(threshold_bytes, args.skill)

    if not candidates:
        print(f'No references ≥ {args.threshold_kb} KB found' +
              (f' for skill {args.skill}' if args.skill else '') + '.')
        return

    print(f'{"Skill":<30} {"src KB":>8} {"dst KB":>8} {"ratio":>6}  Rules / Status')
    print('-' * 90)
    total_saved = 0

    for src in candidates:
        skill = src.parent.parent.name
        dst   = src.parent / src.name.replace('-references.md', '-references.compact.md')

        result_or_pair = compress_one(src, dst, force=args.force)
        if isinstance(result_or_pair, tuple):
            result, content = result_or_pair
        else:
            result = result_or_pair
            content = None

        status = result.skipped_reason or ', '.join(result.rules_fired) or 'no-op'
        src_kb = result.src_bytes / 1024
        dst_kb = result.dst_bytes / 1024
        ratio  = result.ratio

        print(f'{skill:<30} {src_kb:>8.1f} {dst_kb:>8.1f} {ratio:>6.0%}  {status}')

        if not args.dry_run and content is not None and not result.skipped_reason:
            dst.write_text(content, encoding='utf-8')
            total_saved += result.saved_bytes

    if not args.dry_run:
        print(f'\n  total bytes saved: {total_saved:,} ({total_saved / 1024:.1f} KB)')
    else:
        print(f'\n  --dry-run: no files written')


if __name__ == '__main__':
    main()
