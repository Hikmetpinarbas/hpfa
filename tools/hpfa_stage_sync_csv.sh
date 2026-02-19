#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MID="${1:-}"
[ -n "$MID" ] || { echo "usage: hpfa_stage_sync_csv.sh <match_id_dirname>"; exit 2; }

HOME="/data/data/com.termux/files/home"
ST="$HOME/HP_PLATFORM/05_STAGING/matches/$MID"
NZ="$HOME/HP_PLATFORM/06_NORMALIZED/matches/$MID"

for f in events_canonical.csv comparison_tidy.csv xlsx_inventory.csv; do
  [ -f "$NZ/$f" ] || { echo "[FAIL] missing: $NZ/$f"; exit 1; }
done
mkdir -p "$ST"

cp -f "$NZ/events_canonical.csv"  "$ST/"
cp -f "$NZ/comparison_tidy.csv"   "$ST/"
cp -f "$NZ/xlsx_inventory.csv"    "$ST/"

echo "[OK] synced CSVs: $NZ -> $ST"
