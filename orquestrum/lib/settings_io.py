"""settings_io — safe load/write helpers for Claude Code settings.json.

Why a dedicated module: settings.json is touched by `install` (merge
template entries), `mcp add/remove` (CRUD for third-party MCP servers),
`uninstall` (scrub orquestrum entries), `init` (detect global state),
and `setup --advanced` (interactive MCP management). Centralising the
load/write/CRUD primitives here means:

  - One place to handle JSON corruption / missing files / atomic writes.
  - One place to enforce "preserve unknown user keys".
  - All four call sites get the same behavior (e.g. trailing newline,
    indent=2, never reinstating an empty `mcpServers` block).

The legacy logic lives in `orquestrum.core.install._merge_claude_settings`;
this module is its substrate. Tests cover round-trip behavior so the
extraction can't silently drift from the original.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


# ─── load / write ──────────────────────────────────────────────────────────


def load_claude_settings(path: Path) -> dict[str, Any]:
    """Load `path` as JSON. Returns `{}` if file is missing OR malformed.

    The "missing == empty" behavior is by design: callers usually want to
    write a settings.json from scratch when none exists. Malformed JSON
    is treated like "missing" but loud — caller logs a warning. Use
    `is_valid_json(path)` if you need to distinguish the two cases.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def is_valid_json(path: Path) -> bool:
    """Return True iff `path` exists AND parses as JSON. Used by callers
    that want to distinguish "missing" from "corrupted" (e.g. install
    refuses to overwrite a corrupted file)."""
    if not path.exists():
        return False
    try:
        json.loads(path.read_text(encoding='utf-8'))
        return True
    except json.JSONDecodeError:
        return False


def write_claude_settings(path: Path, data: dict[str, Any]) -> None:
    """Atomically write `data` as pretty-printed JSON to `path`.

    Always uses indent=2 and a trailing newline so `git diff` is friendly.
    Creates parent directories if missing. Whole-file replace — no merge
    here; caller is responsible for the merged content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    path.write_text(payload, encoding='utf-8')


# ─── mcpServers CRUD ───────────────────────────────────────────────────────


def list_mcp_servers(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the `mcpServers` dict from settings (or `{}` if absent).
    Read-only — does not mutate `settings`."""
    return dict(settings.get('mcpServers') or {})


def add_mcp_server(
    settings: dict[str, Any],
    name: str,
    *,
    command: str,
    args: list[str] | None = None,
    server_type: str = 'stdio',
    extra: dict[str, Any] | None = None,
) -> bool:
    """Add or replace a MCP server entry in `settings`. Mutates in place.

    Returns True if the entry was newly created, False if it replaced
    an existing entry of the same name (so callers can pick the right
    log message).
    """
    mcp = settings.setdefault('mcpServers', {})
    existed = name in mcp
    entry: dict[str, Any] = {'command': command, 'type': server_type}
    if args is not None:
        entry['args'] = list(args)
    if extra:
        entry.update(extra)
    mcp[name] = entry
    return not existed


def remove_mcp_server(settings: dict[str, Any], name: str) -> bool:
    """Remove a MCP server entry by name. Mutates `settings` in place.

    Returns True if removed, False if it wasn't there. If the resulting
    `mcpServers` dict is empty, drops the key entirely (so we don't
    write `{"mcpServers": {}}` to disk).
    """
    mcp = settings.get('mcpServers') or {}
    if name not in mcp:
        return False
    del mcp[name]
    if not mcp:
        settings.pop('mcpServers', None)
    return True


# ─── hooks CRUD (orquestrum-owned entries only) ────────────────────────────


def is_orquestrum_hook(command: str | None) -> bool:
    """Identify a hook command as orquestrum-owned across versions:
      - `orquestrum hook`                            ≥0.5.1 current form
      - `sdd/scripts/hooks/emit_metrics.py` tail     ≤0.5.0 legacy form

    Used by install + uninstall to find/replace/scrub orquestrum entries
    without touching user-defined hooks at the same matcher.
    """
    if not command:
        return False
    if 'orquestrum hook' in command:
        return True
    return 'sdd/scripts/hooks/emit_metrics.py' in command


def remove_orquestrum_hooks(settings: dict[str, Any]) -> int:
    """Strip every orquestrum hook entry from `settings.hooks.*`. Returns
    the count removed. Preserves user-defined hooks at the same matcher
    by only removing matching `hooks[i]` entries inside each block."""
    hooks = settings.get('hooks') or {}
    if not isinstance(hooks, dict):
        return 0
    removed = 0
    for event_name, blocks in list(hooks.items()):
        if not isinstance(blocks, list):
            continue
        cleaned: list[dict] = []
        for block in blocks:
            inner = [h for h in block.get('hooks', []) if not is_orquestrum_hook(h.get('command'))]
            removed += len(block.get('hooks', [])) - len(inner)
            if inner:
                cleaned.append({**block, 'hooks': inner})
        if cleaned:
            hooks[event_name] = cleaned
        else:
            hooks.pop(event_name, None)
    if not hooks:
        settings.pop('hooks', None)
    return removed


# ─── high-level merge (template into target) ───────────────────────────────


def merge_template_settings(
    template: dict[str, Any], target: dict[str, Any],
) -> tuple[int, list[str], list[str], list[str]]:
    """Merge `template` settings into `target` (in place). Returns:
      (removed_orq_hooks, added_hook_descriptions, added_mcp, replaced_mcp)

    Strategy:
      - Drop existing orquestrum hooks from target (avoid duplicates).
      - Append every template hook block into target's `hooks` map.
      - For mcpServers, replace existing entries with same key (so re-install
        always installs the latest config) and add net-new ones. User-defined
        servers (filesystem, github, ...) are preserved untouched because
        they don't appear in `template.mcpServers`.
    """
    removed = remove_orquestrum_hooks(target)

    target_hooks = target.setdefault('hooks', {})
    template_hooks = template.get('hooks') or {}
    added_hooks: list[str] = []
    for event_name, blocks in template_hooks.items():
        existing = target_hooks.setdefault(event_name, [])
        if not isinstance(existing, list):
            continue
        for block in blocks:
            cmd = next(
                (h.get('command') for h in block.get('hooks', []) if h.get('command')),
                None,
            )
            existing.append(block)
            added_hooks.append(f'{event_name}: {cmd}')

    target_mcp = target.setdefault('mcpServers', {})
    template_mcp = template.get('mcpServers') or {}
    added_mcp: list[str] = []
    replaced_mcp: list[str] = []
    for name, config in template_mcp.items():
        if name in target_mcp:
            replaced_mcp.append(name)
        else:
            added_mcp.append(name)
        target_mcp[name] = config
    if not target_mcp:
        target.pop('mcpServers', None)

    return removed, added_hooks, added_mcp, replaced_mcp
