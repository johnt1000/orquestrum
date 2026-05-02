"""orquestrum.lib.registry — read/write ~/.orquestrum/registry.toml.

Single source of truth for the global list of Orquestrum-linked projects.
TOML format chosen for human-readability (consistent with pinned_refs.toml).
"""
from __future__ import annotations
import datetime as dt
from pathlib import Path
import tomllib

from orquestrum.lib.paths import orquestrum_home


REGISTRY_FILENAME = 'registry.toml'

_HEADER = """# Orquestrum global project registry.
# Auto-managed by `orquestrum init`, `orquestrum update`, and `orquestrum repos`.
# Keep in your dotfiles backup if you want portability.

"""


def _registry_path() -> Path:
    return orquestrum_home() / REGISTRY_FILENAME


def load_registry() -> list[dict]:
    """Return list of project dicts. Empty list if file missing."""
    path = _registry_path()
    if not path.exists():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError:
        return []
    return list(data.get('projects', []))


def _quote(value: str | None) -> str:
    if value is None:
        return ''
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _dump_registry(projects: list[dict]) -> str:
    lines = [_HEADER]
    for p in projects:
        lines.append('[[projects]]')
        lines.append(f'name        = {_quote(p.get("name"))}')
        lines.append(f'path        = {_quote(p.get("path"))}')
        if p.get('tool'):
            lines.append(f'tool        = {_quote(p["tool"])}')
        if p.get('provider'):
            lines.append(f'provider    = {_quote(p["provider"])}')
        if p.get('linked_at'):
            lines.append(f'linked_at   = {_quote(p["linked_at"])}')
        if p.get('last_sync'):
            lines.append(f'last_sync   = {_quote(p["last_sync"])}')
        lines.append('')
    return '\n'.join(lines)


def _save_registry(projects: list[dict]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_registry(projects), encoding='utf-8')


def _today() -> str:
    return dt.date.today().isoformat()


def find_by_path(path: Path) -> dict | None:
    abs_path = str(path.expanduser().resolve())
    for proj in load_registry():
        if proj.get('path') == abs_path:
            return proj
    return None


def find_by_name(name: str) -> dict | None:
    for proj in load_registry():
        if proj.get('name') == name:
            return proj
    return None


def register_project(
    *,
    name: str,
    path: Path,
    tool: str | None = None,
    provider: str | None = None,
) -> dict:
    """Add or update a project entry. Idempotent — same path → update fields."""
    abs_path = str(path.expanduser().resolve())
    projects = load_registry()

    existing_idx = next((i for i, p in enumerate(projects)
                         if p.get('path') == abs_path), None)
    today = _today()

    if existing_idx is not None:
        # Update in place
        existing = projects[existing_idx]
        existing['name'] = name
        if tool:
            existing['tool'] = tool
        if provider:
            existing['provider'] = provider
        existing['last_sync'] = today
        # linked_at preserved
        _save_registry(projects)
        return existing

    # New entry — handle name collision (different path with same name)
    if any(p.get('name') == name for p in projects):
        suffix = 2
        while any(p.get('name') == f'{name}-{suffix}' for p in projects):
            suffix += 1
        name = f'{name}-{suffix}'

    entry = {
        'name': name,
        'path': abs_path,
        'linked_at': today,
        'last_sync': today,
    }
    if tool:
        entry['tool'] = tool
    if provider:
        entry['provider'] = provider

    projects.append(entry)
    _save_registry(projects)
    return entry


def unregister_project(*, name: str | None = None, path: Path | None = None) -> dict | None:
    """Remove an entry by name or path. Returns the removed entry, or None."""
    projects = load_registry()
    target_idx = None
    if path is not None:
        abs_path = str(path.expanduser().resolve())
        target_idx = next((i for i, p in enumerate(projects)
                           if p.get('path') == abs_path), None)
    elif name is not None:
        target_idx = next((i for i, p in enumerate(projects)
                           if p.get('name') == name), None)
    if target_idx is None:
        return None
    removed = projects.pop(target_idx)
    _save_registry(projects)
    return removed


def update_last_sync(path: Path) -> None:
    """Bump last_sync timestamp for the project at this path. No-op if not registered."""
    abs_path = str(path.expanduser().resolve())
    projects = load_registry()
    for p in projects:
        if p.get('path') == abs_path:
            p['last_sync'] = _today()
            _save_registry(projects)
            return
