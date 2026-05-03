"""orquestrum.lib.verify — post-action verifiers for convert and install.

Both `orquestrum convert` and `orquestrum install` write a lot of files in
one shot. Without verification a partial write (disk full, copy failure,
adapter regression) can silently produce a half-broken integration. This
module runs a per-tool checklist against the output directory and reports
results so users see, in plain text, exactly what was generated and where.

Each tool has an expected manifest:
  - claude-code  : .claude/agents/*.md (8), .claude/settings.json, .sdd/{docs,skills,scripts}/
  - opencode     : agents/*.md (8), docs/, skills/, scripts/
  - cursor       : .cursor/rules/*.mdc (>= 8 + skills count)
  - aider        : CONVENTIONS.md
  - windsurf     : .windsurfrules

The verifier is read-only: it never modifies the target. On failure it
returns a structured report that callers (CLI, tests) can render.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


# ── ANSI colours (mirror lib.log so callers can render uniformly) ──────────
_GREEN  = '\033[0;32m'
_RED    = '\033[0;31m'
_YELLOW = '\033[1;33m'
_DIM    = '\033[2m'
_NC     = '\033[0m'

# Number of orchestrator agents Orquestrum ships. Hard-coded here as a
# verification anchor — divergence from this count means something dropped
# silently.
EXPECTED_AGENT_COUNT = 8


@dataclass
class Check:
    label: str
    ok: bool
    detail: str = ''


@dataclass
class VerifyReport:
    target: str               # 'convert:claude-code', 'install:opencode → /path'
    root: Path
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok)

    def add(self, label: str, ok: bool, detail: str = '') -> None:
        self.checks.append(Check(label=label, ok=ok, detail=detail))

    def render(self) -> str:
        """Pretty-print the report with colours; one line per check."""
        lines = []
        status_icon = f'{_GREEN}✓{_NC}' if self.passed else f'{_RED}✗{_NC}'
        lines.append(f'{status_icon} verify: {self.target}')
        for c in self.checks:
            icon = f'{_GREEN}✓{_NC}' if c.ok else f'{_RED}✗{_NC}'
            line = f'    {icon} {c.label}'
            if c.detail:
                colour = _DIM if c.ok else _YELLOW
                line += f' {colour}({c.detail}){_NC}'
            lines.append(line)
        return '\n'.join(lines)


# ─── helpers ────────────────────────────────────────────────────────────────


def _count_files(p: Path, glob: str) -> int:
    if not p.is_dir():
        return 0
    return sum(1 for _ in p.glob(glob))


def _check_dir(report: VerifyReport, rel_path: str, root: Path | None = None) -> bool:
    base = root or report.root
    p = base / rel_path
    exists = p.is_dir()
    report.add(f'{rel_path}/ exists', exists,
               '' if exists else 'directory missing')
    return exists


def _check_file(report: VerifyReport, rel_path: str,
                min_bytes: int = 1, root: Path | None = None) -> bool:
    base = root or report.root
    p = base / rel_path
    if not p.is_file():
        report.add(f'{rel_path}', False, 'file missing')
        return False
    size = p.stat().st_size
    if size < min_bytes:
        report.add(f'{rel_path}', False, f'only {size} bytes (expected >= {min_bytes})')
        return False
    report.add(f'{rel_path}', True, f'{size:,} bytes')
    return True


def _check_count(report: VerifyReport, rel_path: str, glob: str,
                 expected: int, exact: bool = True,
                 root: Path | None = None) -> int:
    base = root or report.root
    p = base / rel_path
    n = _count_files(p, glob)
    if exact:
        ok = n == expected
        detail = f'{n} found' if ok else f'expected {expected}, found {n}'
    else:
        ok = n >= expected
        detail = f'{n} found' if ok else f'expected ≥ {expected}, found {n}'
    report.add(f'{rel_path}/{glob}', ok, detail)
    return n


# ─── per-tool verifiers ─────────────────────────────────────────────────────


def verify_convert_output(tool: str, out_dir: Path,
                          expected_skill_count: int | None = None) -> VerifyReport:
    """Verify the artefacts produced by `orquestrum convert --tool <tool>`.

    out_dir is the per-tool subdir, e.g. `~/.orquestrum/cache/integrations/cursor/`.
    expected_skill_count is the number of skills the source had — used so the
    cursor adapter (which writes one .mdc per skill plus per agent) can be
    validated tightly.
    """
    report = VerifyReport(target=f'convert:{tool}', root=out_dir)

    if not out_dir.is_dir():
        report.add('output directory exists', False,
                   f'{out_dir} not created')
        return report
    report.add('output directory exists', True, str(out_dir))

    if tool == 'claude-code':
        _check_dir(report, '.claude/agents')
        _check_count(report, '.claude/agents', '*.md', EXPECTED_AGENT_COUNT)
        _check_file(report, '.claude/settings.json', min_bytes=10)
        _check_dir(report, '.sdd/docs')
        _check_dir(report, '.sdd/skills')
        _check_dir(report, '.sdd/scripts/hooks')
        _check_dir(report, '.sdd/scripts/lib')
        _check_file(report, '.sdd/scripts/archive-cleanup.sh', min_bytes=100)

    elif tool == 'opencode':
        _check_dir(report, 'agents')
        _check_count(report, 'agents', '*.md', EXPECTED_AGENT_COUNT)
        _check_dir(report, 'docs')
        _check_dir(report, 'skills')
        _check_file(report, 'scripts/archive-cleanup.sh', min_bytes=100)

    elif tool == 'cursor':
        _check_dir(report, '.cursor/rules')
        # 8 agents + ≥ N skills as .mdc files
        skills = expected_skill_count or 0
        _check_count(report, '.cursor/rules', '*.mdc',
                     EXPECTED_AGENT_COUNT + skills, exact=False)
        _check_file(report, '.sdd/scripts/archive-cleanup.sh', min_bytes=100)

    elif tool == 'aider':
        _check_file(report, 'CONVENTIONS.md', min_bytes=500)
        _check_file(report, 'scripts/archive-cleanup.sh', min_bytes=100)

    elif tool == 'windsurf':
        _check_file(report, '.windsurfrules', min_bytes=500)
        _check_file(report, 'scripts/archive-cleanup.sh', min_bytes=100)

    else:
        report.add(f'tool "{tool}" recognised', False,
                   'no verification rules registered')

    return report


def verify_install_target(tool: str, target: Path) -> VerifyReport:
    """Verify the artefacts copied by `orquestrum install --tool <tool> --target <target>`.

    Project-level checks: agent files in the right place, no orphan placeholders.
    """
    report = VerifyReport(target=f'install:{tool} → {target}', root=target)

    if not target.is_dir():
        report.add('target directory exists', False,
                   f'{target} missing')
        return report
    report.add('target directory exists', True, str(target))

    if tool == 'claude-code':
        agents_dir = target / '.claude' / 'agents'
        _check_dir(report, '.claude/agents')
        _check_count(report, '.claude/agents', '*.md', EXPECTED_AGENT_COUNT)
        _check_file(report, '.claude/settings.json', min_bytes=10)
        _check_dir(report, '.sdd/docs')
        _check_dir(report, '.sdd/skills')
        _check_dir(report, '.sdd/scripts/hooks')

    elif tool == 'opencode':
        _check_dir(report, 'agents')
        _check_count(report, 'agents', '*.md', EXPECTED_AGENT_COUNT)
        _check_dir(report, 'docs')
        _check_dir(report, 'skills')
        # Critical post-install check: __OPENCODE_ROOT__ must be resolved
        unresolved = _count_placeholders(target, '__OPENCODE_ROOT__')
        report.add('__OPENCODE_ROOT__ placeholders resolved', unresolved == 0,
                   '' if unresolved == 0 else f'{unresolved} unresolved instances')

    elif tool == 'cursor':
        _check_dir(report, '.cursor/rules')
        _check_count(report, '.cursor/rules', '*.mdc',
                     EXPECTED_AGENT_COUNT, exact=False)

    elif tool == 'aider':
        _check_file(report, 'CONVENTIONS.md', min_bytes=500)

    elif tool == 'windsurf':
        _check_file(report, '.windsurfrules', min_bytes=500)

    else:
        report.add(f'tool "{tool}" recognised', False,
                   'no verification rules registered')

    return report


def _count_placeholders(root: Path, marker: str) -> int:
    """Count files under root whose contents still contain `marker`."""
    if not root.is_dir():
        return 0
    n = 0
    for md in root.rglob('*.md'):
        try:
            if marker in md.read_text(encoding='utf-8'):
                n += 1
        except (OSError, UnicodeDecodeError):
            continue
    return n


def render_summary(reports: list[VerifyReport]) -> str:
    """Render a compact one-line-per-report tally + grand total."""
    lines = []
    total_ok = 0
    total_fail = 0
    for r in reports:
        if r.passed:
            tally = f'{_GREEN}{len(r.checks)} ok{_NC}'
            total_ok += 1
        else:
            tally = f'{_RED}{r.fail_count} failed{_NC}, {len(r.checks) - r.fail_count} ok'
            total_fail += 1
        lines.append(f'  {tally:<24} {r.target}')

    summary_color = _GREEN if total_fail == 0 else _RED
    icon = '✓' if total_fail == 0 else '✗'
    lines.append('')
    lines.append(f'{summary_color}{icon} {total_ok}/{len(reports)} verifications passed{_NC}')
    return '\n'.join(lines)
