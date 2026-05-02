#!/usr/bin/env python3
"""convert.py — generates integrations/<tool>/ from canonical source.

Usage:
    uv run scripts/convert.py --tool <tool>
    uv run scripts/convert.py --all
    uv run scripts/convert.py --tool claude-code --provider claude

    Tools:     claude-code, opencode, cursor, aider, windsurf
    Providers: claude (default for claude-code), copilot, glm
"""
import argparse
import re
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.log import log, ok, warn, err, set_prefix
from lib.models import (
    VALID_PROVIDERS, VALID_TOOLS, PROVIDER_MODELS,
    CANONICAL_MODELS, HELM_NAME, ORCHESTRATOR_NAMES,
    AGENT_TIERS, resolve_model, apply_provider_models, tier_collapse,
    estimate_cost,
)
from lib.frontmatter import parse_agent, parse_skill, AgentConfig
from lib.paths import rewrite_paths, name_to_kebab, skill_reference_content

set_prefix('convert')

ROOT         = Path(__file__).parent.parent
INTEGRATIONS = ROOT / 'integrations'
AGENTS_DIR   = ROOT / 'agents'
SKILLS_DIR   = ROOT / 'skills'
DOCS_DIR     = ROOT / 'docs'
SCRIPTS_DIR  = ROOT / 'scripts'
BUNDLE_DIR   = ROOT / 'bundle'

# Settings.json template for Claude Code with metrics hook installed
_CLAUDE_SETTINGS_TEMPLATE = '''{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .sdd/scripts/hooks/emit_metrics.py"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .sdd/scripts/hooks/emit_metrics.py"
          }
        ]
      }
    ]
  }
}
'''


# ─── Adapters ─────────────────────────────────────────────────────────────────

_CACHE_MARKER_RE = re.compile(
    r'<!--\s*/?cache:(?:stable|volatile)\s*-->\n?',
    re.IGNORECASE,
)


def _yaml_quote(value: str) -> str:
    """Quote a YAML scalar so colons / quotes / hashes don't break parsing.

    Always uses double quotes; escapes embedded double-quotes and backslashes.
    """
    if not isinstance(value, str):
        return str(value)
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


class ToolAdapter(ABC):
    docs_prefix:   str
    skills_prefix: str

    @abstractmethod
    def convert(self, provider: str | None) -> None: ...

    def _apply(self, body: str, provider: str | None) -> str:
        body = self._segment_for_cache(body)
        return apply_provider_models(rewrite_paths(body, self.docs_prefix, self.skills_prefix), provider)

    def _segment_for_cache(self, body: str) -> str:
        """Default: strip cache:stable/cache:volatile markers (no segmented cache).

        Adapters that support segmented prompt caching (e.g. native cache_control
        injection) override this to emit per-segment directives. See
        docs/agent-context/CONVENTIONS.md → Cache Segmentation Markers.
        """
        return _CACHE_MARKER_RE.sub('', body)

    def _check_canonical(self, content: str, filename: str, provider: str | None) -> None:
        if not provider:
            return
        import re
        for canonical in CANONICAL_MODELS:
            if re.search(rf'^model:\s+{re.escape(canonical)}\s*$', content, re.MULTILINE):
                warn(f'{filename}: model field is bare canonical \'{canonical}\' — provider={provider} may be incomplete')


