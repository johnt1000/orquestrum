#!/usr/bin/env python3
"""deps.py — installs external agent/skill dependencies for Orquestrum.

Usage:
    uv run scripts/deps.py --target ~/.config/opencode
    uv run scripts/deps.py --target ~/.config/opencode --only agency
    uv run scripts/deps.py --target ~/.config/opencode --only skills

    Supported dependencies:
      agency   - agency-agents (msitarzewski/agency-agents)
      skills   - anthropics/skills (includes supabase)
      supabase - skipped, already included in anthropics/skills
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.log import log, ok, warn, err, set_prefix

set_prefix('deps')

AGENCY_REPO = 'https://github.com/msitarzewski/agency-agents.git'
SKILLS_REPO = 'https://github.com/anthropics/skills.git'

AGENCY_CATEGORIES = [
    'engineering', 'design', 'sales', 'marketing', 'product',
    'project-management', 'testing', 'support', 'spatial-computing',
    'specialized', 'academic', 'finance', 'game-development',
    'paid-media', 'strategy',
]


def clone_to_temp(repo: str) -> Path | None:
    tmp = Path(tempfile.mkdtemp())
    log(f'Cloning {repo}...')
    result = subprocess.run(
        ['git', 'clone', '--depth', '1', '--quiet', repo, str(tmp)],
        capture_output=True, timeout=60,
    )
    if result.returncode != 0:
        warn('Shallow clone failed or timed out, retrying full clone...')
        result = subprocess.run(
            ['git', 'clone', '--quiet', repo, str(tmp)],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            err(f'Clone failed: {repo}')
            shutil.rmtree(tmp, ignore_errors=True)
            return None
    return tmp


def install_agency(target: Path) -> None:
    log('Installing agency-agents (msitarzewski/agency-agents)...')
    tmp = clone_to_temp(AGENCY_REPO)
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


def install_skills(target: Path) -> None:
    log('Installing anthropics/skills (includes supabase)...')
    tmp = clone_to_temp(SKILLS_REPO)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Install external agent/skill dependencies for Orquestrum.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  uv run scripts/deps.py --target ~/.config/opencode\n'
            '  uv run scripts/deps.py --target ~/.config/opencode --only agency\n'
            '  uv run scripts/deps.py --target ~/.config/opencode --only skills'
        ),
    )
    parser.add_argument('--target', required=True, metavar='PATH',
                        help='Target directory (e.g. ~/.config/opencode)')
    parser.add_argument('--only', metavar='NAME',
                        help='Install specific dependency only (agency | skills | supabase)')
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        err(f'Target directory does not exist: {target}')
        sys.exit(1)

    (target / 'agents').mkdir(parents=True, exist_ok=True)
    (target / 'skills').mkdir(parents=True, exist_ok=True)

    print()

    only = args.only or 'all'
    if only == 'agency':
        install_agency(target)
    elif only == 'skills':
        install_skills(target)
    elif only == 'supabase':
        install_supabase()
    elif only in ('', 'all'):
        install_agency(target)
        install_skills(target)
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
