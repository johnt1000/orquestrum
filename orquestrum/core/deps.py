#!/usr/bin/env python3
"""deps.py — installs external agent/skill dependencies for Orquestrum.

All upstream repositories are pinned by commit SHA in `pinned_refs.toml` to
prevent silent upstream drift / supply-chain compromise. Rotation is explicit:

    orquestrum deps --update-pins        # rewrite SHAs to current HEADs
    git diff pinned_refs.toml            # review
    git commit -m "chore(deps): rotate pinned SHAs"

Usage:
    orquestrum deps --target ~/.config/opencode
    orquestrum deps --target ~/.config/opencode --only agency
    orquestrum deps --target ~/.config/opencode --only skills
    orquestrum deps --update-pins

    Supported dependencies:
      agency   - agency-agents (msitarzewski/agency-agents)
      skills   - anthropics/skills (includes supabase)
      supabase - skipped, already included in anthropics/skills
"""
import argparse
import datetime
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from orquestrum.lib.log import log, ok, warn, err, set_prefix
from orquestrum.lib.paths import is_dev_mode, pinned_refs_path

set_prefix('deps')

# Pin file resolution:
#   dev mode  → <repo>/pinned_refs.toml (writeable; --update-pins target)
#   wheel mode → orquestrum/_assets/pinned_refs.toml (read-only)
PINS_FILE = pinned_refs_path()

AGENCY_CATEGORIES = [
    'engineering', 'design', 'sales', 'marketing', 'product',
    'project-management', 'testing', 'support', 'spatial-computing',
    'specialized', 'academic', 'finance', 'game-development',
    'paid-media', 'strategy',
]


def load_pins() -> dict[str, dict]:
    """Return {name: {repo, sha, last_pinned, notes}} from pinned_refs.toml."""
    if not PINS_FILE.exists():
        err(f'Pin file missing: {PINS_FILE}. Run --update-pins or restore from git.')
        sys.exit(1)
    data = tomllib.loads(PINS_FILE.read_text(encoding='utf-8'))
    refs = data.get('refs', [])
    return {ref['name']: ref for ref in refs}


def clone_at_sha(repo: str, sha: str) -> Path | None:
    """Clone a repo and check out the pinned SHA. Returns the cloned dir or None on failure."""
    tmp = Path(tempfile.mkdtemp())
    log(f'Cloning {repo} @ {sha[:12]}...')

    init = subprocess.run(['git', 'init', '--quiet', str(tmp)], capture_output=True)
    if init.returncode != 0:
        err(f'git init failed: {init.stderr.decode().strip()}')
        shutil.rmtree(tmp, ignore_errors=True)
        return None

    add_remote = subprocess.run(
        ['git', '-C', str(tmp), 'remote', 'add', 'origin', repo],
        capture_output=True,
    )
    if add_remote.returncode != 0:
        err(f'git remote add failed: {add_remote.stderr.decode().strip()}')
        shutil.rmtree(tmp, ignore_errors=True)
        return None

    fetch = subprocess.run(
        ['git', '-C', str(tmp), 'fetch', '--depth', '1', '--quiet', 'origin', sha],
        capture_output=True, timeout=120,
    )
    if fetch.returncode != 0:
        # Some servers refuse single-SHA fetches; fall back to full fetch + checkout
        warn('Shallow fetch by SHA failed, retrying full fetch...')
        fetch = subprocess.run(
            ['git', '-C', str(tmp), 'fetch', '--quiet', 'origin'],
            capture_output=True, timeout=300,
        )
        if fetch.returncode != 0:
            err(f'fetch failed: {fetch.stderr.decode().strip()}')
            shutil.rmtree(tmp, ignore_errors=True)
            return None

    checkout = subprocess.run(
        ['git', '-C', str(tmp), 'checkout', '--quiet', sha],
        capture_output=True,
    )
    if checkout.returncode != 0:
        err(f'checkout {sha} failed: {checkout.stderr.decode().strip()}')
        shutil.rmtree(tmp, ignore_errors=True)
        return None

    return tmp


