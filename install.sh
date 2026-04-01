#!/bin/bash
# install.sh — c-daily one-command installer
# curl -fsSL https://raw.githubusercontent.com/atsushi729/c-daily/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/atsushi729/c-daily"
INSTALL_DIR="${HOME}/.local/share/c-daily"
BIN_DIR="${HOME}/.local/bin"

# Color output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}"
cat <<'BANNER'
   ___  ___  ___  __
  / __\/ __\| _ \/ _\
 | /  | /  |   /\ \
 |_\  |_\  |_|_\\_/   v0.1.0
BANNER
echo -e "${RESET}"
echo "Claude Code daily log auto-generator"
echo ""

# --- Dependency check ---
fail() { echo -e "${RED}❌ $1${RESET}"; exit 1; }
ok()   { echo -e "${GREEN}✅ $1${RESET}"; }
warn() { echo -e "${YELLOW}⚠️  $1${RESET}"; }

command -v python3 &>/dev/null || fail "python3 is required: https://brew.sh → brew install python3"
command -v git     &>/dev/null || fail "git is required"
python3 -c "import sys; exit(0 if sys.version_info>=(3,9) else 1)" || \
  fail "Python 3.9 or higher required (current: $(python3 --version))"
ok "Dependency check passed"

# --- Install or update ---
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "🔄 Updating c-daily..."
  git -C "$INSTALL_DIR" pull --quiet
  ok "Update complete"
else
  echo "📦 Downloading c-daily..."
  git clone --quiet --depth 1 "$REPO" "$INSTALL_DIR"
  ok "Download complete"
fi

# --- Add bin/c-daily to PATH ---
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/bin/c-daily" "$BIN_DIR/c-daily"
chmod +x "$INSTALL_DIR/bin/c-daily"
ok "Linked c-daily command to $BIN_DIR"

# --- Configure PATH (if not already set) ---
SHELL_RC=""
case "${SHELL:-}" in
  */zsh)  SHELL_RC="${HOME}/.zshrc" ;;
  */bash) SHELL_RC="${HOME}/.bashrc" ;;
esac

if [ -n "$SHELL_RC" ] && ! echo "$PATH" | grep -q "$BIN_DIR"; then
  {
    echo ""
    echo "# c-daily"
    printf 'export PATH="%s:$PATH"\n' "$BIN_DIR"
  } >> "$SHELL_RC"
  warn "Added PATH to $SHELL_RC. To apply now:"
  echo "  source $SHELL_RC"
fi

# --- Done ---
echo ""
echo -e "${BOLD}🎉 Installation complete!${RESET}"
echo ""
echo "Next steps:"
echo -e "  ${BOLD}c-daily install${RESET}   Set up Claude Code hooks and launchd"
echo -e "  ${BOLD}c-daily today${RESET}     Test log generation"
echo -e "  ${BOLD}c-daily help${RESET}      Show all commands"
echo ""
echo "Documentation: $REPO"
