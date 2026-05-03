"""orquestrum.lib.manifest — read/write the project manifest.

Since v0.5 the manifest lives at `<project>/.orquestrum/manifest.md` so all
orquestrum-related files share a single root. The file is BOTH human-readable
AND machine-managed: everything above the marker is rewritten by the CLI;
everything below is preserved verbatim.

`init` migrates legacy `<project>/ORQUESTRUM.md` (≤v0.4) on first run by
reading from the old path, writing the new file, and deleting the old one.
"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from orquestrum import __version__


# Current location: <project>/.orquestrum/manifest.md
MANIFEST_DIR      = '.orquestrum'
MANIFEST_FILENAME = 'manifest.md'

# Legacy location used by ≤v0.4: <project>/ORQUESTRUM.md
LEGACY_MANIFEST_FILENAME = 'ORQUESTRUM.md'

MARKER = '<!-- ===== orquestrum:auto-managed-above ===== -->'

_DEFAULT_USER_SECTION = """\
<!-- Below this line is yours. Add notes, project-specific overrides, etc. -->

## Notes

(your notes here)
"""


@dataclass
class ManifestState:
    name: str
    tool: str | None = None
    provider: str | None = None
    default_tier: str = 'balanced'
    initialized: str | None = None      # ISO date
    last_sync: str | None = None        # ISO date
    history: list[str] = field(default_factory=list)   # ['2026-05-02 — initialized with claude-code']


def _today() -> str:
    return dt.date.today().isoformat()


def _render_managed(state: ManifestState) -> str:
    """Render the auto-managed section (everything above the marker)."""
    lines = [
        '# Orquestrum — Project Manifest',
        '',
        '> 🎼 This project is governed by Orquestrum.',
        '> Auto-managed by `orquestrum init`, `orquestrum update`, `orquestrum repos`.',
        '> Edit the `## Notes` section freely; everything above the marker is rewritten.',
        '',
        '## Configuration',
        '',
        '| Field | Value |',
        '|-------|-------|',
        f'| Project name | `{state.name}` |',
        f'| Tool         | `{state.tool or "—"}` |',
        f'| Provider     | `{state.provider or "—"}` |',
        f'| Default tier | `{state.default_tier}` |',
        f'| Initialized  | {state.initialized or "—"} |',
        f'| Last sync    | {state.last_sync or "—"} |',
        f'| Orquestrum   | v{__version__} |',
        '',
        '## Quick commands',
        '',
        '- `orquestrum web` — open the dashboard for this project',
        '- `orquestrum dashboard` — print metrics summary in terminal',
        '- `orquestrum audit attention` — review attention scores across artifacts',
        '- `orquestrum lint` — validate Orquestrum-installed agents',
        '- `orquestrum update` — re-run integration install + bump this manifest',
        '',
        '## For AI agents reading this file',
        '',
        'Orquestrum orchestrates agent-driven development in this project. Agents and',
        'skills are installed **globally** at `~/.claude/agents/` and `~/.claude/skills/`',
        '— never inside this project. Governance docs live at `~/.claude/sdd/docs/`',
        '(global) or `.claude/sdd/docs/` (project-level if installed locally).',
        'Per-project metrics live in `.orquestrum/metrics/` (gitignored).',
        '',
        '## History',
        '',
    ]
    if state.history:
        lines.extend([f'- {entry}' for entry in state.history])
    else:
        lines.append('- (none yet)')
    lines.append('')
    lines.append(MARKER)
    lines.append('')
    return '\n'.join(lines)


def _split_existing(text: str) -> tuple[str | None, str]:
    """Return (managed_section, user_section). If marker missing, user_section is empty."""
    if MARKER not in text:
        return None, ''
    above, below = text.split(MARKER, 1)
    return above, below.lstrip('\n')


def manifest_path(project_root: Path) -> Path:
    """Return the canonical manifest path: `<project>/.orquestrum/manifest.md`."""
    return project_root / MANIFEST_DIR / MANIFEST_FILENAME


def legacy_manifest_path(project_root: Path) -> Path:
    """Return the legacy manifest path used by ≤v0.4: `<project>/ORQUESTRUM.md`."""
    return project_root / LEGACY_MANIFEST_FILENAME


def write_manifest(project_root: Path, state: ManifestState) -> Path:
    """Write or update the manifest at `.orquestrum/manifest.md`, preserving
    the user-editable section if present."""
    path = manifest_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    user_section = _DEFAULT_USER_SECTION
    if path.exists():
        existing = path.read_text(encoding='utf-8')
        _, below = _split_existing(existing)
        if below.strip():
            user_section = below
    content = _render_managed(state) + user_section
    path.write_text(content, encoding='utf-8')
    return path


def read_manifest_state(project_root: Path) -> ManifestState | None:
    """Best-effort parse of the manifest to recover state. Returns None if
    missing.

    Looks at the new path first (`.orquestrum/manifest.md`) and falls back to
    the legacy path (`<project>/ORQUESTRUM.md`) so projects from before v0.5
    keep working until they're migrated. Only reads the Configuration table
    + History list — other fields come from `.orquestrum/config.toml`.
    """
    path = manifest_path(project_root)
    if not path.exists():
        legacy = legacy_manifest_path(project_root)
        if legacy.exists():
            path = legacy
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8')
    above, _ = _split_existing(text)
    if above is None:
        above = text  # no marker → treat full file as managed (legacy case)

    state = ManifestState(name=project_root.name)
    in_config = False
    in_history = False
    for line in above.split('\n'):
        s = line.strip()
        if s.startswith('## Configuration'):
            in_config, in_history = True, False
            continue
        if s.startswith('## History'):
            in_config, in_history = False, True
            continue
        if s.startswith('## '):
            in_config = in_history = False
            continue
        if in_config and s.startswith('|'):
            cells = [c.strip().strip('`') for c in s.strip('|').split('|')]
            if len(cells) < 2:
                continue
            field_name = cells[0].lower()
            value = cells[1] if cells[1] not in ('—', '-', '') else None
            if field_name == 'project name' and value:
                state.name = value
            elif field_name == 'tool':
                state.tool = value
            elif field_name == 'provider':
                state.provider = value
            elif field_name == 'default tier' and value:
                state.default_tier = value
            elif field_name == 'initialized':
                state.initialized = value
            elif field_name == 'last sync':
                state.last_sync = value
        elif in_history and s.startswith('- '):
            entry = s[2:].strip()
            if entry and entry != '(none yet)':
                state.history.append(entry)
    return state


def append_history(state: ManifestState, entry: str) -> None:
    """Append a new History entry prefixed with today's date."""
    state.history.append(f'{_today()} — {entry}')


def init_state(name: str, tool: str | None = None, provider: str | None = None) -> ManifestState:
    """Build a fresh ManifestState for a new init."""
    today = _today()
    state = ManifestState(name=name, tool=tool, provider=provider,
                          initialized=today, last_sync=today)
    if tool:
        append_history(state, f'initialized with `{tool}`'
                       + (f' (provider: {provider})' if provider else ''))
    else:
        append_history(state, 'initialized (no tool selected yet)')
    return state