def install_agency(target: Path, pins: dict[str, dict]) -> None:
    pin = pins.get('agency')
    if not pin:
        err('No pin entry for "agency" in pinned_refs.toml')
        sys.exit(1)
    log(f'Installing agency-agents @ {pin["sha"][:12]} (pinned {pin["last_pinned"]})...')
    tmp = clone_at_sha(pin['repo'], pin['sha'])
    if not tmp:
        sys.exit(1)

    try:
        log('Running agency-agents convert.sh...')
        result = subprocess.run(
            ['bash', 'scripts/convert.sh'],
            cwd=tmp, capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            warn('agency-agents convert.sh failed — integrations may be outdated')

        agents_out = target / 'agents'
        agents_out.mkdir(parents=True, exist_ok=True)

        opencode_agents = tmp / 'integrations' / 'opencode' / 'agents'
        if opencode_agents.is_dir():
            for md in opencode_agents.glob('*.md'):
                shutil.copy(md, agents_out / md.name)
            ok(f'agency-agents installed to {agents_out}/')
        else:
            warn('OpenCode integration not found in agency-agents, copying agent files directly...')
            for cat in AGENCY_CATEGORIES:
                cat_dir = tmp / cat
                if cat_dir.is_dir():
                    for md in cat_dir.glob('*.md'):
                        shutil.copy(md, agents_out / md.name)
            ok(f'agency-agents files copied to {agents_out}/')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def install_skills(target: Path, pins: dict[str, dict]) -> None:
    pin = pins.get('skills')
    if not pin:
        err('No pin entry for "skills" in pinned_refs.toml')
        sys.exit(1)
    log(f'Installing anthropics/skills @ {pin["sha"][:12]} (pinned {pin["last_pinned"]})...')
    tmp = clone_at_sha(pin['repo'], pin['sha'])
    if not tmp:
        sys.exit(1)

    try:
        skills_out = target / 'skills'
        skills_out.mkdir(parents=True, exist_ok=True)

        count = 0
        src_skills = tmp / 'skills'
        if src_skills.is_dir():
            for skill_dir in sorted(src_skills.iterdir()):
                if not skill_dir.is_dir():
                    continue
                dest = skills_out / skill_dir.name
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
                count += 1

        ok(f'anthropics/skills installed: {count} skills to {skills_out}/')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def install_supabase() -> None:
    log('supabase/agent-skills is included in anthropics/skills, skipping separate install...')


def update_pins() -> None:
    """Refresh SHAs in pinned_refs.toml to upstream HEADs.

    Preserves the order and structure of the file by overwriting only the
    `sha` and `last_pinned` lines per [[refs]] block.

    Only valid in dev mode — the wheel-bundled copy is read-only and pin
    rotation requires code review (see docs/governance/HOOKS.md).
    """
    if not is_dev_mode():
        err('--update-pins requires the canonical Orquestrum repo.')
        err('Clone https://github.com/jonatasrodrigues/ia-fluency and run')
        err('the command from inside it; pin rotation needs code review.')
        sys.exit(2)

    if not PINS_FILE.exists():
        err(f'Pin file missing: {PINS_FILE}')
        sys.exit(1)

    pins = load_pins()
    today = datetime.date.today().isoformat()

    new_shas: dict[str, str] = {}
    for name, ref in pins.items():
        log(f'Resolving HEAD for {name} ({ref["repo"]})...')
        result = subprocess.run(
            ['git', 'ls-remote', ref['repo'], 'HEAD'],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            err(f'  ls-remote failed: {result.stderr.decode().strip()}')
            sys.exit(1)
        head_sha = result.stdout.decode().split()[0]
        log(f'  {head_sha[:12]} (was {ref["sha"][:12]})')
        new_shas[name] = head_sha

    text = PINS_FILE.read_text(encoding='utf-8')
    for name, head_sha in new_shas.items():
        old_sha = pins[name]['sha']
        old_pinned = pins[name]['last_pinned']
        if f'sha         = "{old_sha}"' not in text:
            err(f'Could not locate sha line for {name} (formatting drift?)')
            sys.exit(1)
        text = text.replace(
            f'sha         = "{old_sha}"',
            f'sha         = "{head_sha}"',
            1,
        ).replace(
            f'last_pinned = "{old_pinned}"',
            f'last_pinned = "{today}"',
            1,
        )

    PINS_FILE.write_text(text, encoding='utf-8')
    ok(f'Updated {len(new_shas)} pin(s). Review with `git diff pinned_refs.toml` and commit.')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog='orquestrum deps',
        description='Install external agent/skill dependencies for Orquestrum.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum deps --target ~/.config/opencode\n'
            '  orquestrum deps --target ~/.config/opencode --only agency\n'
            '  orquestrum deps --target ~/.config/opencode --only skills\n'
            '  orquestrum deps --update-pins'
        ),
    )
    parser.add_argument('--target', metavar='PATH',
                        help='Target directory (e.g. ~/.config/opencode). Required for installs.')
    parser.add_argument('--only', metavar='NAME',
                        help='Install specific dependency only (agency | skills | supabase)')
    parser.add_argument('--update-pins', action='store_true',
                        help='Rewrite pinned_refs.toml with current upstream HEADs and exit')
    args = parser.parse_args(argv)

    if args.update_pins:
        update_pins()
        return

    if not args.target:
        err('--target is required (or pass --update-pins to refresh SHAs)')
        sys.exit(2)

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        err(f'Target directory does not exist: {target}')
        sys.exit(1)

    pins = load_pins()
    (target / 'agents').mkdir(parents=True, exist_ok=True)
    (target / 'skills').mkdir(parents=True, exist_ok=True)

    print()

    only = args.only or 'all'
    if only == 'agency':
        install_agency(target, pins)
    elif only == 'skills':
        install_skills(target, pins)
    elif only == 'supabase':
        install_supabase()
    elif only in ('', 'all'):
        install_agency(target, pins)
        install_skills(target, pins)
    else:
        err(f'Unknown dependency: {only} (use: agency, skills, supabase)')
        sys.exit(1)

    print()
    agents_count = sum(1 for _ in (target / 'agents').iterdir()) if (target / 'agents').exists() else 0
    skills_count = sum(1 for _ in (target / 'skills').iterdir()) if (target / 'skills').exists() else 0
    log('Done! Review installed dependencies:')
    print(f'  Agents: {agents_count}')
    print(f'  Skills: {skills_count}')


if __name__ == '__main__':
    main()