class ClaudeCodeAdapter(ToolAdapter):
    docs_prefix   = '.sdd/docs'
    skills_prefix = '.sdd/skills'

    def _frontmatter(self, agent: AgentConfig, provider: str | None) -> str:
        # Always resolve model — claude-code is always Anthropic; default to 'claude'
        model = resolve_model(agent.name, provider or 'claude', agent.model_tier_override)
        lines = ['---',
                 f'name: {_yaml_quote(agent.name)}',
                 f'description: {_yaml_quote(agent.description)}',
                 f'model: {model}',
                 f'temperature: {agent.temperature}']
        if agent.max_tokens is not None:
            lines.append(f'maxTokens: {agent.max_tokens}')
        if not agent.bash:
            lines.append('disallowedTools: Bash')
        lines.append('---\n')
        return '\n'.join(lines) + '\n'

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'claude-code'
        shutil.rmtree(out, ignore_errors=True)
        agents_out = out / '.claude' / 'agents'
        agents_out.mkdir(parents=True)
        (out / '.sdd' / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = self._frontmatter(agent, provider) + self._apply(agent.body, provider)
            out_file = agents_out / f'{slug}.md'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        # docs/ has subdirectories now (agent-context, governance, baselines) —
        # copytree preserves the full structure
        shutil.copytree(DOCS_DIR, out / '.sdd' / 'docs', dirs_exist_ok=True)
        shutil.copytree(SKILLS_DIR, out / '.sdd' / 'skills', dirs_exist_ok=True)
        for bak in (out / '.sdd' / 'skills').rglob('*.bak'):
            bak.unlink()

        # Hook + lib copy (R3): metrics hook needs scripts/lib/models for estimate_cost
        shutil.copytree(SCRIPTS_DIR / 'hooks', out / '.sdd' / 'scripts' / 'hooks', dirs_exist_ok=True)
        shutil.copytree(SCRIPTS_DIR / 'lib',   out / '.sdd' / 'scripts' / 'lib',   dirs_exist_ok=True)
        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / '.sdd' / 'scripts')

        # Claude Code settings.json template — install.py merges with user's existing
        (out / '.claude' / 'settings.json').write_text(_CLAUDE_SETTINGS_TEMPLATE, encoding='utf-8')

        ok(f'claude-code → {out}')
        print(f'    .claude/agents/        ← copy to your project\'s .claude/agents/')
        print(f'    .claude/settings.json  ← merged into your project\'s settings (hooks for metrics)')
        print(f'    .sdd/                  ← copy to your project root')


class OpenCodeAdapter(ToolAdapter):
    docs_prefix   = '__OPENCODE_ROOT__/docs'
    skills_prefix = '__OPENCODE_ROOT__/skills'

    def _frontmatter(self, agent: AgentConfig, provider: str | None) -> str:
        model_line = ''
        if provider:
            model = resolve_model(agent.name, provider, agent.model_tier_override)
            model_line = f'model: {model}\n'
        max_tokens_line = f'maxTokens: {agent.max_tokens}\n' if agent.max_tokens is not None else ''
        bash_perm = 'allow' if agent.bash else 'deny'
        if agent.name == HELM_NAME:
            task = '    "*": deny\n' + ''.join(f'    "{o}": allow\n' for o in ORCHESTRATOR_NAMES)
        else:
            task = '    "*": allow\n'
        return (
            f'---\nname: {_yaml_quote(agent.name)}\ndescription: {_yaml_quote(agent.description)}\n'
            f'mode: primary\n{model_line}temperature: {agent.temperature}\n'
            f'{max_tokens_line}'
            f'emoji: {agent.emoji}\npermission:\n  edit: allow\n'
            f'  bash: {bash_perm}\n  task:\n{task}---\n\n'
        )

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'opencode'
        shutil.rmtree(out, ignore_errors=True)
        (out / 'agents').mkdir(parents=True)
        (out / 'docs').mkdir(parents=True)
        (out / 'skills').mkdir(parents=True)
        (out / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = self._frontmatter(agent, provider) + self._apply(agent.body, provider)
            out_file = out / 'agents' / f'{slug}.md'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        # docs/ has subdirectories now (agent-context, governance, baselines)
        shutil.copytree(DOCS_DIR, out / 'docs', dirs_exist_ok=True)
        shutil.copytree(SKILLS_DIR, out / 'skills', dirs_exist_ok=True)
        for bak in (out / 'skills').rglob('*.bak'):
            bak.unlink()

        # Rewrite governance paths in all skill files
        for md in (out / 'skills').rglob('*.md'):
            text = md.read_text(encoding='utf-8')
            rewritten = rewrite_paths(text, self.docs_prefix, self.skills_prefix)
            if rewritten != text:
                md.write_text(rewritten, encoding='utf-8')

        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / 'scripts')

        ok(f'opencode → {out}')
        print(f'    Install global:   uv run scripts/install.py --tool opencode --target ~/.config/opencode')
        print(f'    Install local:    uv run scripts/install.py --tool opencode --target /your/project/.opencode')


