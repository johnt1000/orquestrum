# Orquestrum — developer convenience targets.
#
# `make` (no args) prints help. Most targets are thin wrappers over the
# `orquestrum` CLI; they exist so a new contributor can clone the repo
# and bootstrap without memorising flags.

.PHONY: help dev sync lint convert convert-dry test web doctor audit clean

help:  ## Show this help (default target)
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────

dev: sync  ## Install the CLI in editable mode + ui/webview extras
	uv tool install --editable .
	@echo ""
	@echo "✓ orquestrum installed globally (editable). Try: make doctor"

sync:  ## Refresh the local virtualenv with all extras
	uv sync --extra ui --extra webview

# ── Day-to-day ───────────────────────────────────────────────────────────────

lint:  ## Validate agents and skills (run before convert)
	orquestrum lint

convert:  ## Generate integrations/ for all tools (no provider)
	orquestrum convert --all

convert-dry:  ## Inventory + cost projection without writing files
	orquestrum convert --all --dry-run

test:  ## Run the test suite (placeholder until Onda 4)
	uv run pytest

web:  ## Launch the local FastAPI console (127.0.0.1:7700)
	orquestrum web

doctor:  ## Diagnose the local environment
	orquestrum doctor

audit:  ## Run the reference-payload audit (most common one)
	orquestrum audit payload

# ── Maintenance ──────────────────────────────────────────────────────────────

clean:  ## Remove generated integrations/ (keeps source untouched)
	rm -rf integrations/
	@echo "✓ integrations/ removed; run \`make convert\` to regenerate"
