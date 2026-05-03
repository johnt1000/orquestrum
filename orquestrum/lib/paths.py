"""orquestrum.lib.paths — path resolution helpers for the CLI.

Five concepts:
  - canonical_root         : the Orquestrum repo itself (`agents/`, `skills/`,
                             `docs/agent-context/` on disk). Found via cwd-walk
                             or package-relative — None when CLI was installed
                             from a wheel and the user is outside the repo.
  - canonical_assets_root  : best source of canonical SDD content. Prefers a
                             dev-mode repo (so contributors edit directly) but
                             falls back to the wheel-bundled `_assets/` tree.
                             Never None.
  - convert_output_root    : where `convert` writes its `integrations/<tool>/`
                             intermediate output. Dev-mode → repo
                             `integrations/`; wheel-mode → user cache under
                             `~/.orquestrum/cache/integrations/`. Override via
                             `$ORQUESTRUM_CACHE`.
  - project_root           : a target project directory (contains
                             `.orquestrum/`).
  - orquestrum_home        : the user's global state dir (`~/.orquestrum/`).
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
    presence of agents/, skills/, orquestrum/lib/, docs/agent-context/.
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


# ── Source / output split ──────────────────────────────────────────────────
#
# `convert` reads canonical SDD content (agents/skills/docs/bundle) and writes
# generated integration packages. Pre-0.3 these both lived inside the repo.
# Now the read side is satisfied by the wheel bundle in user-mode and the
# write side goes to a per-user cache so the CLI can run from any cwd.


def canonical_assets_root() -> Path:
    """Return the on-disk root that holds `agents/`, `skills/`, `docs/`,
    `bundle/`, `pinned_refs.toml`.

    Resolution order:
      1. Dev mode: a canonical repo found via cwd-walk (contributors edit
         source directly).
      2. Wheel mode: the bundled `orquestrum/_assets/` tree.

    Never returns None — the wheel always ships `_assets/`.
    """
    repo = find_canonical_root()
    if repo is not None and (repo / 'agents').is_dir():
        return repo
    from orquestrum.lib.assets import assets_root
    return assets_root()


def convert_output_root() -> Path:
    """Return the directory where `orquestrum convert` writes its integration
    packages.

    Resolution order:
      1. `$ORQUESTRUM_CACHE` env var (explicit override, e.g. for CI).
      2. Dev mode: `<canonical>/integrations/` so `make convert` keeps the
         legacy contributor flow.
      3. User mode: `<orquestrum_home>/cache/integrations/`.
    """
    explicit = os.environ.get('ORQUESTRUM_CACHE')
    if explicit:
        return Path(explicit).expanduser()
    repo = find_canonical_root()
    if repo is not None and (repo / 'agents').is_dir():
        return repo / 'integrations'
    return orquestrum_home() / 'cache' / 'integrations'


def pinned_refs_path() -> Path:
    """Return the path to `pinned_refs.toml` (used by `orquestrum deps`).

    Dev mode → repo file (writeable, used by `--update-pins`).
    Wheel mode → bundled, read-only copy.
    """
    repo = find_canonical_root()
    if repo is not None and (repo / 'pinned_refs.toml').is_file():
        return repo / 'pinned_refs.toml'
    from orquestrum.lib.assets import assets_root
    return assets_root() / 'pinned_refs.toml'


def is_dev_mode() -> bool:
    """True when the CLI is running from a clone of the canonical repo —
    used to gate operations that only make sense for contributors
    (e.g. `--update-pins`, writing audit baselines into `docs/baselines/`).
    """
    repo = find_canonical_root()
    return repo is not None and (repo / 'agents').is_dir()
