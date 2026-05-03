"""catalog_loader.py — load agent + skill catalog from canonical source.

Reusable in both framework mode (the Orquestrum repo) and project mode
(read installed agents under .claude/agents/ or .opencode/agents/).
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from pathlib import Path

try:
    from orquestrum.lib.frontmatter import parse_agent, parse_skill, AgentConfig, SkillConfig
    from orquestrum.lib.models import AGENT_TIERS
except ImportError:
    parse_agent = parse_skill = None
    AGENT_TIERS = {}


@dataclass(frozen=True)
class AgentRow:
    name:        str
    slug:        str
    description: str
    tier:        str
    max_tokens:  int | None
    temperature: float
    bash:        bool
    body_path:   Path
    sources:     tuple[str, ...] = ()   # ('local',), ('global',), or ('local','global')
    emoji:       str = '◇'              # frontmatter `emoji:` field; '◇' fallback

    @property
    def short_name(self) -> str:
        """First token of the canonical name (e.g. 'Helm - The Architect' → 'Helm')."""
        return self.name.split(' - ', 1)[0]

    @property
    def location_label(self) -> str:
        if 'local' in self.sources and 'global' in self.sources:
            return 'local+global'
        if 'local' in self.sources:
            return 'local'
        return 'global'


@dataclass(frozen=True)
class SkillRow:
    name:             str
    slug:             str
    description:      str
    inject_refs:      str
    inject_fewshot:   str
    chain_next:       str | None
    depends_on:       list[str]
    emits_confidence: bool
    body_path:        Path
    sources:          tuple[str, ...] = ()

    @property
    def location_label(self) -> str:
        if 'local' in self.sources and 'global' in self.sources:
            return 'local+global'
        if 'local' in self.sources:
            return 'local'
        return 'global'


def _slug_from_name(name: str) -> str:
    import re
    s = name.lower()
    s = re.sub(r'\s*[—–-]\s*', '-', s)
    s = s.replace(' & ', '-and-').replace(' ', '-')
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')


def list_agents(agents_dir: Path) -> list[AgentRow]:
    if parse_agent is None or not agents_dir.is_dir():
        return []
    out: list[AgentRow] = []
    for f in sorted(agents_dir.glob('*.md')):
        try:
            cfg = parse_agent(f)
        except Exception:
            continue
        # `emoji` is a custom frontmatter field not exposed by AgentConfig
        emoji = '◇'
        try:
            import frontmatter as fm
            raw = fm.load(str(f)).get('emoji')
            if raw:
                emoji = str(raw)
        except Exception:
            pass
        out.append(AgentRow(
            name=cfg.name,
            slug=_slug_from_name(cfg.name),
            description=cfg.description,
            tier=AGENT_TIERS.get(cfg.name, '?'),
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            bash=cfg.bash,
            body_path=f,
            emoji=emoji,
        ))
    return out


def list_skills(skills_dir: Path) -> list[SkillRow]:
    if parse_skill is None or not skills_dir.is_dir():
        return []
    out: list[SkillRow] = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        f = d / 'SKILL.md'
        if not f.exists():
            continue
        try:
            cfg = parse_skill(f)
        except Exception:
            continue
        # emits_confidence is a custom field — read raw frontmatter
        emits = False
        try:
            import frontmatter as fm
            emits = bool(fm.load(str(f)).get('emits_confidence', False))
        except Exception:
            pass
        out.append(SkillRow(
            name=cfg.name,
            slug=d.name,
            description=cfg.description,
            inject_refs=cfg.inject_refs,
            inject_fewshot=cfg.inject_fewshot,
            chain_next=cfg.chain_next,
            depends_on=cfg.depends_on,
            emits_confidence=emits,
            body_path=f,
        ))
    return out


def merged_agents(
    local_dirs: list[Path],
    global_dir: Path | None,
    *,
    local_tag: str = 'local',
    global_tag: str = 'global',
) -> list[AgentRow]:
    """Merge agents from multiple local dirs + one global dir, deduping by slug.

    Each row gets a `sources` tuple indicating where it was found.
    When the same slug appears in both local and global, the local row's data
    is kept (it's the installed version) and both tags are recorded.
    """
    local_by_slug: dict[str, AgentRow] = {}
    for d in local_dirs:
        for row in list_agents(d):
            local_by_slug[row.slug] = row

    global_by_slug: dict[str, AgentRow] = {}
    if global_dir is not None:
        for row in list_agents(global_dir):
            global_by_slug[row.slug] = row

    result: list[AgentRow] = []
    for slug in sorted(set(local_by_slug) | set(global_by_slug)):
        if slug in local_by_slug and slug in global_by_slug:
            result.append(replace(local_by_slug[slug], sources=(local_tag, global_tag)))
        elif slug in local_by_slug:
            result.append(replace(local_by_slug[slug], sources=(local_tag,)))
        else:
            result.append(replace(global_by_slug[slug], sources=(global_tag,)))
    return result


def merged_skills(
    local_dirs: list[Path],
    global_dir: Path | None,
    *,
    local_tag: str = 'local',
    global_tag: str = 'global',
) -> list[SkillRow]:
    """Merge skills from multiple local dirs + one global dir, deduping by slug."""
    local_by_slug: dict[str, SkillRow] = {}
    for d in local_dirs:
        for row in list_skills(d):
            local_by_slug[row.slug] = row

    global_by_slug: dict[str, SkillRow] = {}
    if global_dir is not None:
        for row in list_skills(global_dir):
            global_by_slug[row.slug] = row

    result: list[SkillRow] = []
    for slug in sorted(set(local_by_slug) | set(global_by_slug)):
        if slug in local_by_slug and slug in global_by_slug:
            result.append(replace(local_by_slug[slug], sources=(local_tag, global_tag)))
        elif slug in local_by_slug:
            result.append(replace(local_by_slug[slug], sources=(local_tag,)))
        else:
            result.append(replace(global_by_slug[slug], sources=(global_tag,)))
    return result
