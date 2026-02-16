#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRC="$HOME/.bashrc"
BK="$HOME/.bashrc.BAK_$(date +%Y%m%d_%H%M%S)"
cp -f "$BRC" "$BK"
echo "[OK] backup=$BK"

SRC='[ -f "$HOME/.config/hpfa/helpers.sh" ] && source "$HOME/.config/hpfa/helpers.sh"'

# 1) Remove all existing occurrences of SRC line
# 2) Append a single canonical block at EOF
# 3) Keep file bash -n clean

grep -vF "$SRC" "$BK" > "$BRC"

cat >> "$BRC" <<'EOF'

# --- HPFA (external helpers) ---
case $- in
  *i*) ;;
  *) return 0 ;;
esac
[ -f "$HOME/.config/hpfa/helpers.sh" ] && source "$HOME/.config/hpfa/helpers.sh"
# --- /HPFA ---
EOF

bash -n "$BRC" && echo "[OK] bashrc lint pass" || { echo "[FAIL] bashrc lint fail"; exit 3; }
echo "[OK] injected single HPFA block"
echo "[INFO] occurrences:"
grep -nF "$SRC" "$BRC" || true
