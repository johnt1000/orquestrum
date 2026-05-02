import sys

RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE   = '\033[0;34m'
NC     = '\033[0m'

_prefix = ''

def set_prefix(p: str) -> None:
    global _prefix
    _prefix = p

def log(msg: str) -> None:
    label = f'[{_prefix}]' if _prefix else '[*]'
    print(f'{BLUE}{label}{NC} {msg}')

def ok(msg: str) -> None:
    print(f'{GREEN}[✓]{NC} {msg}')

def warn(msg: str) -> None:
    print(f'{YELLOW}[!]{NC} {msg}')

def err(msg: str) -> None:
    print(f'{RED}[✗]{NC} {msg}', file=sys.stderr)
