"""orquestrum.lib.prompts — minimal interactive prompt helpers for `init`.

Three primitives:
  - `ask_yn(question, default)`     → bool
  - `ask_choice(question, options)` → str (one of `options`)
  - `ask_text(question, default)`   → str

Each helper respects an `interactive=False` flag (or `OQUESTRUM_NONINTERACTIVE=1`
env var) to fall back to defaults silently — the path used by CI / `-y` flag.
Also falls back when stdin is not a TTY (piped input on a one-shot script).

Why a thin local module instead of `click`/`prompt_toolkit`/`rich`:
  - Single optional dep in `init` shouldn't pull a 30-package tree.
  - The prompts are small and predictable; ANSI handling is already mirrored
    in `lib.log` / `lib.verify`.
  - Tests can monkeypatch `_read_line` to feed scripted input.
"""
from __future__ import annotations
import os
import sys
from typing import Sequence


_GREEN  = '\033[0;32m'
_YELLOW = '\033[1;33m'
_DIM    = '\033[2m'
_BOLD   = '\033[1m'
_NC     = '\033[0m'


def _is_interactive() -> bool:
    """True only when stdin is a TTY and the env opt-out isn't set."""
    if os.environ.get('ORQUESTRUM_NONINTERACTIVE'):
        return False
    try:
        return sys.stdin.isatty()
    except (AttributeError, OSError):
        return False


def _read_line(prompt: str) -> str:
    """Wrapped for tests — monkeypatch this to feed scripted answers.

    Catches EOFError (e.g. stdin closed mid-prompt) and returns ''
    so callers fall through to the default.
    """
    try:
        return input(prompt)
    except EOFError:
        return ''


def ask_yn(question: str, *, default: bool = True, interactive: bool = True) -> bool:
    """Yes/no prompt. `default` is taken when the user just hits enter, when
    interactive=False, or when stdin isn't a TTY."""
    if not interactive or not _is_interactive():
        return default

    suffix = '[Y/n]' if default else '[y/N]'
    while True:
        raw = _read_line(f'{_BOLD}?{_NC} {question} {_DIM}{suffix}{_NC} ').strip().lower()
        if raw == '':
            return default
        if raw in ('y', 'yes', 's', 'sim'):
            return True
        if raw in ('n', 'no', 'nao', 'não'):
            return False
        print(f'{_YELLOW}  please answer y or n (or press enter for default){_NC}')


def ask_choice(question: str, options: Sequence[tuple[str, str]],
               *, default: str | None = None,
               interactive: bool = True) -> str:
    """Multiple-choice prompt.

    `options` is a sequence of `(key, description)`. Keys must be single-letter
    or short tokens (e.g. 'g', 'p', 'skip'). The user types the key; trailing
    space and case are tolerated. Returns the matched key.

    `default` (when given) is a key from `options`; if the user just hits enter
    or the prompt is non-interactive, it is returned.
    """
    keys = [k for k, _ in options]
    if default is not None and default not in keys:
        raise ValueError(f'default {default!r} not in {keys}')

    if not interactive or not _is_interactive():
        if default is None:
            raise RuntimeError('non-interactive mode requires a default')
        return default

    print(f'{_BOLD}?{_NC} {question}')
    for k, desc in options:
        marker = f'{_GREEN}*{_NC}' if k == default else ' '
        print(f'  {marker} [{_BOLD}{k}{_NC}] {desc}')
    suffix = f'[{"/".join(keys)}]'
    if default is not None:
        suffix += f' (default: {default})'

    while True:
        raw = _read_line(f'  {_DIM}{suffix}{_NC} ').strip().lower()
        if raw == '' and default is not None:
            return default
        for k in keys:
            if raw == k.lower():
                return k
        print(f'{_YELLOW}  pick one of: {", ".join(keys)}{_NC}')


def ask_text(question: str, *, default: str = '',
             interactive: bool = True) -> str:
    """Free-text prompt. Returns the trimmed answer or the default."""
    if not interactive or not _is_interactive():
        return default
    suffix = f' {_DIM}(default: {default}){_NC}' if default else ''
    raw = _read_line(f'{_BOLD}?{_NC} {question}{suffix} ').strip()
    return raw or default
