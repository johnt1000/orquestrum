"""init_impl — implementation of `orquestrum init`.

Since v0.5 the `init` command is config-only: it bootstraps `<project>/
.orquestrum/` (config + manifest + metrics dir + global registry entry)
and asks 3 interactive questions about optional integrations:

  1. Metrics hook        — install Stop hook globally or per-project
  2. MCP server          — register `mcpServers.orquestrum` in settings.json
  3. Claude-code agents  — install the 8 subagents (always GLOBAL, never
                            project-level — agents must not pollute the repo)

Every artifact written by `init` lives under `.orquestrum/` (so a single
`rm -rf .orquestrum/` cleans up the project) EXCEPT the optional
`~/.claude/settings.json` and `~/.claude/agents/` paths, which target the
user's Claude Code config dir intentionally — those are the user's, not
the project's.

Migration: ≤v0.4 left `<project>/ORQUESTRUM.md` at the root. On first
run the new `init` migrates that file's content into
`.orquestrum/manifest.md` and removes the root file.
"""
from __future__ import annotations
import datetime as dt
import shutil
from pathlib import Path
from typing import Literal

from orquestrum.lib import manifest, paths, prompts, registry


Scope = Literal['global', 'project', 'skip']


_CONFIG_TOML_TEMPLATE = """\
# Created by `orquestrum init`. Safe to commit.
[project]
name      = "{name}"
created   = "{created}"

[metrics]
tier    = "balanced"
enabled = {metrics_enabled}
scope   = "{metrics_scope}"

[mcp]
enabled = {mcp_enabled}
scope   = "{mcp_scope}"

[agents]
# false = agents not installed by `init`; run
#   orquestrum install --tool claude-code --target ~
# whenever you want them. Always installed GLOBAL — never to the project.
installed = {agents_installed}
"""

_GITIGNORE = """# Auto-managed by orquestrum — do not edit.
# Everything below is locally generated, not relevant to the project, OR
# can leak ephemeral session data. config.toml + manifest.md ARE meant to
# be committed.
metrics/
integrations/
services/
plugins/
*.tmp
*.candidate.md
session.json
events.jsonl
dashboard.{md,html}
"""


# ─── prompts ────────────────────────────────────────────────────────────────


def _ask_scope(label: str, *, interactive: bool, default: Scope) -> Scope:
    """Ask whether to install the named hook/server globally, per-project,
    or skip. Returns the chosen scope.
    """
    choice = prompts.ask_choice(
        f'  Where should {label} be installed?',
        [
            ('g', 'global   — ~/.claude/settings.json (all projects)'),
            ('p', 'project  — ./.claude/settings.json (this project only)'),
            ('s', 'skip     — do not install now (you can re-run init later)'),
        ],
        default={'global': 'g', 'project': 'p', 'skip': 's'}[default],
        interactive=interactive,
    )
    return {'g': 'global', 'p': 'project', 's': 'skip'}[choice]


def _detect_global_state() -> dict[str, bool]:
    """Inspect ~/.claude/settings.json to see whether `setup` already
    registered the metrics hook + orquestrum MCP. Returns a dict with
    `hook_registered` and `mcp_registered` flags. Used to skip
    redundant prompts in `init` after the user already ran `setup`.

    Reads only — never writes. Missing file = both False (no global setup).
    """
    from orquestrum.lib import settings_io
    settings_path = Path.home() / '.claude' / 'settings.json'
    settings = settings_io.load_claude_settings(settings_path)

    # Hook detection: look for the orquestrum stop hook command
    hook_registered = False
    for blocks in (settings.get('hooks') or {}).values():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            for h in block.get('hooks', []):
                if settings_io.is_orquestrum_hook(h.get('command')):
                    hook_registered = True
                    break
            if hook_registered:
                break
        if hook_registered:
            break

    # MCP detection: look for the orquestrum entry under mcpServers
    mcp_servers = settings.get('mcpServers') or {}
    mcp_registered = 'orquestrum' in mcp_servers

    return {'hook_registered': hook_registered,
            'mcp_registered':  mcp_registered}


