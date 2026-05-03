"""orquestrum.lib.assets — read bundled SDD assets from inside the wheel.

The canonical source (agents/, skills/, docs/agent-context/, docs/governance/,
bundle/, pinned_refs.toml) is force-included into orquestrum/_assets/ at wheel
build time (see pyproject.toml [tool.hatch.build.targets.wheel.force-include]).

This module is the single point of access. Use it whenever you need to READ
canonical SDD content; write paths go through `lib.paths`.

Override via `$ORQUESTRUM_ASSETS_ROOT` for tests, CI runs against an editable
checkout that lacks `_assets/`, or power users pointing at a fork.

Note on zip-imports: hatchling produces an unpacked wheel and `pip` / `uv tool
install` both extract it to a real directory, so `Path(str(files(...)))` works.
If a downstream consumer ever zip-imports this package, switch the helper to
`importlib.resources.as_file()` with a context manager.
"""
from __future__ import annotations
import os
from importlib.resources import files
from pathlib import Path


_ASSETS_DIR = '_assets'


def assets_root() -> Path:
    """Return the absolute path of the bundled `_assets/` directory.

    `$ORQUESTRUM_ASSETS_ROOT` takes precedence — useful in CI to point at a
    pre-built bundle, or in tests to simulate wheel mode without rebuilding.
    """
    explicit = os.environ.get('ORQUESTRUM_ASSETS_ROOT')
    if explicit:
        return Path(explicit).expanduser()
    return Path(str(files('orquestrum').joinpath(_ASSETS_DIR)))


def has_bundled_assets() -> bool:
    """True when the wheel-bundled asset tree is present and non-empty."""
    root = assets_root()
    return root.is_dir() and (root / 'agents').is_dir()