class CursorAdapter(ToolAdapter):
    docs_prefix   = '.sdd/docs'
    skills_prefix = '.sdd/skills'

    def _mdc_frontmatter(self, description: str) -> str:
        return f'---\ndescription: >-\n  {description}\nglobs: []\nalwaysApply: false\n---\n\n'

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'cursor'
        shutil.rmtree(out, ignore_errors=True)
        rules_dir = out / '.cursor' / 'rules'
        rules_dir.mkdir(parents=True)
        (out / '.sdd' / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = (self._mdc_frontmatter(agent.description) +
                       f'# {agent.name}\n\n' +
                       self._apply(agent.body, provider))
            out_file = rules_dir / f'{slug}.mdc'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / 'SKILL.md'
            if not skill_file.exists():
                continue
            skill = parse_skill(skill_file)
            ref   = skill_reference_content(skill_dir)
            content = (self._mdc_frontmatter(skill.description) +
                       f'# {skill.name}\n\n' +
                       self._apply(skill.body, provider) + ref)
            (rules_dir / f'{skill_dir.name}.mdc').write_text(content, encoding='utf-8')

        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / '.sdd' / 'scripts')
        ok(f'cursor → {out}')
        print(f'    .cursor/rules/    ← copy to your project root')


class AiderAdapter(ToolAdapter):
    docs_prefix   = '.sdd/docs'
    skills_prefix = '.sdd/skills'

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'aider'
        shutil.rmtree(out, ignore_errors=True)
        (out / 'scripts').mkdir(parents=True)

        lines: list[str] = [
            '# Orquestrum — Agent Conventions\n',
            '\n> Auto-generated by scripts/convert.py — do not edit manually.\n',
        ]

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            lines.append(f'\n---\n\n## Agent: {agent.name}\n\n')
            lines.append(self._apply(agent.body, provider) + '\n')

        lines.append('\n---\n\n# Skills\n')
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / 'SKILL.md'
            if not skill_file.exists():
                continue
            skill = parse_skill(skill_file)
            ref   = skill_reference_content(skill_dir)
            lines.append(f'\n---\n\n## Skill: {skill.name}\n\n')
            lines.append(self._apply(skill.body, provider) + ref + '\n')

        conv = out / 'CONVENTIONS.md'
        conv.write_text(''.join(lines), encoding='utf-8')
        self._check_canonical(conv.read_text(), conv.name, provider)
        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / 'scripts')

        ok(f'aider → {out}')
        print(f'    CONVENTIONS.md    ← copy to your project root')


class WindsurfAdapter(ToolAdapter):
    docs_prefix   = '.sdd/docs'
    skills_prefix = '.sdd/skills'

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'windsurf'
        shutil.rmtree(out, ignore_errors=True)
        (out / 'scripts').mkdir(parents=True)

        lines: list[str] = [
            '# Orquestrum — Agent Rules\n',
            '\n> Auto-generated by scripts/convert.py — do not edit manually.\n',
        ]

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            lines.append(f'\n---\n\n## {agent.name}\n\n')
            lines.append(self._apply(agent.body, provider) + '\n')

        lines.append('\n---\n\n# Skills\n')
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / 'SKILL.md'
            if not skill_file.exists():
                continue
            skill = parse_skill(skill_file)
            ref   = skill_reference_content(skill_dir)
            lines.append(f'\n---\n\n## Skill: {skill.name}\n\n')
            lines.append(self._apply(skill.body, provider) + ref + '\n')

        rules = out / '.windsurfrules'
        rules.write_text(''.join(lines), encoding='utf-8')
        self._check_canonical(rules.read_text(), rules.name, provider)
        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / 'scripts')

        ok(f'windsurf → {out}')
        print(f'    .windsurfrules    ← copy to your project root')


