#!/usr/bin/env bash
set -euo pipefail

CFG="$HOME/.config/hpfa"
mkdir -p "$CFG"

cat > "$CFG/helpers.sh" <<'EOF'
# HPFA helpers (sourced)
# Intentionally does NOT define hpfa-run / hpfa-set-primary.
# SSOT commands live in $HOME/bin as executable scripts.

hpfa-primary() {
  local f="$HOME/.config/hpfa/primary.env"
  if [ -f "$f" ]; then
    # shellcheck disable=SC1090
    source "$f"
    echo "PRIMARY_DIR=${PRIMARY_DIR:-EMPTY}"
  else
    echo "PRIMARY_DIR=EMPTY (no $f)"
  fi
}
EOF

sed -i 's/\r$//' "$CFG/helpers.sh"
chmod 644 "$CFG/helpers.sh"
echo "[OK] installed: $CFG/helpers.sh"
