#!/usr/bin/env bash
# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
set -euo pipefail

REPO_URL="${GHGOYIFIER_REPO:-https://github.com/sepiol026-wq/GhGoyifier.git}"
INSTALL_DIR="${GHGOYIFIER_DIR:-${HOME}/.local/share/GhGoyifier}"
BIN_DIR="${GHGOYIFIER_BIN:-${HOME}/.local/bin}"
BRANCH="${GHGOYIFIER_BRANCH:-main}"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null || fail "git is required"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
[ -n "$PYTHON_BIN" ] || fail "python3 is required"

say "Installing GhGoyifier from ${REPO_URL}"
mkdir -p "$(dirname "$INSTALL_DIR")" "$BIN_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
if command -v uv >/dev/null; then
  printf 'uv found. Use uv to create the environment and install dependencies? [Y/n] '
  read -r use_uv
  case "${use_uv:-Y}" in
    [Yy]|[Yy][Ee][Ss])
      uv venv --python "$PYTHON_BIN" .venv
      uv pip install --python .venv/bin/python -r requirements.txt
      ;;
    *)
      "$PYTHON_BIN" -m venv .venv
      .venv/bin/python -m pip install --upgrade pip >/dev/null
      .venv/bin/python -m pip install -r requirements.txt
      ;;
  esac
else
  say "uv not found; using Python venv and pip"
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
fi

cat > "$BIN_DIR/ghgoyifi" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$INSTALL_DIR"
case "\${1:-}" in
  ""|config|gateway|logs|doctor|status|update|uninstall|-h|--help|--version)
    exec "$INSTALL_DIR/.venv/bin/python" -m GhGoyifier "\$@"
    ;;
  *)
    exec "$INSTALL_DIR/.venv/bin/python" -m GhGoyifier --config "$INSTALL_DIR/config.toml" "\$@"
    ;;
esac
EOF
chmod 755 "$BIN_DIR/ghgoyifi"
ln -sfn ghgoyifi "$BIN_DIR/ghgoyifier"
ln -sfn ghgoyifi "$BIN_DIR/GhGoyifier"

say "Opening Rich configuration TUI"
"$INSTALL_DIR/.venv/bin/python" -m GhGoyifier config --file "$INSTALL_DIR/config.toml"

if [ "$(id -u)" -eq 0 ]; then
  "$BIN_DIR/ghgoyifi" gateway install && "$BIN_DIR/ghgoyifi" gateway enable || say "Native service enablement failed; direct gateway mode remains available"
elif command -v sudo >/dev/null; then
  sudo "$BIN_DIR/ghgoyifi" gateway install && sudo "$BIN_DIR/ghgoyifi" gateway enable || say "Native service enablement failed; direct gateway mode remains available"
else
  say "sudo is unavailable; direct gateway mode remains available"
fi

say "Installed aliases: ghgoyifi, ghgoyifier, GhGoyifier"
say "Run: $BIN_DIR/ghgoyifi gateway start"
case ":${PATH}:" in *":$BIN_DIR:"*) ;; *) printf '\nAdd to PATH: export PATH="%s:\$PATH"\n' "$BIN_DIR" ;; esac
