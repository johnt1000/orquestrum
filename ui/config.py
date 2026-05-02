"""config.py — UI mode resolution + ORQ_ROOT validation.

Two modes:
  - framework: UI runs in the Orquestrum repo and manages multiple targets
                (state in ~/.orquestrum/targets.json)
  - project:   UI runs inside one target project, focused on its .orquestrum/ dir

Mode is resolved (in priority order):
  1. CLI --mode flag (set by orquestrum/commands/web.py)
  2. ORQ_MODE env var
  3. auto-detect: presence of agents/ + skills/ + orquestrum/ → framework, else project
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Mode = Literal['framework', 'project']

DEFAULT_PORT = 7700


@dataclass(frozen=True)
class UIConfig:
    mode:                 Mode
    root:                 Path
    metrics_dir:          Path | None    # only set in project mode
    targets_path:         Path | None    # only set in framework mode
    port:                 int
    linked_project_root:  Path | None = None  # nearest ancestor with .orquestrum/
    framework_root:       Path | None = None  # canonical Orquestrum source

    @property
    def is_framework(self) -> bool:
        return self.mode == 'framework'

    @property
    def is_project(self) -> bool:
        return self.mode == 'project'

    @property
    def is_linked(self) -> bool:
        """True when root (or an ancestor) has a .orquestrum/ directory."""
        return self.linked_project_root is not None


def auto_detect_mode(root: Path) -> Mode:
    """If root looks like the Orquestrum repo (has agents/, skills/, orquestrum/lib/),
    treat it as framework mode. Otherwise project mode.
    """
    framework_markers = [
        root / 'agents',
        root / 'skills',
        root / 'orquestrum' / 'lib',
        root / 'docs' / 'agent-context',
    ]
    if all(p.exists() for p in framework_markers):
        return 'framework'
    return 'project'


def resolve(
    *,
    mode_arg:   str | None = None,
    root_arg:   str | None = None,
    port_arg:   int | None = None,
) -> UIConfig:
    """Resolve config from CLI args + env vars + auto-detection.

    Raises ValueError on misconfiguration so the caller can print a clear error.
    """
    raw_root = root_arg or os.environ.get('ORQ_ROOT') or '.'
    root     = Path(raw_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'ORQ_ROOT does not exist or is not a directory: {root}')

    raw_mode = (mode_arg or os.environ.get('ORQ_MODE') or '').strip().lower()
    if raw_mode in ('framework', 'project'):
        mode: Mode = raw_mode  # type: ignore[assignment]
    elif raw_mode == '':
        mode = auto_detect_mode(root)
    else:
        raise ValueError(f'Invalid ORQ_MODE: {raw_mode!r} (expected: framework | project)')

    metrics_dir:          Path | None = None
    targets_path:         Path | None = None
    linked_project_root:  Path | None = None
    framework_root_path:  Path | None = None

    if mode == 'project':
        from orquestrum.lib.paths import find_project_root, canonical_root
        linked_project_root = find_project_root(root)
        framework_root_path = canonical_root()
        # metrics live in the linked project, or fall back to root (may not exist yet)
        metrics_dir = (linked_project_root or root) / '.orquestrum' / 'metrics'
    else:
        # Framework mode requires the canonical layout
        for required in ('agents', 'skills', 'orquestrum'):
            if not (root / required).is_dir():
                raise ValueError(
                    f'Framework mode at {root} but {required}/ is missing. '
                    f'Use --mode project or run from the Orquestrum repo root.'
                )
        targets_path = Path('~/.orquestrum/targets.json').expanduser()
        framework_root_path = root  # root IS the canonical framework in framework mode

    port = port_arg or int(os.environ.get('ORQ_PORT', DEFAULT_PORT))

    return UIConfig(
        mode=mode,
        root=root,
        metrics_dir=metrics_dir,
        targets_path=targets_path,
        port=port,
        linked_project_root=linked_project_root,
        framework_root=framework_root_path,
    )
