#!/usr/bin/env bash
# Orquestrum installer — https://github.com/johnt1000/orquestrum
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/johnt1000/orquestrum/main/install.sh | bash
#   bash install.sh               # full install (CLI + web console + app window)
#   bash install.sh --minimal     # CLI only
#   bash install.sh --no-webview  # CLI + web console, no pywebview
set -euo pipefail

# ── colours ─────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
  RED='\033[0;31m'; RESET='\033[0m'
else
  BOLD=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

step()  { echo -e "${BOLD}▸ $*${RESET}"; }
ok()    { echo -e "  ${GREEN}✓${RESET} $*"; }
warn()  { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
fail()  { echo -e "  ${RED}✗${RESET} $*"; exit 1; }

# ── flags ────────────────────────────────────────────────────────────────────
MINIMAL=0
NO_WEBVIEW=0
for arg in "$@"; do
  case "$arg" in
    --minimal)    MINIMAL=1 ;;
    --no-webview) NO_WEBVIEW=1 ;;
    --help|-h)
      echo "Usage: bash install.sh [--minimal] [--no-webview]"
      echo "  --minimal      Install CLI only (no web console or app window)"
      echo "  --no-webview   Install CLI + web console, skip pywebview"
      exit 0 ;;
    *) warn "Unknown flag: $arg — ignored" ;;
  esac
done

# ── header ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Orquestrum Installer${RESET}"
printf '%0.s─' {1..40}; echo ""
echo ""

# ── 1. OS check ─────────────────────────────────────────────────────────────
step "Checking prerequisites..."

OS="$(uname -s)"
case "$OS" in
  Darwin) ok "macOS detected" ;;
  Linux)  ok "Linux detected" ;;
  *)      fail "Unsupported OS: $OS — Orquestrum requires macOS or Linux." ;;
esac

# ── 2. Python 3.12+ ─────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "${major:-0}" -ge 3 ] && [ "${minor:-0}" -ge 12 ]; then
      PYTHON="$candidate"
      ok "Python $ver found ($candidate)"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  fail "Python 3.12+ is required. Install from https://python.org or via your package manager."
fi

# ── 3. uv ────────────────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
  UV_VER=$(uv --version 2>/dev/null | awk '{print $2}')
  ok "uv ${UV_VER} found"
else
  warn "uv not found — installing via https://astral.sh/uv/install.sh"
  echo ""
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Source the cargo/uv env so the binary is available in this shell session
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv &>/dev/null; then
    fail "uv installation failed. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
  fi
  UV_VER=$(uv --version 2>/dev/null | awk '{print $2}')
  ok "uv ${UV_VER} installed"
fi
echo ""

# ── 4. Build uv tool install command ─────────────────────────────────────────
step "Installing orquestrum..."

REPO="git+https://github.com/johnt1000/orquestrum"

UI_PACKAGES=(
  "fastapi>=0.115"
  "uvicorn[standard]>=0.32"
  "jinja2>=3.1"
  "mistune>=3.0"
  "watchfiles>=0.24"
  "python-multipart>=0.0.20"
)
WEBVIEW_PACKAGES=("pywebview>=5.0")

UV_ARGS=()
if [ "$MINIMAL" -eq 0 ]; then
  for pkg in "${UI_PACKAGES[@]}"; do
    UV_ARGS+=(--with "$pkg")
  done
  if [ "$NO_WEBVIEW" -eq 0 ]; then
    # Linux: warn about GTK prerequisite before attempting webview
    if [ "$OS" = "Linux" ]; then
      warn "pywebview on Linux requires libwebkit2gtk-4.0-dev"
      warn "Run: sudo apt install libwebkit2gtk-4.0-dev  # Debian/Ubuntu"
      warn "     sudo dnf install webkit2gtk4.0-devel    # Fedora/RHEL"
      warn "Skipping pywebview. Re-run without --no-webview after installing system deps."
      echo ""
    else
      for pkg in "${WEBVIEW_PACKAGES[@]}"; do
        UV_ARGS+=(--with "$pkg")
      done
    fi
  fi
fi

uv tool install "${UV_ARGS[@]}" "$REPO"
echo ""

# ── 5. PATH check ────────────────────────────────────────────────────────────
step "Checking PATH..."

LOCAL_BIN="$HOME/.local/bin"
if echo "$PATH" | grep -q "$LOCAL_BIN"; then
  ok "$LOCAL_BIN is in PATH"
else
  warn "$LOCAL_BIN is not in PATH"
  warn "Add the following to your ~/.zshrc or ~/.bashrc:"
  warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  warn "Then restart your terminal or run: source ~/.zshrc"
fi
echo ""

# ── 6. Verify ────────────────────────────────────────────────────────────────
step "Verifying installation..."

export PATH="$LOCAL_BIN:$PATH"
if command -v orquestrum &>/dev/null; then
  VERSION=$(orquestrum --version 2>/dev/null || echo "unknown")
  ok "$VERSION"
else
  fail "orquestrum binary not found after install. Check that $LOCAL_BIN is in PATH."
fi
echo ""

# ── 7. Next steps ────────────────────────────────────────────────────────────
printf '%0.s─' {1..40}; echo ""
echo -e "${GREEN}${BOLD}Installation complete!${RESET}"
echo ""
echo "Next steps:"
echo "  cd /path/to/your/project"
echo "  orquestrum init --tool claude-code"
echo "  orquestrum web"
echo ""
echo "Docs: https://github.com/johnt1000/orquestrum"
echo ""