ADAPTERS: dict[str, ToolAdapter] = {
    'claude-code': ClaudeCodeAdapter(),
    'opencode':    OpenCodeAdapter(),
    'cursor':      CursorAdapter(),
    'aider':       AiderAdapter(),
    'windsurf':    WindsurfAdapter(),
}


# ─── Dry run ──────────────────────────────────────────────────────────────────

# Approximate session shapes (tier → (avg input, avg output) per LLM call) and
# call counts. Source: docs/agent-context/TIERS.md (~2 / ~5 / ~13 calls per tier).
# Conservative; prefer over-estimation for budgeting.
SESSION_SHAPES: dict[str, dict] = {
    'tier-0': {
        'calls':  [('mechanical', 2, 1500, 400)],   # 2 mechanical calls
        'label':  'Tier 0 — Micro (typo, config, single-file edit)',
    },
    'tier-1': {
        'calls':  [('balanced', 5, 1800, 500)],
        'label':  'Tier 1 — Standard (epic + tasks + QA)',
    },
    'tier-2': {
        'calls':  [
            ('deep',       2, 4500, 1200),    # spec + adr (heavy reasoning)
            ('balanced',   9, 2200, 600),     # architecture, epic, task, review, qa, learning, etc.
            ('mechanical', 2, 1500, 400),     # changelog, runbook
        ],
        'label':  'Tier 2 — Full pipeline (greenfield feature)',
    },
}


def _session_cost(provider: str, shape: dict) -> tuple[int, int, float]:
    """Return (total_in_tokens, total_out_tokens, total_cost_usd) for one session shape."""
    total_in = 0
    total_out = 0
    total_cost = 0.0
    for tier, calls, in_per_call, out_per_call in shape['calls']:
        model = PROVIDER_MODELS[provider][tier]
        in_t  = calls * in_per_call
        out_t = calls * out_per_call
        total_in  += in_t
        total_out += out_t
        total_cost += estimate_cost(model, in_t, out_t)
    return total_in, total_out, round(total_cost, 4)


def _count_canonical_inventory() -> dict:
    agents = [parse_agent(f) for f in sorted(AGENTS_DIR.glob('*.md'))]
    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / 'SKILL.md').exists():
            skills.append(parse_skill(d / 'SKILL.md'))
    docs_count = sum(1 for _ in DOCS_DIR.rglob('*.md'))
    return {
        'agents':           agents,
        'skills':           skills,
        'docs_count':       docs_count,
        'agent_total_b':    sum(len(a.body.encode('utf-8')) for a in agents),
        'skill_total_b':    sum(len(s.body.encode('utf-8')) for s in skills),
    }


def _count_cache_markers() -> int:
    pattern = re.compile(r'<!--\s*/?cache:(?:stable|volatile)\s*-->', re.IGNORECASE)
    total = 0
    for f in list(AGENTS_DIR.rglob('*.md')) + list(SKILLS_DIR.rglob('*.md')) + list(DOCS_DIR.rglob('*.md')):
        try:
            total += len(pattern.findall(f.read_text(encoding='utf-8')))
        except OSError:
            continue
    return total


