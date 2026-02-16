#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRC="$HOME/.bashrc"
BK="$HOME/.bashrc.BAK_$(date +%Y%m%d_%H%M%S)"

cp -f "$BRC" "$BK"
echo "[OK] backup=$BK"

# markers (literal match, not regex-heavy)
START='^# --- HPFA \(external helpers\) ---$'
ENDMARK='^# --- /HPFA ---$'

# Keep first HPFA block; drop subsequent ones
awk -v START="$START" -v ENDMARK="$ENDMARK" '
  BEGIN {state=0; seen=0}
  $0 ~ START {
    if (seen==0) {seen=1; state=1; print; next}
    state=2; next
  }
  state==2 {
    if ($0 ~ ENDMARK) {state=0}
    next
  }
  $0 ~ ENDMARK {
    if (state==1) {state=0; print; next}
  }
  {print}
' "$BK" > "$BRC"

bash -n "$BRC" && echo "[OK] bashrc lint pass" || { echo "[FAIL] bashrc lint fail"; exit 3; }

echo "[OK] dedupe complete"
echo "[INFO] HPFA block markers now:"
grep -nE '^# --- HPFA \(external helpers\) ---$|^# --- /HPFA ---$' "$BRC" || true
