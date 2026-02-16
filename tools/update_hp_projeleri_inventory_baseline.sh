#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
DIAG="$HOME/hpfa/_diag"

SRC="$DIAG/hp_projeleri_inventory.tsv"
BASE="$DIAG/hp_projeleri_inventory.BASELINE.tsv"
SIG="$DIAG/hp_projeleri_inventory.BASELINE.sig"

if [ ! -f "$SRC" ]; then
  echo "[FAIL] missing inventory: $SRC"
  echo "[HINT] run: python ~/hpfa/tools/hp_projeleri_inventory.py"
  exit 2
fi

sha256f() { sha256sum "$1" | awk '{print $1}'; }

if [ -f "$BASE" ]; then
  SRC_SHA="$(sha256f "$SRC")"
  BASE_SHA="$(sha256f "$BASE")"
  if [ "$SRC_SHA" = "$BASE_SHA" ]; then
    echo "[OK] baseline already up-to-date (noop)"
    echo "[OK] SRC_SHA=$SRC_SHA"
    exit 0
  fi
fi

# unlock (ignore if missing)
chmod 644 "$BASE" "$SIG" 2>/dev/null || true

cp "$SRC" "$BASE"
rm -f "$SIG"

~/hpfa/tools/hp_projeleri_drift_guard.sh

chmod 444 "$BASE" "$SIG"

echo "[OK] inventory baseline updated+locked"
echo "[OK] BASE=$BASE"
echo "[OK] SIG=$SIG"
