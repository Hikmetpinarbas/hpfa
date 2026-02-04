#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# venv (varsa)
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$PWD/tools${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/5] reports pipeline"
python tools/run_reports_pipeline.py

echo "[2/5] summaries"
python tools/make_summaries.py
python tools/make_goal_timing_profiles.py
python tools/make_manifest.py

echo "[3/5] export"
# hp_export bashrc fonksiyonu değilse fallback: manuel export
TS="$(date +%Y%m%d_%H%M%S)"
SRC="artifacts/reports/normalized"
OUT="out/exports/$TS"
mkdir -p "$OUT"

need=(
  "$SRC/standings__normalized.csv"
  "$SRC/goal_timing__normalized.csv"
  "$SRC/passes_players_split__normalized.csv"
)

for f in "${need[@]}"; do
  [ -f "$f" ] || { echo "[ERR] missing: $f"; exit 2; }
done

cp -f "${need[@]}" "$OUT/"

# optional normalized
[ -f "$SRC/passes_aggregate__normalized.csv" ] && cp -f "$SRC/passes_aggregate__normalized.csv" "$OUT/"
[ -f "$SRC/passes_clean__normalized.csv" ] && cp -f "$SRC/passes_clean__normalized.csv" "$OUT/"
[ -f "$SRC/tables_catalog.txt" ] && cp -f "$SRC/tables_catalog.txt" "$OUT/"

# summaries + manifest
[ -d out/summaries ] && cp -f out/summaries/*.csv out/summaries/*.json "$OUT/" 2>/dev/null || true

# zip
mkdir -p out/exports
( cd out/exports && zip -r "$TS.zip" "$TS" >/dev/null )

echo "[4/5] copy zip to Downloads"
LATEST_ZIP="out/exports/$TS.zip"
mkdir -p ~/storage/downloads
cp -f "$LATEST_ZIP" ~/storage/downloads/

echo "[OK] zip -> $LATEST_ZIP"
echo "[OK] copied -> ~/storage/downloads/$(basename "$LATEST_ZIP")"
echo "[OK] contents:"
zipinfo -1 "$LATEST_ZIP" | sed -n '1,200p'

ZIP_LIST="$(zipinfo -1 "$LATEST_ZIP")"
TOPDIR="$(printf "%s\n" "$ZIP_LIST" | head -n 1 | sed 's:/$::')"
if [ -z "$TOPDIR" ]; then echo "[ERR] cannot detect zip topdir"; exit 90; fi


echo "[5/5] verify zip contents"
REQUIRED=()
while IFS= read -r line; do
  [[ "$line" =~ ^#|^$ ]] && continue
  REQUIRED+=("$line")
done < "tools/release_requirements.txt"

missing=0
for req in "${REQUIRED[@]}"; do
  if ! zipinfo -1 "$LATEST_ZIP" | grep -qx "$TOPDIR/$req"; then
    echo "[ERR] missing in zip: $req"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "[ERR] zip verification failed"
  exit 9
fi
echo "[OK] zip verification passed"


echo "[5/5] verify"
need_in_zip=(
  "standings__normalized.csv"
  "goal_timing__normalized.csv"
  "passes_players_split__normalized.csv"
  "goal_timing_team_profile.csv"
  "passes_players_top_attempted.csv"
  "passes_players_top_pct_min50.csv"
  "passes_team_summary.csv"
  "manifest.json"
)

missing=0
for f in "${need_in_zip[@]}"; do
  if ! zipinfo -1 "$LATEST_ZIP" | grep -qE "/${f}$"; then
    echo "[ERR] missing in zip: $f"
    missing=1
  fi
done

# manifest sanity: schema_version + commit alanları
if unzip -p "$LATEST_ZIP" "*/manifest.json" 2>/dev/null | grep -q '"schema_version"'    && unzip -p "$LATEST_ZIP" "*/manifest.json" 2>/dev/null | grep -q '"commit"'; then
  echo "[OK] manifest sanity"
else
  echo "[ERR] manifest sanity failed"
  missing=1
fi

if [ "$missing" -ne 0 ]; then
  echo "[FAIL] verify failed"
  exit 10
fi

echo "[OK] verify passed"

