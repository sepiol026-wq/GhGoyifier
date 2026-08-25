#!/usr/bin/env bash
# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
set -euo pipefail

REPO_URL="${GHGOYIFIER_REPO:-https://github.com/sepiol026-wq/GhGoyifier.git}"
INSTALL_DIR="${GHGOYIFIER_DIR:-${HOME}/.local/share/GhGoyifier}"
BIN_DIR="${GHGOYIFIER_BIN:-${HOME}/.local/bin}"
BRANCH="${GHGOYIFIER_BRANCH:-main}"
if [ -r /dev/tty ]; then
  INPUT_DEVICE=/dev/tty
else
  INPUT_DEVICE=/dev/stdin
fi

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null || fail "git is required"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
[ -n "$PYTHON_BIN" ] || fail "python3 is required"

say "Installing GhGoyifier from ${REPO_URL}"
mkdir -p "$(dirname "$INSTALL_DIR")" "$BIN_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
  if [ ! -w "$INSTALL_DIR/.git/objects" ]; then
    if [ "$(id -u)" -eq 0 ]; then
      chown -R "$(id -u):$(id -g)" "$INSTALL_DIR"
    elif command -v sudo >/dev/null; then
      sudo chown -R "$(id -u):$(id -g)" "$INSTALL_DIR"
    else
      fail "Installation directory is not writable and sudo is unavailable: $INSTALL_DIR"
    fi
  fi
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
if command -v uv >/dev/null; then
  printf 'uv found. Use uv to create the environment and install dependencies? [Y/n] '
  read -r use_uv < "$INPUT_DEVICE"
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
  "")
    exec "$INSTALL_DIR/.venv/bin/python" -m GhGoyifier --help
    ;;
  config|gateway|logs|doctor|status|update|uninstall|-h|--help|-v|--version)
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
"$INSTALL_DIR/.venv/bin/python" -m GhGoyifier config --file "$INSTALL_DIR/config.toml" < "$INPUT_DEVICE"

if [ "$(id -u)" -eq 0 ]; then
  "$BIN_DIR/ghgoyifi" gateway install && "$BIN_DIR/ghgoyifi" gateway enable || say "Native service enablement failed; direct gateway mode remains available"
elif command -v sudo >/dev/null; then
  sudo "$BIN_DIR/ghgoyifi" gateway install && sudo "$BIN_DIR/ghgoyifi" gateway enable || say "Native service enablement failed; direct gateway mode remains available"
else
  say "sudo is unavailable; direct gateway mode remains available"
fi

say "Installed aliases: ghgoyifi, ghgoyifier, GhGoyifier"
proxy_env_file="${XDG_CONFIG_HOME:-$HOME/.config}/environment.d/90-goyifier-proxy.conf"
if [ -n "${HTTP_PROXY:-}${HTTPS_PROXY:-}${ALL_PROXY:-}${NO_PROXY:-}${http_proxy:-}${https_proxy:-}${all_proxy:-}${no_proxy:-}" ]; then
  mkdir -p "$(dirname "$proxy_env_file")"
  umask 077
  : > "$proxy_env_file"
  for proxy_name in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy; do
    proxy_value=${!proxy_name:-}
    if [ -n "$proxy_value" ]; then
      proxy_value=${proxy_value//\\/\\\\}
      proxy_value=${proxy_value//\"/\\\"}
      printf '%s="%s"\n' "$proxy_name" "$proxy_value" >> "$proxy_env_file"
    fi
  done
  chmod 600 "$proxy_env_file"
  say "Saved proxy environment for systemd"
fi
COMMAND_BIN="$BIN_DIR/ghgoyifi"
if [ "$(id -u)" -eq 0 ]; then
  PRIVILEGE=""
elif command -v sudo >/dev/null; then
  PRIVILEGE=sudo
fi
if [ -n "${PRIVILEGE:-}" ] || [ "$(id -u)" -eq 0 ]; then
  if ${PRIVILEGE:-} install -m 755 "$BIN_DIR/ghgoyifi" /usr/local/bin/ghgoyifi && \
     ${PRIVILEGE:-} ln -sfn ghgoyifi /usr/local/bin/ghgoyifier && \
     ${PRIVILEGE:-} ln -sfn ghgoyifi /usr/local/bin/GhGoyifier; then
    COMMAND_BIN=/usr/local/bin/ghgoyifi
    say "Installed global commands in /usr/local/bin"
  else
    say "Global command installation failed; user-local aliases remain available"
  fi
else
  say "sudo is unavailable; user-local aliases remain in $BIN_DIR"
fi
say "Run: $COMMAND_BIN gateway start"
