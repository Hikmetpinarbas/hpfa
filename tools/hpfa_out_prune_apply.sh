#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
OUT="$HOME/hpfa/_out"
ARCH_ROOT="$HOME/HP_ARCHIVES/_OUT_ARCHIVE"

KEEP="${KEEP:-5}"          # env ile override edebilirsin: KEEP=8 ...
MODE="${1:-dry}"           # dry | apply

if [ ! -d "$OUT" ]; then
  echo "[FAIL] missing OUT dir: $OUT"
  exit 2
fi

mkdir -p "$ARCH_ROOT"

# engine_run_* dizinlerini mtime'a göre sırala (newest first)
mapfile -t RUNS < <(find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@\t%p\n' | sort -nr | awk -F'\t' '{print $2}')

TOTAL="${#RUNS[@]}"
echo "[OK] OUT=$OUT"
echo "[OK] total_runs=$TOTAL"
echo "[OK] keep=$KEEP"
echo "[OK] mode=$MODE"
echo

if [ "$TOTAL" -le "$KEEP" ]; then
  echo "[OK] nothing to prune (total<=keep)"
  exit 0
fi

# prune list: KEEP'ten sonraki her şey
PRUNE=("${RUNS[@]:$KEEP}")

echo "== KEEP (newest $KEEP) =="
for p in "${RUNS[@]:0:$KEEP}"; do
  echo "  $(basename "$p")"
done
echo

echo "== PRUNE (to archive) =="
for p in "${PRUNE[@]}"; do
  echo "  $(basename "$p")"
done
echo

STAMP="$(date +%Y%m%d_%H%M%S)"
ARCH_DIR="$ARCH_ROOT/OUT_PRUNE_$STAMP"
mkdir -p "$ARCH_DIR"

if [ "$MODE" = "dry" ]; then
  echo "[DRY] would create: $ARCH_DIR"
  echo "[DRY] would tar.gz each PRUNE run into archive and then remove from _out"
  exit 0
fi

if [ "$MODE" != "apply" ]; then
  echo "[FAIL] mode must be: dry | apply"
  exit 3
fi

echo "[OK] archiving into: $ARCH_DIR"
for p in "${PRUNE[@]}"; do
  bn="$(basename "$p")"
  tgz="$ARCH_DIR/${bn}.tar.gz"
  echo "[OK] tar -> $tgz"
  # tar: relative paths inside archive
  tar -C "$OUT" -czf "$tgz" "$bn"

  # verify archive non-empty
  if [ ! -s "$tgz" ]; then
    echo "[FAIL] archive is empty: $tgz"
    exit 9
  fi

  echo "[OK] remove dir: $p"
  rm -rf "$p"
done

echo
echo "[OK] prune complete"
echo "[OK] archived_at=$ARCH_DIR"
echo "[OK] remaining_runs=$(find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' | wc -l | tr -d ' ')"
