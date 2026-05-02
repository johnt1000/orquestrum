"""orquestrum.lib.paths — path resolution helpers for the CLI.

Three concepts:
  - canonical_root  : the Orquestrum repo itself (where agents/, skills/ live).
                      Located via the installed package or via search-up from cwd.
  - project_root    : a target project directory (contains .orquestrum/).
  - orquestrum_home : the user's global state dir (~/.orquestrum/).
"""
from __future__ import annotations
import os
from pathlib import Path


def orquestrum_home() -> Path:
    """Return ~/.orquestrum/ — created if missing."""
    p = Path(os.environ.get('ORQUESTRUM_HOME') or '~/.orquestrum').expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default cwd) looking for a directory containing
    `.orquestrum/`. Return the project root, or None if not found.
    """
    cur = (start or Path.cwd()).expanduser().resolve()
    for parent in [cur, *cur.parents]:
        if (parent / '.orquestrum').is_dir():
            return parent
    return None


def find_canonical_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default cwd) looking for the Orquestrum repo —
    presence of agents/, skills/, scripts/lib/, docs/agent-context/.
    Return the canonical root, or None.
    """
    cur = (start or Path.cwd()).expanduser().resolve()
    markers = ('agents', 'skills', 'orquestrum/lib', 'docs/agent-context')
    for parent in [cur, *cur.parents]:
        if all((parent / m).exists() for m in markers):
            return parent
    return None


def canonical_root_from_package() -> Path | None:
    """If the installed orquestrum package is editable, the canonical source
    lives next to it (sibling of the orquestrum/ dir). Returns that path
    or None when installed from a wheel where source is unavailable.
    """
    pkg_root = Path(__file__).resolve().parent.parent.parent  # orquestrum/lib/paths.py → repo root
    markers = ('agents', 'skills', 'orquestrum/lib', 'docs/agent-context')
    if all((pkg_root / m).exists() for m in markers):
        return pkg_root
    return None


def canonical_root() -> Path | None:
    """Best-effort canonical root: prefer cwd-based search (developer is in
    the repo), fall back to package-based detection (CLI installed globally).
    """
    return find_canonical_root() or canonical_root_from_package()