def _gather_choices(*, interactive: bool, per_project: bool = False) -> dict:
    """Run the three prompts and return a dict with the user's selections.

    Auto-skips the metrics hook + MCP prompts when global registration
    already exists (set by `orquestrum setup`). Pass `per_project=True`
    to force the prompts even when global is registered (rare edge case
    where the user wants project-scoped overrides).

    In non-interactive mode all defaults are honoured: metrics + MCP enabled
    globally, agents NOT installed.
    """
    print()
    print('Optional integrations (skip any with [s]):')
    print()

    global_state = _detect_global_state() if not per_project else {
        'hook_registered': False, 'mcp_registered': False,
    }

    # ── Metrics hook ─────────────────────────────────────────────────
    if global_state['hook_registered']:
        print('  ✓ Metrics hook already registered globally '
              '(~/.claude/settings.json) — using it for this project')
        metrics_on = True
        metrics_scope: Scope = 'global'
    else:
        metrics_on = prompts.ask_yn(
            '[1/3] Enable metrics collection? (Stop hook records tokens/cost per turn)',
            default=True, interactive=interactive,
        )
        metrics_scope = 'skip'
        if metrics_on:
            metrics_scope = _ask_scope('the metrics hook',
                                       interactive=interactive, default='global')
            metrics_on = metrics_scope != 'skip'

    # ── MCP server ───────────────────────────────────────────────────
    if global_state['mcp_registered']:
        print('  ✓ MCP server already registered globally '
              '(~/.claude/settings.json) — using it for this project')
        mcp_on = True
        mcp_scope: Scope = 'global'
    else:
        mcp_on = prompts.ask_yn(
            '[2/3] Register orquestrum MCP server? (Helm/Flux query budget mid-turn)',
            default=True, interactive=interactive,
        )
        mcp_scope = 'skip'
        if mcp_on:
            mcp_scope = _ask_scope('the MCP server',
                                   interactive=interactive, default='global')
            mcp_on = mcp_scope != 'skip'

    # ── Agents (always asked — independent of global state) ─────────
    print()
    print('  Note: agents always install to ~/.claude/agents/ (never to this project).')
    agents_on = prompts.ask_yn(
        '[3/3] Install Claude Code subagents now? (8 orchestrators, ~50 KB total)',
        default=False, interactive=interactive,
    )

    return {
        'metrics_enabled':    metrics_on,
        'metrics_scope':      metrics_scope,
        'mcp_enabled':        mcp_on,
        'mcp_scope':          mcp_scope,
        'agents_installed':   agents_on,
        # Flag: when True, skip _install_metrics_hook + _install_mcp because
        # the global registration already covers it. The choices are still
        # recorded for config.toml.
        'skip_global_install': (
            global_state['hook_registered'] or global_state['mcp_registered']
        ),
        '_global_hook_present': global_state['hook_registered'],
        '_global_mcp_present':  global_state['mcp_registered'],
    }


# ─── filesystem helpers ─────────────────────────────────────────────────────


def _write_config(project_root: Path, name: str, choices: dict) -> Path:
    today = dt.date.today().isoformat()
    content = _CONFIG_TOML_TEMPLATE.format(
        name=name, created=today,
        metrics_enabled=str(choices['metrics_enabled']).lower(),
        metrics_scope=choices['metrics_scope'],
        mcp_enabled=str(choices['mcp_enabled']).lower(),
        mcp_scope=choices['mcp_scope'],
        agents_installed=str(choices['agents_installed']).lower(),
    )
    cfg = project_root / '.orquestrum' / 'config.toml'
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        cfg.write_text(content, encoding='utf-8')
    else:
        # Re-init: rewrite [metrics]/[mcp]/[agents] sections in place. Simplest
        # safe path: overwrite entirely. The user keeps `name` because we
        # pass the existing one through.
        cfg.write_text(content, encoding='utf-8')
    return cfg


def _write_gitignore(project_root: Path) -> Path:
    gi = project_root / '.orquestrum' / '.gitignore'
    gi.parent.mkdir(parents=True, exist_ok=True)
    # Always overwrite — this file is auto-managed and must stay in sync with
    # _GITIGNORE so re-inits on old projects pick up newly added ignore rules.
    gi.write_text(_GITIGNORE, encoding='utf-8')
    return gi


def _ensure_metrics_dir(project_root: Path) -> Path:
    metrics = project_root / '.orquestrum' / 'metrics'
    metrics.mkdir(parents=True, exist_ok=True)
    return metrics


def _migrate_legacy_manifest(project_root: Path) -> Path | None:
    """If `<project>/ORQUESTRUM.md` exists (legacy ≤v0.4 location), read its
    content into `.orquestrum/manifest.md` and delete the legacy file.
    Returns the new path on migration, None when nothing to migrate.
    """
    legacy = manifest.legacy_manifest_path(project_root)
    if not legacy.exists():
        return None
    new_path = manifest.manifest_path(project_root)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    if not new_path.exists():
        new_path.write_text(legacy.read_text(encoding='utf-8'), encoding='utf-8')
    legacy.unlink()
    return new_path


# ─── optional integrations ─────────────────────────────────────────────────


def _resolve_install_target(scope: Scope, project_root: Path) -> Path | None:
    """Map scope → the directory the install runs against.

    Returns None when scope=skip. For scope=global we install at the user's
    home so the integration's `.claude/` materialises at `~/.claude/`. For
    scope=project we point at the project root.
    """
    if scope == 'global':
        return Path.home()
    if scope == 'project':
        return project_root
    return None


def _install_metrics_hook(project_root: Path, scope: Scope) -> None:
    """Drop the Stop hook into the chosen settings.json. Reuses the
    full claude-code install path (which merges hooks surgically) and
    immediately undoes the agent / sdd file copy by removing those paths
    after the install — we ONLY want the hook entry."""
    if scope == 'skip':
        return
    target = _resolve_install_target(scope, project_root)
    assert target is not None
    print(f'  Installing metrics hook ({scope}) — target: {target}')

    from orquestrum.core.convert import main as convert_main
    from orquestrum.core.install import _merge_claude_settings, INTEGRATIONS

    cache = INTEGRATIONS / 'claude-code'
    if not cache.is_dir():
        convert_main(['--tool', 'claude-code'])
    template = cache / '.claude' / 'settings.json'
    if not template.exists():
        return  # convert failed silently — caller already logged
    target_settings = target / '.claude' / 'settings.json'
    target_settings.parent.mkdir(parents=True, exist_ok=True)
    _merge_claude_settings(template, target_settings)


