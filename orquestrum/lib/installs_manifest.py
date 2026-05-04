"""orquestrum.lib.installs_manifest — persistent record of what we installed.

Single source of truth for "which files does orquestrum own at each target?".
Lives at `~/.orquestrum/installs.json` (override via `$ORQUESTRUM_HOME`).

Why it exists
-------------
The CLI must guarantee: orquestrum only manipulates files it created.
Without a manifest, uninstall has to guess via heuristics (blanket
`rmtree(.sdd)`, "agent files matching this list", …) which works in the
common case but loses user content placed inside orquestrum-managed dirs.

With this manifest the rule is exact: on uninstall, read the install
record, remove only the files listed (skipping anything missing or
externally modified beyond recognition), then attempt rmdir on the
directories orquestrum created — non-empty dirs (because user added
content) survive untouched.

Schema (forward-compatible via `schema_version`)
------------------------------------------------
```
{
  "schema_version": 1,
  "installs": [
    {
      "target":             "/abs/target/path",
      "tool":               "opencode",
      "orquestrum_version": "0.3.0",
      "installed_at":       "2026-05-03T10:30:00",
      "files":              ["agents/helm-the-architect.md", …],
      "directories":        ["agents", "skills", …]
    },
    …
  ]
}
```

Files and directories are stored relative to `target`. Lookups are by the
`(target, tool)` pair; we permit multiple tools per target (a single
project initialised for several IDEs) but only one record per pair —
re-installing the same tool replaces its entry.
"""
from __future__ import annotations
import datetime as dt
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from orquestrum import __version__
from orquestrum.lib.paths import orquestrum_home


_MANIFEST_FILENAME = 'installs.json'
_SCHEMA_VERSION = 1


@dataclass
class ToolInstall:
    """One tool-at-target record. Paths are relative to `target`."""
    target:             str
    tool:               str
    orquestrum_version: str
    installed_at:       str
    files:              list[str] = field(default_factory=list)
    directories:        list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolInstall':
        return cls(
            target=data['target'],
            tool=data['tool'],
            orquestrum_version=data.get('orquestrum_version', ''),
            installed_at=data.get('installed_at', ''),
            files=list(data.get('files') or []),
            directories=list(data.get('directories') or []),
        )


def _manifest_path() -> Path:
    return orquestrum_home() / _MANIFEST_FILENAME


def _load_raw() -> dict:
    path = _manifest_path()
    if not path.is_file():
        return {'schema_version': _SCHEMA_VERSION, 'installs': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'schema_version': _SCHEMA_VERSION, 'installs': []}
    if not isinstance(data, dict) or 'installs' not in data:
        return {'schema_version': _SCHEMA_VERSION, 'installs': []}
    return data


def _save_raw(data: dict) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n',
                    encoding='utf-8')


def _normalize_target(target: Path) -> str:
    return str(target.expanduser().resolve())


# ─── public API ─────────────────────────────────────────────────────────────


def list_installs() -> list[ToolInstall]:
    """Return every install record currently known."""
    data = _load_raw()
    return [ToolInstall.from_dict(d) for d in data.get('installs', [])]


def get_install(tool: str, target: Path) -> ToolInstall | None:
    """Return the (tool, target) record, or None if not present."""
    abs_target = _normalize_target(target)
    for entry in list_installs():
        if entry.tool == tool and entry.target == abs_target:
            return entry
    return None


def record_install(tool: str, target: Path,
                   files: list[Path], directories: list[Path]) -> ToolInstall:
    """Persist a record of what `install_tool` just created.

    `files` and `directories` are absolute paths under `target`; we store
    them relative so the manifest survives `target` being moved (rare but
    possible). Existing record for the same (tool, target) is replaced.
    """
    abs_target = Path(_normalize_target(target))
    rec = ToolInstall(
        target=str(abs_target),
        tool=tool,
        orquestrum_version=__version__,
        installed_at=dt.datetime.now().replace(microsecond=0).isoformat(),
        files=sorted(_relpath(f, abs_target) for f in files),
        directories=sorted(_relpath(d, abs_target) for d in directories),
    )

    data = _load_raw()
    entries = [d for d in data.get('installs', [])
               if not (d.get('tool') == tool and d.get('target') == str(abs_target))]
    entries.append(rec.to_dict())
    data['installs'] = entries
    data['schema_version'] = _SCHEMA_VERSION
    _save_raw(data)
    return rec


def remove_install(tool: str, target: Path) -> ToolInstall | None:
    """Drop a record from the manifest. Returns what was removed (or None)."""
    abs_target = _normalize_target(target)
    data = _load_raw()
    new_entries = []
    removed: ToolInstall | None = None
    for d in data.get('installs', []):
        if d.get('tool') == tool and d.get('target') == abs_target:
            removed = ToolInstall.from_dict(d)
        else:
            new_entries.append(d)
    if removed is not None:
        data['installs'] = new_entries
        _save_raw(data)
    return removed


