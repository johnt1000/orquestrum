"""sidebar.py — cheap per-request counts surfaced in the sidebar nav.

Computed lazily on each render. No caching: scanning the filesystem for
agents/skills counts is sub-millisecond and keeps the badges always fresh.
"""
from __future__ import annotations
from pathlib import Path

from ui.config import UIConfig
from ui.lib import jobs as jobs_lib


def sidebar_counts(config: UIConfig) -> dict[str, int | None]:
    """Return {'agents', 'skills', 'jobs_running'} — None when not applicable.

    Never raises; missing paths just yield zero counts.
    """
    agents:  int | None = None
    skills:  int | None = None

    try:
        if config.is_framework:
            agents_dir = config.root / 'agents'
            skills_dir = config.root / 'skills'
            agents = sum(1 for _ in agents_dir.glob('*.md')) if agents_dir.is_dir() else 0
            skills = sum(1 for _ in skills_dir.glob('*/SKILL.md')) if skills_dir.is_dir() else 0
        elif config.linked_project_root:
            local_agents: set[str] = set()
            local_skills: set[str] = set()
            for sub in ('.claude/agents', '.opencode/agents', '.sdd/agents'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    local_agents.update(p.stem for p in d.glob('*.md'))
            for sub in ('.sdd/skills', '.opencode/skills'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    local_skills.update(p.parent.name for p in d.glob('*/SKILL.md'))
            # Merge with framework canon if available
            if config.framework_root:
                fw_a = config.framework_root / 'agents'
                fw_s = config.framework_root / 'skills'
                if fw_a.is_dir():
                    local_agents.update(p.stem for p in fw_a.glob('*.md'))
                if fw_s.is_dir():
                    local_skills.update(p.parent.name for p in fw_s.glob('*/SKILL.md'))
            agents = len(local_agents)
            skills = len(local_skills)
        elif config.framework_root:
            agents_dir = config.framework_root / 'agents'
            skills_dir = config.framework_root / 'skills'
            agents = sum(1 for _ in agents_dir.glob('*.md')) if agents_dir.is_dir() else 0
            skills = sum(1 for _ in skills_dir.glob('*/SKILL.md')) if skills_dir.is_dir() else 0
    except Exception:
        pass

    jobs_running = sum(1 for j in jobs_lib._jobs.values() if not j.is_terminal)

    return {
        'agents':       agents,
        'skills':       skills,
        'jobs_running': jobs_running,
    }
