#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
BIN="$HOME/bin"
CFG="$HOME/.config/hpfa"

mkdir -p "$BIN" "$CFG"

cat > "$BIN/hpfa-set-primary" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

D="${1:-}"
if [ -z "$D" ] || [ ! -d "$D" ]; then
  echo "[FAIL] usage: hpfa-set-primary /path/to/match_dir"
  exit 2
fi

mkdir -p "$HOME/.config/hpfa"
echo "PRIMARY_DIR=$D" > "$HOME/.config/hpfa/primary.env"
export PRIMARY_DIR="$D"

echo "[OK] PRIMARY_DIR=$D"
EOF

cat > "$BIN/hpfa-run" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ENVF="$HOME/.config/hpfa/primary.env"
if [ ! -f "$ENVF" ]; then
  echo "[FAIL] PRIMARY_DIR not set. Run: hpfa-set-primary /path/to/match_dir"
  exit 11
fi

# shellcheck disable=SC1090
source "$ENVF"
if [ -z "${PRIMARY_DIR:-}" ] || [ ! -d "$PRIMARY_DIR" ]; then
  echo "[FAIL] PRIMARY_DIR invalid: ${PRIMARY_DIR:-EMPTY}"
  exit 12
fi

exec "$HOME/hpfa/tools/hpfa_run_guarded.sh" "$PRIMARY_DIR" --save-meta "$@"
EOF

chmod +x "$BIN/hpfa-set-primary" "$BIN/hpfa-run"

echo "[OK] installed:"
ls -lah "$BIN/hpfa-run" "$BIN/hpfa-set-primary"
