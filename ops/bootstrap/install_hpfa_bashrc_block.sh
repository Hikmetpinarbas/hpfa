#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRC="$HOME/.bashrc"
BK="$HOME/.bashrc.BAK_$(date +%Y%m%d_%H%M%S)"
cp -f "$BRC" "$BK"
echo "[OK] backup=$BK"

BLOCK_START="# --- HPFA (external helpers) ---"
BLOCK_END="# --- /HPFA ---"

# remove any existing block (between markers)
awk -v S="$BLOCK_START" -v E="$BLOCK_END" '
  BEGIN{drop=0}
  $0==S {drop=1; next}
  $0==E {drop=0; next}
  drop==0 {print}
' "$BK" > "$BRC"

# append canonical block
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
echo "[OK] installed bashrc block"
