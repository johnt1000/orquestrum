# Distribution Policy

How Orquestrum is distributed today, why we restrict to Mac + Linux, and the roadmap for broader package channels.

---

## Audience

**Operating systems:** macOS (12+) and Linux (any modern distro). **Windows is not supported.**

The decision is deliberate, not lazy:

- The framework writes hooks into `.claude/settings.json` whose `command:` field assumes POSIX shell semantics (`uv run .sdd/scripts/hooks/emit_metrics.py`). Windows path separators and the absence of `/usr/bin` style binaries make this fragile.
- File-system invariants (`~/.orquestrum/registry.toml` resolution, atomic `os.replace` semantics, `pathlib.Path` POSIX behavior) are tested only on macOS and Linux.
- Process-supervision (`subprocess.run` with `cwd`, signal handling, `webbrowser.open`) has subtle Windows differences that we don't have time to validate.
- `uv tool install` and `pipx install` global-binary installation has known Windows quirks around PATH, `.exe` shims, and `--editable` mode.

WSL2 is best-effort — most things work, but we don't ship explicit fixes for issues unique to it.

---

## Today (v0.2)

The canonical install is **`uv tool install`** from the GitHub repository:

```bash
uv tool install git+https://github.com/johnt1000/orquestrum
```

This:
- Resolves Python 3.12+
- Installs into an isolated venv under `~/.local/share/uv/tools/orquestrum/`
- Symlinks `orquestrum` into `~/.local/bin/`
- Picks up updates via `uv tool upgrade orquestrum`

Alternatives that work today:

- `pipx install git+https://github.com/johnt1000/orquestrum`
- `uv tool install --editable /path/to/clone` (development; `git pull` updates the source)
- Manual `git clone` + `make dev` (developer install; binary stays linked to the clone)

We do **not** publish to PyPI yet. Once the CLI surface stabilizes (target: v0.5), PyPI becomes the canonical channel for `pip install orquestrum`.

---

## Roadmap (≥ v0.5)

### macOS — Homebrew tap

```bash
brew tap johnt1000/orquestrum
brew install orquestrum
```

Mechanics:
- Tap repo: `johnt1000/homebrew-orquestrum` (separate from the main repo)
- Formula installs the `orquestrum` Python package into `/opt/homebrew/Cellar/orquestrum/X.Y.Z/`
- Symlinks `orquestrum` into `/opt/homebrew/bin/`
- Optional `[ui]` extras via `brew install orquestrum --with-ui`

### Debian / Ubuntu — APT repository

```bash
curl -fsSL https://orquestrum.dev/apt/keyring.asc | sudo gpg --dearmor -o /etc/apt/keyrings/orquestrum.gpg
echo "deb [signed-by=/etc/apt/keyrings/orquestrum.gpg] https://orquestrum.dev/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/orquestrum.list
sudo apt update
sudo apt install orquestrum
```

Mechanics:
- `.deb` packages built per release for amd64 and arm64
- Depends on `python3 (>= 3.12)`, `python3-pip`
- Installs into `/usr/lib/orquestrum/` with a wrapper at `/usr/bin/orquestrum`
- Optional `orquestrum-ui` package for the web console

### Arch User Repository (AUR)

```bash
yay -S orquestrum-bin       # binary release
yay -S orquestrum-git       # git HEAD
```

PKGBUILD scripts maintained alongside the main repo under `packaging/aur/`.

### Nix flake

```bash
nix profile install github:johnt1000/orquestrum
# or
nix run github:johnt1000/orquestrum -- init --tool claude-code
```

`flake.nix` at repo root exposes `packages.orquestrum` and `apps.orquestrum`.

---

## Versioning

Semantic versioning. Breaking changes:

- **MAJOR**: changes to the CLI command surface that require user action (e.g., renamed subcommand). Changes to canonical schemas (frontmatter shape, registry.toml structure) that older clients can't read.
- **MINOR**: new commands, new flags, new schema fields (additive). New skills or agents.
- **PATCH**: bug fixes, doc updates, hook contract additions that maintain backwards compatibility.

Tagged releases via `git tag vX.Y.Z` + GitHub Releases. CHANGELOG follows Keep a Changelog format (the framework already has `changelog-manager` skill — eat your own cooking).

---

## Release process (target: stabilize before v0.5)

1. Bump `__version__` in `orquestrum/__init__.py` and `pyproject.toml`
2. Update `CHANGELOG.md` (or generate via `orquestrum` `changelog-manager` skill)
3. `git tag vX.Y.Z && git push --tags`
4. CI (TBD) builds wheels + creates GitHub Release
5. Per-channel publish jobs:
   - PyPI (when v0.5+): `uv build && uv publish`
   - Homebrew tap: bump formula version + sha256
   - APT/AUR/Nix: manual or scripted bump

CI matrix (TBD):
- `macos-latest` (arm64)
- `ubuntu-latest` (amd64)
- Python 3.12 and 3.13
- Both `--no-extras` and `--extra ui` test runs

---

## Telemetry & supply chain

- **Zero outbound network calls** by default. The framework runs locally; the web console binds 127.0.0.1.
- External dependency installs (`orquestrum deps`) clone from pinned SHAs in `pinned_refs.toml`. See `docs/governance/SUPPLY_CHAIN.md`.
- Wheels published in any channel will be signed (Sigstore / GitHub Attestations) starting at v0.5.

---

## Why no Windows support is unlikely to change soon

| Cost | Estimate |
|------|----------|
| Hook command shim that works on PowerShell + cmd + Git Bash | ~1 sprint |
| Path-rewriting for `\\` separators across `convert.py` adapters | ~3 days |
| CI matrix expanded to `windows-latest` | ~1 week of flaky-test debugging |
| Documentation + cross-platform examples | ~3 days |
| **Maintenance ongoing** | recurring — every Windows-specific bug becomes ours |

Until there's clear demand, the cost-benefit doesn't justify it. Mac + Linux covers ~95% of professional AI-development environments today.

---

## How to ask for a new channel

Open an issue with title `[distribution] <channel>`. Include:

- Why your environment can't use `uv tool install` directly
- Whether you'd help maintain the channel (formula, package recipe)
- An estimate of users that would benefit

We say yes more easily to channels with a maintainer offer.
