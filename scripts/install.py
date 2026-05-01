#!/usr/bin/env python3
"""install.py — copies an integration package into a target project.

Usage:
    uv run scripts/install.py --tool <tool> --target <path>
    uv run scripts/install.py --auto --target <path>

    Tools: claude-code, opencode, cursor, aider, windsurf

    Run scripts/convert.py first to generate integrations/.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.log import log, ok, warn, err, set_prefix
from lib.models import VALID_TOOLS

set_prefix('install')

ROOT         = Path(__file__).parent.parent
INTEGRATIONS = ROOT / 'integrations'


def detect_tools(target: Path) -> list[str]:
    found: list[str] = []
    home = Path.home()
    if (home / '.claude').is_dir() or shutil.which('claude'):
        found.append('claude-code')
    if ((home / '.config' / 'opencode').is_dir() or
            (target / '.opencode').is_dir() or shutil.which('opencode')):
        found.append('opencode')
    if (target / '.cursor').is_dir() or shutil.which('cursor'):
        found.append('cursor')
    if shutil.which('aider'):
        found.append('aider')
    if (target / '.windsurfrules').exists() or shutil.which('windsurf'):
        found.append('windsurf')
    return found


def install_tool(tool: str, target: Path) -> bool:
    if tool not in VALID_TOOLS:
        err(f'Unknown tool: {tool}')
        if tool == 'claude':
            err('  Did you mean: claude-code?')
        return False

    src = INTEGRATIONS / tool
    if not src.is_dir():
        err(f'Integration package not found: {src}')
        err(f'Run first: uv run scripts/convert.py --tool {tool}')
        return False

    abs_target = target.expanduser().resolve()
    log(f'Installing {tool} → {abs_target}')
    abs_target.mkdir(parents=True, exist_ok=True)

    shutil.copytree(src, abs_target, dirs_exist_ok=True)

    # Make any bundled shell scripts executable
    scripts_dir = abs_target / 'scripts'
    if scripts_dir.is_dir():
        for sh in scripts_dir.glob('*.sh'):
            sh.chmod(sh.stat().st_mode | 0o111)

    # OpenCode: resolve __OPENCODE_ROOT__ placeholder
    if tool == 'opencode':
        for md in abs_target.rglob('*.md'):
            try:
                content = md.read_text(encoding='utf-8')
                if '__OPENCODE_ROOT__' in content:
                    md.write_text(
                        content.replace('__OPENCODE_ROOT__', str(abs_target)),
                        encoding='utf-8',
                    )
            except (OSError, UnicodeDecodeError):
                pass

    ok(f'{tool} installed into {abs_target}')
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Install a generated integration package into a target project.',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tool', metavar='TOOL',
                       help='Tool to install (claude-code | opencode | cursor | aider | windsurf)')
    group.add_argument('--auto', action='store_true',
                       help='Auto-detect installed tools and install all')
    parser.add_argument('--target', required=True, metavar='PATH',
                        help='Target directory (project root or tool config dir)')
    args = parser.parse_args()

    target = Path(args.target).expanduser()
    if not target.exists():
        err(f'Target directory does not exist: {target}')
        sys.exit(1)

    print()

    if args.auto:
        tools = detect_tools(target)
        if not tools:
            warn(f'No supported tools detected in {target}')
            warn('Install one of: claude-code, opencode, cursor, aider, windsurf')
            sys.exit(1)
        log(f'Detected tools: {", ".join(tools)}')
        print()
        for tool in tools:
            if not install_tool(tool, target):
                sys.exit(1)
    else:
        if not install_tool(args.tool, target):
            sys.exit(1)

    print()


if __name__ == '__main__':
    main()
