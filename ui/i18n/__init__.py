"""i18n — flat dict-based locale lookup for the Orquestrum console.

Two locales: 'pt' (default, primary) and 'en' (fallback). One JSON file per
locale lives next to this module. The Jinja `t` filter (registered in
ui.server) resolves keys with `current → fallback en → key itself`.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SUPPORTED: tuple[str, ...] = ('pt', 'en')
DEFAULT: str = 'pt'
FALLBACK: str = 'en'


@lru_cache(maxsize=None)
def load(locale: str) -> dict[str, str]:
    """Load a locale dict (cached). Returns empty dict if file missing."""
    path = _HERE / f'{locale}.json'
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def resolve(locale: str) -> str:
    """Coerce any input to a supported locale, falling back to DEFAULT."""
    return locale if locale in SUPPORTED else DEFAULT


def translate(key: str, locale: str = DEFAULT, **vars: object) -> str:
    """Look up `key` in `locale`, falling back to FALLBACK then to the key.

    `vars` are interpolated with str.format_map for `{name}` placeholders.
    """
    primary = load(resolve(locale))
    text = primary.get(key)
    if text is None and locale != FALLBACK:
        text = load(FALLBACK).get(key)
    if text is None:
        text = key
    if vars:
        try:
            text = text.format_map(vars)
        except (KeyError, IndexError):
            pass
    return text