def _install_agents_global(project_root: Path) -> None:
    """Always installs claude-code agents to ~/.claude/. The project root
    is passed only so we can log a clear message — agents NEVER land here."""
    target = Path.home()
    print(f'  Installing claude-code agents → {target}/.claude/')
    from orquestrum.core.convert import main as convert_main
    from orquestrum.core.install import main as install_main
    from orquestrum.lib.paths import convert_output_root

    cache_tool_dir = convert_output_root() / 'claude-code'
    if not cache_tool_dir.is_dir():
        convert_main(['--tool', 'claude-code'])
    install_main(['--tool', 'claude-code', '--target', str(target)])


# ─── main entry point ──────────────────────────────────────────────────────


def run_init(*, name: str | None = None,
             interactive: bool = True,
             per_project: bool = False) -> int:
    """Bootstrap `.orquestrum/` and run the optional-integrations prompts.

    Returns 0 on success, 1 on failure of an optional install (the
    `.orquestrum/` bootstrap itself is best-effort and never fails).

    When `per_project=False` (default): auto-detects whether MCP/hook
    are already registered globally by `orquestrum setup` and skips
    those prompts + installs. The user gets a clean fast init.

    When `per_project=True`: always runs the prompts, even when global
    is registered. Used for the rare case where someone wants project-
    scoped overrides.
    """
    project_root = Path.cwd()
    project_name = name or project_root.name

    already_initialized = (project_root / '.orquestrum').is_dir()
    legacy_present = manifest.legacy_manifest_path(project_root).exists()

    print(f'{"Re-initializing" if already_initialized else "Initializing"} '
          f'{project_name} at {project_root}')

    # Always — bootstrap .orquestrum/ structure
    _write_gitignore(project_root)
    _ensure_metrics_dir(project_root)

    # Migration of legacy ORQUESTRUM.md (≤v0.4)
    if legacy_present:
        moved = _migrate_legacy_manifest(project_root)
        if moved:
            print(f'  Migrated legacy ORQUESTRUM.md → {moved.relative_to(project_root)}')

    # Interactive prompts (or defaults when -y / non-tty); auto-skips
    # prompts whose work `orquestrum setup` already did unless --per-project.
    choices = _gather_choices(interactive=interactive, per_project=per_project)

    # Persist choices into config.toml + manifest
    _write_config(project_root, project_name, choices)

    existing_state = manifest.read_manifest_state(project_root)
    if existing_state is not None:
        existing_state.last_sync = dt.date.today().isoformat()
        manifest.append_history(existing_state, 're-initialized')
        manifest.write_manifest(project_root, existing_state)
    else:
        new_state = manifest.init_state(name=project_name)
        manifest.write_manifest(project_root, new_state)

    registry.register_project(name=project_name, path=project_root)

    print()
    print(f'  Wrote .orquestrum/config.toml')
    print(f'  Wrote .orquestrum/manifest.md')
    print(f'  Ensured .orquestrum/metrics/, .orquestrum/.gitignore')
    print(f'  Registered in {paths.orquestrum_home() / "registry.toml"}')

    # Optional integrations — run AFTER bootstrap so the project is consistent
    # even if any of these fail. SKIP when global registration already
    # covers it (set by `orquestrum setup`); the project picks up the global
    # config automatically.
    rc = 0
    skip_hook = choices.get('_global_hook_present', False)
    skip_mcp  = choices.get('_global_mcp_present', False)
    try:
        if choices['metrics_enabled'] and not skip_hook:
            _install_metrics_hook(project_root, choices['metrics_scope'])
        if choices['mcp_enabled'] and not skip_mcp:
            # Same code path as metrics hook — settings.json merge handles
            # both `hooks` and `mcpServers` blocks atomically.
            if not choices['metrics_enabled']:
                _install_metrics_hook(project_root, choices['mcp_scope'])
            elif choices['metrics_scope'] != choices['mcp_scope']:
                # User asked for different scopes — run merge once per scope
                _install_metrics_hook(project_root, choices['mcp_scope'])
        if choices['agents_installed']:
            _install_agents_global(project_root)
    except Exception as e:  # defensive: bootstrap already done
        print(f'  ! optional install reported error: {e}')
        rc = 1

    print()
    if rc == 0:
        print(f'✓ Project ready. {project_name} is an orquestrum project.')
    else:
        print(f'✗ Bootstrap completed with errors above. Inspect and re-run.')
    print(f'  Try: orquestrum doctor   (verify environment)')
    if not choices['agents_installed']:
        print(f'       orquestrum install --tool claude-code --target ~  '
              f'(install agents later)')
    print(f'       orquestrum web      (open dashboard)')

    return rc
