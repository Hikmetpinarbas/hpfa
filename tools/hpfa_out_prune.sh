#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
OUTROOT="$HOME/hpfa/_out"
ARCHROOT="$HOME/HP_ARCHIVES/_OUT_ARCHIVE"
KEEP_N="${KEEP_N:-12}"          # son N run kalsın (default 12)
MODE="${1:-plan}"               # plan | apply

if [ ! -d "$OUTROOT" ]; then
  echo "[FAIL] missing OUTROOT: $OUTROOT"
  exit 2
fi

if ! [[ "$KEEP_N" =~ ^[0-9]+$ ]] || [ "$KEEP_N" -lt 1 ]; then
  echo "[FAIL] KEEP_N must be positive int. got: $KEEP_N"
  exit 3
fi

mkdir -p "$ARCHROOT"

# list engine_run_* dirs by mtime (newest first)
mapfile -t RUNS < <(find "$OUTROOT" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@\t%p\n' \
  | sort -nr | awk -F'\t' '{print $2}')

TOTAL="${#RUNS[@]}"
echo "[OK] OUTROOT=$OUTROOT"
echo "[OK] TOTAL_RUN_DIRS=$TOTAL"
echo "[OK] KEEP_N=$KEEP_N"
echo "[OK] MODE=$MODE"
echo

if [ "$TOTAL" -le "$KEEP_N" ]; then
  echo "[OK] nothing to prune (TOTAL<=KEEP_N)"
  exit 0
fi

# keep first KEEP_N, move the rest
TO_MOVE=("${RUNS[@]:$KEEP_N}")

STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$ARCHROOT/out_prune_$STAMP"
mkdir -p "$DEST"

echo "== PLAN =="
i=0
for d in "${TO_MOVE[@]}"; do
  bn="$(basename "$d")"
  echo "[MOVE] $bn -> $DEST/$bn"
  i=$((i+1))
  [ "$i" -ge 200 ] && { echo "[WARN] showing first 200 only"; break; }
done
echo "[OK] MOVE_COUNT=${#TO_MOVE[@]}"
echo

if [ "$MODE" = "plan" ]; then
  echo "[OK] plan-only (no changes). To apply:"
  echo "  KEEP_N=$KEEP_N ~/hpfa/tools/hpfa_out_prune.sh apply"
  exit 0
fi

if [ "$MODE" != "apply" ]; then
  echo "[FAIL] usage: hpfa_out_prune.sh [plan|apply]"
  exit 4
fi

echo "== APPLY =="
for d in "${TO_MOVE[@]}"; do
  bn="$(basename "$d")"
  mv -n "$d" "$DEST/$bn"
done

echo "[OK] moved ${#TO_MOVE[@]} run dirs to:"
echo "[OK] $DEST"