def dry_run_report(tools: list[str], provider: str | None) -> None:
    inv = _count_canonical_inventory()

    print(f'{"─" * 72}')
    print(f'  Orquestrum — convert dry-run')
    print(f'{"─" * 72}')
    print(f'  Canonical inventory')
    print(f'    agents:      {len(inv["agents"])} ({inv["agent_total_b"]:,} bytes total)')
    print(f'    skills:      {len(inv["skills"])} ({inv["skill_total_b"]:,} bytes total)')
    print(f'    docs:        {inv["docs_count"]} files under docs/')
    print(f'    cache markers: {_count_cache_markers()}')
    print()

    if provider:
        print(f'  Provider: {provider}')
        for tier in ('deep', 'sharp', 'balanced', 'mechanical'):
            print(f'    {tier:11}: {PROVIDER_MODELS[provider][tier]}')
        collapses = [(n, t, tier_collapse(provider, t)) for n, t in AGENT_TIERS.items()
                     if tier_collapse(provider, t)]
        if collapses:
            print()
            print(f'  ⚠ Tier collapses on \'{provider}\':')
            for name, tier, to in collapses:
                print(f'    {name}: {tier!r} → {to!r}')
        print()
        print(f'  Projected session cost (provider={provider}):')
        print(f'    {"Tier":<8} {"Calls":>5}  {"Input tk":>10}  {"Output tk":>10}  {"USD":>8}  Description')
        print(f'    {"-"*8} {"-"*5}  {"-"*10}  {"-"*10}  {"-"*8}  {"-"*40}')
        for key in ('tier-0', 'tier-1', 'tier-2'):
            shape = SESSION_SHAPES[key]
            in_t, out_t, cost = _session_cost(provider, shape)
            calls = sum(c[1] for c in shape['calls'])
            print(f'    {key:<8} {calls:>5}  {in_t:>10,}  {out_t:>10,}  ${cost:>7.4f}  {shape["label"]}')
        print()
    else:
        print('  Provider: not set — costs not computed (use --provider claude|copilot|glm to project)')
        print()

    print(f'  Tools to generate: {", ".join(tools)}')
    print(f'  → would write to: {INTEGRATIONS}/{{{",".join(tools)}}}/')
    print(f'  → no files written (dry-run)')
    print(f'{"─" * 72}')


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog='orquestrum convert',
        description='Generate integration packages from canonical source.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Tools:     claude-code, opencode, cursor, aider, windsurf\n'
            'Providers: claude (default for claude-code), copilot, glm'
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tool', choices=list(ADAPTERS), metavar='TOOL',
                       help='Single tool to generate')
    group.add_argument('--all', action='store_true', help='Generate all tools')
    parser.add_argument('--provider', choices=list(VALID_PROVIDERS), metavar='PROVIDER',
                        help='Model provider (claude | copilot | glm)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary (inventory, cost projection, tier collapses) without writing files')
    args = parser.parse_args(argv)

    provider = args.provider or None
    tools = list(ADAPTERS) if args.all else [args.tool]

    if args.dry_run:
        dry_run_report(tools, provider)
        return

    if provider:
        log(f'Provider: {provider}')
        models = PROVIDER_MODELS[provider]
        log(f'  deep:       {models["deep"]}')
        log(f'  sharp:      {models["sharp"]}')
        log(f'  balanced:   {models["balanced"]}')
        log(f'  mechanical: {models["mechanical"]}')

        collapses = []
        for agent_name, tier in AGENT_TIERS.items():
            collapsed_to = tier_collapse(provider, tier)
            if collapsed_to:
                collapses.append((agent_name, tier, collapsed_to))
        if collapses:
            warn(f'Tier collapse for provider \'{provider}\' — these agents run on a lower tier than declared:')
            for agent_name, tier, target in collapses:
                target_model = PROVIDER_MODELS[provider][target]
                warn(f'  {agent_name}: \'{tier}\' → \'{target}\' ({target_model})')
            warn('See docs/governance/MODELS.md → Provider Parity Caveats for rationale.')
    else:
        log('Provider: none (model not set — user chooses at runtime; claude-code defaults to claude)')

    print()

    for tool in tools:
        ADAPTERS[tool].convert(provider)
        print()

    if args.all:
        ok('All integrations generated in integrations/')


if __name__ == '__main__':
    main()
