"""orquestrum.lib.install_plan — pre-flight classification for `install`.

Guarantees the user-facing contract: orquestrum only ever creates / updates
files it owns.

Plan classification — for every file in the staging dir, decide whether the
install would CREATE, UPDATE (orquestrum's own previous write), or LEAVE
UNCHANGED at the target. Reported back to the user so the action is never
opaque.

Single-owner protection (kept as no-op since v0.4): the previous design
guarded a few common project-level files (aider's `CONVENTIONS.md`,
windsurf's `.windsurfrules`) that orquestrum used to own outright. With
those tools dropped in v0.4, no current integration ships a single-owner
file; the dict below is left empty and the function still exposed so
re-introducing a guarded path stays a one-line change.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


# Tools where a single conventional file is fully owned by the integration.
# Empty in v0.4 (claude-code and opencode write into dedicated dirs); kept
# here as a documented extension point.
_SINGLE_OWNER_FILES: dict[str, list[tuple[str, str]]] = {}


# ANSI colours mirror the rest of the verify module so output is uniform.
_GREEN  = '\033[0;32m'
_YELLOW = '\033[1;33m'
_RED    = '\033[0;31m'
_DIM    = '\033[2m'
_NC     = '\033[0m'


@dataclass
class InstallPlan:
    """Classified preview of what `install_tool` would do."""

    new:        list[Path] = field(default_factory=list)  # didn't exist before
    update:     list[Path] = field(default_factory=list)  # exists, content differs
    unchanged:  list[Path] = field(default_factory=list)  # exists, identical
    user_owned: list[Path] = field(default_factory=list)  # exists, NOT ours

    @property
    def has_conflicts(self) -> bool:
        return bool(self.user_owned)

    @property
    def total(self) -> int:
        return len(self.new) + len(self.update) + len(self.unchanged) + len(self.user_owned)

    def render(self) -> str:
        """Pretty preview of the plan."""
        lines = []
        if self.new:
            lines.append(f'  {_GREEN}+ {len(self.new):>3} new{_NC} '
                         f'{_DIM}(files orquestrum will create){_NC}')
        if self.update:
            lines.append(f'  {_YELLOW}~ {len(self.update):>3} update{_NC} '
                         f'{_DIM}(orquestrum-owned, content changed){_NC}')
        if self.unchanged:
            lines.append(f'  {_DIM}= {len(self.unchanged):>3} unchanged '
                         f'(already in sync){_NC}')
        if self.user_owned:
            lines.append(f'  {_RED}! {len(self.user_owned):>3} conflict{_NC} '
                         f'{_DIM}(user files; install will refuse){_NC}')
            for p in self.user_owned:
                lines.append(f'      {_RED}{p}{_NC}')
        return '\n'.join(lines) if lines else '  (nothing to do)'


def detect_user_owned_files(tool: str, target: Path) -> list[Path]:
    """Return absolute paths of files at `target` that look user-owned.

    A file is "user-owned" when it lives at a single-owner path AND
    its first KB does not contain orquestrum's marker. Adapters embed the
    marker on every file they generate, so this is reliable for
    distinguishing user content from orquestrum's own previous installs.
    """
    found: list[Path] = []
    for rel, marker in _SINGLE_OWNER_FILES.get(tool, []):
        path = (target / rel).expanduser().resolve()
        if not path.is_file():
            continue
        try:
            head = path.read_text(encoding='utf-8', errors='replace')[:1024]
        except OSError:
            continue
        if marker not in head:
            found.append(path)
    return found


def classify_install(src: Path, target: Path,
                     ignore_filenames: set[str] | None = None) -> InstallPlan:
    """Walk every file under `src` and classify its destination state.

    `ignore_filenames` lets callers skip files that have a special copy
    path (e.g. claude-code's settings.json which is merged, not copied).
    """
    plan = InstallPlan()
    ignore = ignore_filenames or set()

    if not src.is_dir():
        return plan

    for src_file in src.rglob('*'):
        if not src_file.is_file():
            continue
        if src_file.name in ignore:
            continue
        rel = src_file.relative_to(src)
        dest = target / rel

        if not dest.exists():
            plan.new.append(dest)
            continue

        try:
            same = dest.read_bytes() == src_file.read_bytes()
        except OSError:
            same = False

        if same:
            plan.unchanged.append(dest)
        else:
            plan.update.append(dest)

    return plan


def render_user_conflict_error(tool: str, conflicts: list[Path]) -> str:
    """Build a multi-line, actionable error message for user-owned conflicts."""
    lines = [f'{tool}: refusing to overwrite user file(s) at the target.']
    for p in conflicts:
        lines.append(f'  • {p}')
        lines.append(f'    looks user-owned (no orquestrum marker line).')
    lines.append('')
    lines.append('Resolve one of these ways and re-run:')
    lines.append('  1. Move/rename the user file (e.g. CONVENTIONS-mine.md), then re-run.')
    lines.append('  2. Pass --force to overwrite anyway (your file will be lost).')
    return '\n'.join(lines)
