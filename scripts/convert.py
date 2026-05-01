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
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.log import log, ok, warn, err, set_prefix
from lib.models import (
    VALID_PROVIDERS, VALID_TOOLS, PROVIDER_MODELS,
    CANONICAL_MODELS, HELM_NAME, ORCHESTRATOR_NAMES,
    resolve_model, apply_provider_models,
)
from lib.frontmatter import parse_agent, parse_skill, AgentConfig
from lib.paths import rewrite_paths, name_to_kebab, skill_reference_content

set_prefix('convert')

ROOT         = Path(__file__).parent.parent
INTEGRATIONS = ROOT / 'integrations'
AGENTS_DIR   = ROOT / 'agents'
SKILLS_DIR   = ROOT / 'skills'
DOCS_DIR     = ROOT / 'docs'
BUNDLE_DIR   = ROOT / 'bundle'


# ─── Adapters ─────────────────────────────────────────────────────────────────

class ToolAdapter(ABC):
    docs_prefix:   str
    skills_prefix: str

    @abstractmethod
    def convert(self, provider: str | None) -> None: ...

    def _apply(self, body: str, provider: str | None) -> str:
        return apply_provider_models(rewrite_paths(body, self.docs_prefix, self.skills_prefix), provider)

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
        lines = ['---', f'name: {agent.name}', f'description: {agent.description}',
                 f'model: {model}', f'temperature: {agent.temperature}']
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
        (out / '.sdd' / 'docs').mkdir(parents=True)
        (out / '.sdd' / 'skills').mkdir(parents=True)
        (out / '.sdd' / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = self._frontmatter(agent, provider) + self._apply(agent.body, provider)
            out_file = agents_out / f'{slug}.md'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        for md in DOCS_DIR.glob('*.md'):
            shutil.copy(md, out / '.sdd' / 'docs' / md.name)
        shutil.copytree(SKILLS_DIR, out / '.sdd' / 'skills', dirs_exist_ok=True)
        for bak in (out / '.sdd' / 'skills').rglob('*.bak'):
            bak.unlink()
        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / '.sdd' / 'scripts')

        ok(f'claude-code → {out}')
        print(f'    .claude/agents/   ← copy to your project\'s .claude/agents/')
        print(f'    .sdd/             ← copy to your project root')


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
            f'---\nname: {agent.name}\ndescription: {agent.description}\n'
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

        for md in DOCS_DIR.glob('*.md'):
            shutil.copy(md, out / 'docs' / md.name)
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


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
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
    args = parser.parse_args()

    provider = args.provider or None

    if provider:
        log(f'Provider: {provider}')
        models = PROVIDER_MODELS[provider]
        log(f'  deep:       {models["deep"]}')
        log(f'  sharp:      {models["sharp"]}')
        log(f'  balanced:   {models["balanced"]}')
        log(f'  mechanical: {models["mechanical"]}')
    else:
        log('Provider: none (model not set — user chooses at runtime; claude-code defaults to claude)')

    print()

    tools = list(ADAPTERS) if args.all else [args.tool]
    for tool in tools:
        ADAPTERS[tool].convert(provider)
        print()

    if args.all:
        ok('All integrations generated in integrations/')


if __name__ == '__main__':
    main()
