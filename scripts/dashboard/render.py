#!/usr/bin/env python3
"""render.py — render .orquestrum/metrics/events.jsonl into a static dashboard.

Usage:
    uv run scripts/dashboard/render.py                       # default: .orquestrum/metrics/, writes dashboard.md
    uv run scripts/dashboard/render.py --metrics-dir PATH    # custom location
    uv run scripts/dashboard/render.py --html                # also write dashboard.html
    uv run scripts/dashboard/render.py --tier balanced       # show budget bands for tier

Reads:
    {metrics_dir}/events.jsonl

Writes:
    {metrics_dir}/dashboard.md   (always)
    {metrics_dir}/dashboard.html (only with --html)

No server, no auto-refresh. Run on demand.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.metrics import read_events, aggregate, SessionAggregate
from lib.budget import SOFT_THRESHOLDS


def _bar(value: int, threshold: int, width: int = 40) -> str:
    """Render a unicode bar that scales to 1.0 == threshold; values above show overflow."""
    if threshold <= 0:
        return ''
    pct = value / threshold
    filled = min(width, int(pct * width))
    if pct <= 1.0:
        return '█' * filled + '░' * (width - filled)
    return '█' * width + '▓' * min(width // 4, int((pct - 1.0) * width))


def render_markdown(sess: SessionAggregate, events: list[dict], tier_for_budget: str | None) -> str:
    lines = ['# Orquestrum Session Dashboard', '']
    lines.append(f'**Tier**: `{sess.tier or tier_for_budget or "?"}`  |  '
                 f'**Calls**: {sess.totals.get("calls", 0)}  |  '
                 f'**Skills**: {sess.totals.get("skill_calls", 0)}')
    if sess.started_at:
        lines.append(f'**Started**: {sess.started_at}  |  **Last event**: {sess.ended_at}')
    lines.append('')

    in_t  = int(sess.totals.get('input_tokens',  0))
    out_t = int(sess.totals.get('output_tokens', 0))
    cac_t = int(sess.totals.get('cached_tokens', 0))
    cost  = float(sess.totals.get('cost_usd', 0.0))

    lines.append('## Totals')
    lines.append('')
    lines.append('| Metric | Value |')
    lines.append('|---|---:|')
    lines.append(f'| Input tokens   | {in_t:,} |')
    lines.append(f'| Output tokens  | {out_t:,} |')
    lines.append(f'| Cached tokens  | {cac_t:,} ({(cac_t/max(in_t,1)*100):.1f}% of input) |')
    lines.append(f'| Estimated cost | ${cost:.4f} USD |')
    lines.append('')

    if tier_for_budget and tier_for_budget in SOFT_THRESHOLDS:
        in_thr, out_thr = SOFT_THRESHOLDS[tier_for_budget]
        lines.append(f'## Budget — `{tier_for_budget}` tier')
        lines.append('')
        lines.append('```')
        lines.append(f'input  {in_t:>10,} / {in_thr:>10,}  {_bar(in_t, in_thr)}')
        lines.append(f'output {out_t:>10,} / {out_thr:>10,}  {_bar(out_t, out_thr)}')
        lines.append('```')
        if in_t > in_thr or out_t > out_thr:
            lines.append('')
            lines.append('> ⚠ Above soft threshold. See `docs/governance/COST.md` for tuning.')
        lines.append('')

    if sess.by_skill:
        lines.append('## By skill (top 10)')
        lines.append('')
        lines.append('| Skill | Calls | Input | Output | Cost USD |')
        lines.append('|-------|------:|------:|-------:|---------:|')
        ranked = sorted(sess.by_skill.items(), key=lambda kv: int(kv[1].get('input_tokens', 0)), reverse=True)
        for name, rec in ranked[:10]:
            lines.append(
                f'| `{name}` | {rec.get("calls", 0)} | '
                f'{int(rec.get("input_tokens", 0)):,} | '
                f'{int(rec.get("output_tokens", 0)):,} | '
                f'${float(rec.get("cost_usd", 0.0)):.4f} |'
            )
        lines.append('')

    if sess.by_agent:
        lines.append('## By agent')
        lines.append('')
        lines.append('| Agent | Calls | Input | Output | Cost USD |')
        lines.append('|-------|------:|------:|-------:|---------:|')
        for name, rec in sorted(sess.by_agent.items(), key=lambda kv: int(kv[1].get('input_tokens', 0)), reverse=True):
            lines.append(
                f'| `{name}` | {rec.get("calls", 0)} | '
                f'{int(rec.get("input_tokens", 0)):,} | '
                f'{int(rec.get("output_tokens", 0)):,} | '
                f'${float(rec.get("cost_usd", 0.0)):.4f} |'
            )
        lines.append('')

    completion_events = [e for e in events if e.get('kind') == 'skill_completion']
    if completion_events:
        statuses = Counter(e.get('status', 'unknown') for e in completion_events)
        lines.append('## Skill completions')
        lines.append('')
        for status, count in statuses.most_common():
            lines.append(f'- **{status}**: {count}')
        confidences = [float(e['confidence_avg']) for e in completion_events if 'confidence_avg' in e]
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            lines.append('')
            lines.append(f'Mean confidence across {len(confidences)} skills: **{avg_conf:.2f}**')
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('Re-render: `uv run scripts/dashboard/render.py [--tier TIER] [--html]`')
    return '\n'.join(lines)


def render_html(md_text: str, sess: SessionAggregate) -> str:
    """Single-file HTML wrapping the markdown — no build, no fetch, no server."""
    # Convert basic markdown tables/headers to HTML inline (no external libs).
    body_lines: list[str] = []
    in_table = False
    in_code  = False
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.startswith('```'):
            if not in_code:
                body_lines.append('<pre><code>')
                in_code = True
            else:
                body_lines.append('</code></pre>')
                in_code = False
            continue
        if in_code:
            body_lines.append(_html_escape(line))
            continue
        if line.startswith('# '):
            body_lines.append(f'<h1>{_html_escape(line[2:])}</h1>')
        elif line.startswith('## '):
            body_lines.append(f'<h2>{_html_escape(line[3:])}</h2>')
        elif line.startswith('| '):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(set(c) <= set('-:') for c in cells):
                continue  # separator row
            tag = 'th' if not in_table else 'td'
            if not in_table:
                body_lines.append('<table>')
                in_table = True
            body_lines.append('<tr>' + ''.join(f'<{tag}>{_html_escape(c)}</{tag}>' for c in cells) + '</tr>')
        else:
            if in_table:
                body_lines.append('</table>')
                in_table = False
            if line:
                body_lines.append(f'<p>{_html_escape(line)}</p>')
    if in_table:
        body_lines.append('</table>')

    body = '\n'.join(body_lines)
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>Orquestrum dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        max-width: 980px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #222; }}
h1 {{ border-bottom: 2px solid #444; padding-bottom: .3rem; }}
h2 {{ margin-top: 2rem; color: #555; }}
table {{ border-collapse: collapse; margin: 1rem 0; }}
th, td {{ border: 1px solid #ddd; padding: .4rem .8rem; text-align: left; }}
th {{ background: #f5f5f5; }}
pre {{ background: #f9f9f9; padding: .8rem 1rem; overflow-x: auto; border-radius: 4px; }}
code {{ font-family: SFMono-Regular, Menlo, monospace; font-size: 0.95em; }}
</style></head><body>
{body}
</body></html>'''


def _html_escape(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog='orquestrum dashboard',
                                     description='Render Orquestrum session metrics dashboard.')
    parser.add_argument('--metrics-dir', type=Path, default=Path('.orquestrum/metrics'),
                        help='Directory containing events.jsonl (default: .orquestrum/metrics)')
    parser.add_argument('--tier', default=None,
                        help='Tier for budget overlay (deep | balanced | mechanical | sharp)')
    parser.add_argument('--html', action='store_true', help='Also write dashboard.html')
    args = parser.parse_args(argv)

    events_file = args.metrics_dir / 'events.jsonl'
    if not events_file.exists():
        print(f'No events found at {events_file} — nothing to render.', file=sys.stderr)
        sys.exit(1)

    events = read_events(events_file)
    sess   = aggregate(events, tier=args.tier)
    md     = render_markdown(sess, events, args.tier)

    md_path = args.metrics_dir / 'dashboard.md'
    md_path.write_text(md, encoding='utf-8')
    print(f'Wrote {md_path}')

    if args.html:
        html_path = args.metrics_dir / 'dashboard.html'
        html_path.write_text(render_html(md, sess), encoding='utf-8')
        print(f'Wrote {html_path}')


if __name__ == '__main__':
    main()
