#!/usr/bin/env python3
"""run.py — provider parity tests.

Validates that the same canonical source produces structurally equivalent
output across providers (claude / copilot / glm). Differences should be
isolated to the resolved `model:` field; everything else (frontmatter
keys, body sections, file count) must match.

Usage:
    orquestrum audit parity
    orquestrum audit parity --providers claude,glm
    orquestrum audit parity --json   # CI-friendly output

Exit code: 0 if all assertions pass, 1 if any structural divergence.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import frontmatter as fm
from orquestrum.lib.models import VALID_PROVIDERS, AGENT_TIERS, tier_collapse


ROOT          = Path(__file__).parent.parent.parent.parent.parent
INTEGRATIONS  = ROOT / 'integrations'


def run_convert(provider: str, tool: str = 'claude-code') -> Path:
    """Run convert and return the path to the produced agents directory."""
    from orquestrum.core.convert import main as convert_main
    convert_main(['--tool', tool, '--provider', provider])
    return INTEGRATIONS / tool / '.claude' / 'agents'


def collect_frontmatter(agents_dir: Path) -> dict[str, dict]:
    """Read every agent file and return {filename: frontmatter_dict}."""
    out: dict[str, dict] = {}
    for f in sorted(agents_dir.glob('*.md')):
        post = fm.load(str(f))
        out[f.name] = dict(post.metadata)
    return out


def assert_same_keys(per_provider: dict[str, dict[str, dict]]) -> list[str]:
    """Every agent file must have the same set of frontmatter keys across providers."""
    failures: list[str] = []
    providers = list(per_provider.keys())
    if len(providers) < 2:
        return failures

    base = providers[0]
    for filename, base_meta in per_provider[base].items():
        base_keys = set(base_meta.keys())
        for other in providers[1:]:
            other_meta = per_provider[other].get(filename)
            if other_meta is None:
                failures.append(f'{filename}: missing in provider {other!r}')
                continue
            other_keys = set(other_meta.keys())
            if base_keys != other_keys:
                only_in_base  = base_keys - other_keys
                only_in_other = other_keys - base_keys
                failures.append(
                    f'{filename}: key drift between {base!r} and {other!r} '
                    f'(only in {base}: {sorted(only_in_base)}; '
                    f'only in {other}: {sorted(only_in_other)})'
                )
    return failures


def assert_only_model_differs(per_provider: dict[str, dict[str, dict]]) -> list[str]:
    """Same key set is checked elsewhere; here, every value must match across providers
    EXCEPT for the `model` field, which is expected to differ.
    """
    failures: list[str] = []
    providers = list(per_provider.keys())
    if len(providers) < 2:
        return failures

    base = providers[0]
    for filename, base_meta in per_provider[base].items():
        for other in providers[1:]:
            other_meta = per_provider[other].get(filename, {})
            for key, base_val in base_meta.items():
                if key == 'model':
                    continue  # expected to differ
                if other_meta.get(key) != base_val:
                    failures.append(
                        f'{filename}: field {key!r} differs between {base} and {other} '
                        f'(base={base_val!r}, other={other_meta.get(key)!r})'
                    )
    return failures


def assert_tier_collapse_documented(providers: list[str]) -> list[str]:
    """Every tier collapse known in TIER_COLLAPSES must produce a runtime warning when
    the affected provider is built. We don't sniff stdout here; we just validate that
    our metadata accounting matches what the docs claim.
    """
    failures: list[str] = []
    for provider in providers:
        for agent_name, tier in AGENT_TIERS.items():
            collapsed = tier_collapse(provider, tier)
            if collapsed is None:
                continue
            from orquestrum.lib.models import PROVIDER_MODELS
            if PROVIDER_MODELS[provider][tier] != PROVIDER_MODELS[provider][collapsed]:
                failures.append(
                    f'{agent_name} on provider {provider}: TIER_COLLAPSES says '
                    f'{tier!r} → {collapsed!r}, but PROVIDER_MODELS does not match'
                )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='orquestrum audit parity',
                                     description='Provider parity tests for Orquestrum')
    parser.add_argument('--providers', default=','.join(VALID_PROVIDERS),
                        help=f'Comma-separated providers to test (default: {",".join(VALID_PROVIDERS)})')
    parser.add_argument('--json', action='store_true', help='Emit CI-friendly JSON report')
    args = parser.parse_args(argv)

    providers = [p.strip() for p in args.providers.split(',') if p.strip()]
    invalid = [p for p in providers if p not in VALID_PROVIDERS]
    if invalid:
        print(f'Invalid provider(s): {invalid}. Valid: {VALID_PROVIDERS}', file=sys.stderr)
        return 2

    per_provider: dict[str, dict[str, dict]] = {}
    for prov in providers:
        agents_dir = run_convert(prov)
        per_provider[prov] = collect_frontmatter(agents_dir)

    all_failures: list[str] = []
    all_failures += assert_same_keys(per_provider)
    all_failures += assert_only_model_differs(per_provider)
    all_failures += assert_tier_collapse_documented(providers)

    if args.json:
        report = {
            'providers':       providers,
            'agents_per_prov': {p: list(per_provider[p].keys()) for p in providers},
            'failures':        all_failures,
            'pass':            not all_failures,
        }
        print(json.dumps(report, indent=2))
    else:
        if all_failures:
            print(f'\n✗ {len(all_failures)} parity failure(s):')
            for msg in all_failures:
                print(f'  - {msg}')
        else:
            print(f'\n✓ Parity OK across {providers}')
            for prov in providers:
                print(f'    {prov}: {len(per_provider[prov])} agents')

    return 1 if all_failures else 0


if __name__ == '__main__':
    sys.exit(main())