def _relpath(p: Path, base: Path) -> str:
    """Path-string of `p` relative to `base`. Falls back to absolute when
    `p` is outside `base` (which shouldn't happen for installs but we
    keep the manifest readable rather than raising)."""
    p = p.expanduser().resolve()
    base = base.expanduser().resolve()
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


# ─── helpers used by install_tool() to build the file/dir lists ─────────────


def enumerate_writes(src: Path, target: Path,
                     ignore_filenames: set[str] | None = None) -> tuple[list[Path], list[Path]]:
    """Walk `src` and return:
      - absolute paths of every file `install_tool` will create at `target`
      - absolute paths of every directory `install_tool` will create at `target`
        (i.e. dirs that do NOT exist yet — pre-existing dirs are user's)
    """
    files: list[Path] = []
    dirs: list[Path] = []
    ignore = ignore_filenames or set()
    target = target.expanduser().resolve()

    if not src.is_dir():
        return files, dirs

    for src_path in src.rglob('*'):
        rel = src_path.relative_to(src)
        dest = target / rel
        if src_path.is_dir():
            if not dest.exists():
                dirs.append(dest)
        elif src_path.is_file():
            if src_path.name in ignore:
                continue
            files.append(dest)
    return files, dirs


def surgical_uninstall(tool: str, target: Path) -> tuple[list[str], list[str]]:
    """Remove only the files/dirs recorded for (tool, target).

    Returns (removed_files, removed_dirs) with paths relative to `target`.
    Directories are removed deepest-first and only when empty, so any
    user-added content under them is preserved.

    The manifest entry is dropped on completion. Falls through to an empty
    return if no manifest entry exists — caller decides whether to fall back
    to the legacy heuristic.
    """
    record = get_install(tool, target)
    if record is None:
        return [], []

    abs_target = Path(_normalize_target(target))
    removed_files: list[str] = []
    for rel in record.files:
        f = abs_target / rel
        if f.is_file():
            try:
                f.unlink()
                removed_files.append(rel)
            except OSError:
                pass

    # Deepest first so a dir empties before its parent is tried.
    removed_dirs: list[str] = []
    for rel in sorted(record.directories, key=lambda d: d.count('/'), reverse=True):
        d_path = abs_target / rel
        if d_path.is_dir():
            try:
                d_path.rmdir()  # only succeeds when empty
                removed_dirs.append(rel)
            except OSError:
                # Not empty (user dropped content here) — leave it.
                pass

    remove_install(tool, target)
    return removed_files, removed_dirs


# ─── pruning ───────────────────────────────────────────────────────────────


# Tools that have been retired from orquestrum. Entries for these in the
# manifest are dead weight (the tool's adapter no longer exists) and any
# uninstall attempt would fail. Treat them as prunable by default.
RETIRED_TOOLS: frozenset[str] = frozenset({'aider', 'cursor', 'windsurf'})


def classify_stale(records: list[ToolInstall]) -> dict[str, list[ToolInstall]]:
    """Partition a list of install records into three buckets:

    - `stale_target`  — target directory no longer exists on disk
    - `retired_tool`  — tool was removed in v0.4 (aider/cursor/windsurf)
    - `valid`         — target exists AND tool is still supported

    Useful both for the `installs prune` CLI and for the doctor health-check
    that surfaces a warning when stale entries dominate the manifest.
    """
    out: dict[str, list[ToolInstall]] = {
        'stale_target': [],
        'retired_tool': [],
        'valid':        [],
    }
    for r in records:
        # Retired-tool check first — a retired tool's record is always
        # prunable regardless of whether the target still exists.
        if r.tool in RETIRED_TOOLS:
            out['retired_tool'].append(r)
        elif not Path(r.target).is_dir():
            out['stale_target'].append(r)
        else:
            out['valid'].append(r)
    return out


def prune_stale(*, dry_run: bool = False) -> tuple[int, int, int]:
    """Remove every install record whose target directory no longer exists,
    plus every record for a retired tool. Returns
    `(removed_stale, removed_retired, kept)`.

    `dry_run=True` returns the same counts but does NOT write the manifest —
    used by `installs prune --dry-run` and by the doctor check. The caller
    is responsible for printing a human-friendly report.

    Backup of the prior manifest is the caller's responsibility (the CLI
    writes a `.bak.<date>` sibling before invoking this).
    """
    records = list_installs()
    buckets = classify_stale(records)
    removed_stale = len(buckets['stale_target'])
    removed_retired = len(buckets['retired_tool'])
    kept = len(buckets['valid'])

    if not dry_run and (removed_stale or removed_retired):
        data = {
            'schema_version': _SCHEMA_VERSION,
            'installs': [r.to_dict() for r in buckets['valid']],
        }
        _save_raw(data)
    return removed_stale, removed_retired, kept
