# Contributing to Orquestrum

## Development setup

```bash
git clone https://github.com/johnt1000/orquestrum
cd orquestrum
uv tool install --editable .
uv sync --extra ui --extra webview
```

The `orquestrum` binary is now available globally and points to your local clone —
edits take effect immediately without reinstalling.

## Daily workflow

```bash
orquestrum lint              # validate agents and skills (run before convert)
orquestrum convert --all     # regenerate integrations/ for all tools
orquestrum convert --tool opencode --provider claude   # single tool + provider
```

> Always run `lint` before `convert`. Lint exits 1 on errors.

## Managing optional extras

```bash
orquestrum extras            # show installed / missing extras
orquestrum extras install ui webview
```

## Running tests

```bash
uv run pytest
orquestrum audit parity      # provider parity tests
orquestrum audit payload     # reference payload audit
orquestrum audit attention   # attention score distribution
```

## Updating your local install

```bash
git pull
orquestrum convert --all     # regenerate integrations after source changes
```

Or via the CLI:

```bash
orquestrum update --self     # detects source install → git pull + convert --all
```

## Architecture

See [`CLAUDE.md`](CLAUDE.md) for the full codebase guide — directory layout,
path conventions, agent/skill structure, and conversion behavior.

## Commit style

Short imperative subject line, no period. Reference the area in a prefix when helpful:

```
feat(cli): add orquestrum extras command
fix(convert): handle missing frontmatter name field
docs: update installation section
```
