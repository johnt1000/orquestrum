#!/usr/bin/env python3
"""attention_distribution.py — analyze attention_score distribution across artifacts.

Walks `docs/03-quality/` (or any --root) looking for files with
`attention_score`, `attention_band`, `attention_factors` in frontmatter.
Reports band counts, p10/p50/p90, mean, and the most-frequent factors.

Used by ROADMAP R2 to decide whether to tune `orquestrum/lib/attention.py` weights.

Usage:
    orquestrum audit attention
    orquestrum audit attention --root /path/to/project
    orquestrum audit attention --output docs/baselines/attention-YYYY-MM.md
"""
from __future__ import annotations
import argparse
import statistics
import sys
from collections import Counter
from pathlib import Path


def collect(root: Path) -> list[dict]:
    """Walk root, return list of {path, score, band, factors} dicts."""
    import frontmatter as fm
    results: list[dict] = []
    for f in root.rglob('*.md'):
        try:
            post = fm.load(str(f))
        except Exception:
            continue
        if 'attention_score' not in post:
            continue
        try:
            score = int(post['attention_score'])
        except (TypeError, ValueError):
            continue
        results.append({
            'path':    str(f.relative_to(root)),
            'score':   score,
            'band':    str(post.get('attention_band', '?')),
            'factors': list(post.get('attention_factors') or []),
        })
    return results


def render_markdown(items: list[dict], threshold_n: int = 30) -> str:
    n = len(items)
    lines = ['# Attention Score Distribution', '']
    lines.append(f'**Sample size**: {n} artifacts')
    if n == 0:
        lines.append('')
        lines.append('> No artifacts with `attention_score` frontmatter found.')
        lines.append('> Wait until the framework has emitted some review/qa/security/learning artifacts.')
        lines.append('')
        return '\n'.join(lines)

    if n < threshold_n:
        lines.append(f'> ⚠ N < {threshold_n}: distribution is too small to draw conclusions.')
        lines.append(f'> Tuning attention.py weights requires N ≥ 30 (ideally ≥ 100). Continue collecting.')
    lines.append('')

    scores = [it['score'] for it in items]
    bands  = Counter(it['band'] for it in items)

    lines.append('## Score statistics')
    lines.append('')
    lines.append('| Stat | Value |')
    lines.append('|------|------:|')
    lines.append(f'| mean | {statistics.mean(scores):.1f} |')
    lines.append(f'| median | {statistics.median(scores):.0f} |')
    lines.append(f'| stdev | {statistics.stdev(scores) if n > 1 else 0:.1f} |')
    lines.append(f'| min | {min(scores)} |')
    lines.append(f'| max | {max(scores)} |')
    if n >= 10:
        sorted_scores = sorted(scores)
        lines.append(f'| p10 | {sorted_scores[n // 10]} |')
        lines.append(f'| p90 | {sorted_scores[n * 9 // 10]} |')
    lines.append('')

    lines.append('## Band distribution')
    lines.append('')
    lines.append('| Band | Count | % |')
    lines.append('|------|------:|---:|')
    for band in ('green', 'yellow', 'red', '?'):
        c = bands.get(band, 0)
        pct = (c / n * 100) if n else 0
        emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(band, '⚪')
        lines.append(f'| {emoji} {band} | {c} | {pct:.0f}% |')
    lines.append('')

    factor_counter: Counter = Counter()
    for it in items:
        for factor in it['factors']:
            key = str(factor).split(':')[0]
            factor_counter[key] += 1
    if factor_counter:
        lines.append('## Most frequent attention factors (top 10)')
        lines.append('')
        lines.append('| Factor | Count |')
        lines.append('|--------|------:|')
        for factor, count in factor_counter.most_common(10):
            lines.append(f'| `{factor}` | {count} |')
        lines.append('')

    if n >= threshold_n:
        green_pct = bands.get('green', 0) / n
        red_pct   = bands.get('red',   0) / n
        lines.append('## Calibration signal')
        lines.append('')
        if green_pct > 0.90:
            lines.append('> 🔴 **Green > 90%**: formula too lax. Consider raising weight on '
                         '`confidence` (25→30) or `inference_depth` (10→12).')
        elif red_pct > 0.30:
            lines.append('> 🔴 **Red > 30%**: formula too severe (alert fatigue). Consider lowering '
                         '`drift_days` weight (20→15) or `gate_failure_count` (5→3).')
        elif red_pct < 0.05:
            lines.append('> 🟡 **Red < 5%**: red band rarely fires — verify inputs are populated correctly.')
        else:
            lines.append('> 🟢 **Distribution looks balanced.** No tuning recommended at this sample size.')
        lines.append('')

    if items:
        ranked = sorted(items, key=lambda x: x['score'])
        lines.append('## Lowest-scoring artifacts (need attention)')
        lines.append('')
        lines.append('| Score | Band | Factors | Path |')
        lines.append('|------:|------|---------|------|')
        for it in ranked[:10]:
            emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(it['band'], '⚪')
            factors = ', '.join(it['factors'][:3]) or '—'
            lines.append(f'| {it["score"]} | {emoji} | {factors} | `{it["path"]}` |')
        lines.append('')

    lines.append('---')
    lines.append('Re-run: `orquestrum audit attention [--root PATH]`')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog='orquestrum audit attention',
        description='Attention score distribution analysis.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum audit attention\n'
            '  orquestrum audit attention --root /path/to/project\n'
            '  orquestrum audit attention --threshold-n 100 --output report.md'
        ),
    )
    parser.add_argument('--root', default='.', help='Root to scan (default: cwd)')
    parser.add_argument('--threshold-n', type=int, default=30,
                        help='Minimum N to issue calibration signals (default 30)')
    parser.add_argument('--output', metavar='PATH',
                        help='Write the markdown report to this path (also prints to stdout)')
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f'error: not a directory: {root}', file=sys.stderr)
        sys.exit(1)

    # Walk only docs/03-quality/ if it exists; otherwise the whole root
    target = root / 'docs' / '03-quality'
    if not target.is_dir():
        target = root

    items = collect(target)
    md = render_markdown(items, threshold_n=args.threshold_n)
    print(md)

    if args.output:
        out = Path(args.output).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding='utf-8')
        print(f'\nWritten: {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
