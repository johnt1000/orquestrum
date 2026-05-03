"""init_impl — implementation of `orquestrum init`."""
from __future__ import annotations
import datetime as dt
from pathlib import Path

from orquestrum.lib import manifest, paths, registry


_CONFIG_TOML_TEMPLATE = """# Created by `orquestrum init`. Keep in version control.
[project]
name      = "{name}"
created   = "{created}"
{tool_line}{provider_line}
[metrics]
tier = "balanced"

[hooks]
emit_metrics = {emit_metrics}
"""

_GITIGNORE = """# Auto-managed by orquestrum
metrics/
*.tmp
*.candidate.md
session.json
events.jsonl
dashboard.{md,html}
"""


def _write_config(project_root: Path, name: str, tool: str | None, provider: str | None) -> Path:
    today = dt.date.today().isoformat()
    tool_line = f'tool      = "{tool}"\n' if tool else ''
    provider_line = f'provider  = "{provider}"\n' if provider else ''
    content = _CONFIG_TOML_TEMPLATE.format(
        name=name, created=today,
        tool_line=tool_line, provider_line=provider_line,
        emit_metrics='true' if tool == 'claude-code' else 'false',
    )
    cfg = project_root / '.orquestrum' / 'config.toml'
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        cfg.write_text(content, encoding='utf-8')
        return cfg

    # Already exists — update tool/provider fields in place if provided
    import re
    text = cfg.read_text(encoding='utf-8')
    if tool:
        if re.search(r'^\s*tool\s*=', text, re.MULTILINE):
            text = re.sub(r'^\s*tool\s*=\s*".*"', f'tool      = "{tool}"',
                          text, count=1, flags=re.MULTILINE)
        else:
            # Insert under [project] section
            text = re.sub(r'(\[project\][^\[]*?\n)(\n|\[)',
                          rf'\1tool      = "{tool}"\n\2', text, count=1)
    if provider:
        if re.search(r'^\s*provider\s*=', text, re.MULTILINE):
            text = re.sub(r'^\s*provider\s*=\s*".*"', f'provider  = "{provider}"',
                          text, count=1, flags=re.MULTILINE)
        else:
            text = re.sub(r'(\[project\][^\[]*?\n)(\n|\[)',
                          rf'\1provider  = "{provider}"\n\2', text, count=1)
    cfg.write_text(text, encoding='utf-8')
    return cfg


def _write_gitignore(project_root: Path) -> Path:
    gi = project_root / '.orquestrum' / '.gitignore'
    if not gi.exists():
        gi.write_text(_GITIGNORE, encoding='utf-8')
    return gi


def _ensure_metrics_dir(project_root: Path) -> Path:
    metrics = project_root / '.orquestrum' / 'metrics'
    metrics.mkdir(parents=True, exist_ok=True)
    return metrics


def _run_install(project_root: Path, tool: str, provider: str | None) -> bool:
    """Generate the integration package (cached) and install it into the
    target project. Works in dev mode (repo) and wheel mode (cache) alike —
    no chdir, no canonical-repo precondition.
    """
    from orquestrum.core.convert import main as convert_main
    from orquestrum.core.install import main as install_main

    # Make sure the cached integration exists for this tool. convert reads
    # canonical assets from the dev repo OR the bundled `_assets/`, and
    # writes to `<repo>/integrations/` OR `~/.orquestrum/cache/integrations/`.
    integration_dir = paths.convert_output_root() / tool
    if not integration_dir.is_dir():
        print(f'  Generating integration package for {tool} (one-time)...')
        args = ['--tool', tool]
        if provider:
            args += ['--provider', provider]
        convert_main(args)

    install_main(['--tool', tool, '--target', str(project_root)])
    return True


def run_init(*, tool: str | None = None, provider: str | None = None,
             name: str | None = None) -> int:
    project_root = Path.cwd()
    project_name = name or project_root.name

    already_initialized = (project_root / '.orquestrum').is_dir()

    cfg_path = _write_config(project_root, project_name, tool, provider)
    _write_gitignore(project_root)
    _ensure_metrics_dir(project_root)

    # Manifest
    existing_state = manifest.read_manifest_state(project_root)
    if existing_state is not None and tool and existing_state.tool and existing_state.tool != tool:
        # Tool change — append history
        manifest.append_history(
            existing_state,
            f'switched from `{existing_state.tool}` to `{tool}`'
            + (f' (provider: {provider})' if provider else ''),
        )
        existing_state.tool = tool
        if provider:
            existing_state.provider = provider
        existing_state.last_sync = dt.date.today().isoformat()
        manifest.write_manifest(project_root, existing_state)
    elif existing_state is not None:
        # Same tool or first-time tool set: just bump last_sync; if tool was None, set it now
        if tool and not existing_state.tool:
            existing_state.tool = tool
            if provider:
                existing_state.provider = provider
            manifest.append_history(existing_state,
                                    f'tool set to `{tool}`'
                                    + (f' (provider: {provider})' if provider else ''))
        existing_state.last_sync = dt.date.today().isoformat()
        manifest.write_manifest(project_root, existing_state)
    else:
        new_state = manifest.init_state(name=project_name, tool=tool, provider=provider)
        manifest.write_manifest(project_root, new_state)

    # Register globally
    registry.register_project(name=project_name, path=project_root,
                              tool=tool, provider=provider)

    # Output summary
    if already_initialized:
        print(f'Re-initialized {project_name} at {project_root}')
    else:
        print(f'Initialized {project_name} at {project_root}')
    print(f'  Created/updated .orquestrum/config.toml')
    print(f'  Ensured .orquestrum/metrics/, .orquestrum/.gitignore')
    print(f'  Wrote ORQUESTRUM.md (project manifest — keep in version control)')
    print(f'  Registered in {paths.orquestrum_home() / "registry.toml"}')

    if tool:
        print()
        print(f'Installing {tool} integration...')
        ok = _run_install(project_root, tool, provider)
        if ok:
            print(f'  Run `orquestrum web` to open the dashboard.')
    else:
        print()
        print('Next: run `orquestrum init --tool <claude-code|opencode|cursor|aider|windsurf>`')
        print('      to deploy an integration, or `orquestrum install --tool ...` separately.')

    return 0
