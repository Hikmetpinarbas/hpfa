#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
ARCH="${ARCH:-$HOME/HP_ARCHIVES/_HP_ARCHIVE_20260216_114142}"
PACK_ROOT="${PACK_ROOT:-$HOME/HP_ARCHIVES/_PACKED}"
MODE="${1:-dry}"   # dry | apply

mkdir -p "$PACK_ROOT"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="$PACK_ROOT/PACK_${STAMP}"
mkdir -p "$OUTDIR"

echo "[OK] ARCH=$ARCH"
echo "[OK] PACK_ROOT=$PACK_ROOT"
echo "[OK] outdir=$OUTDIR"
echo "[OK] mode=$MODE"
echo

# pack list (top-level heavy hitters, excluding drive_dump.zip__* which is already a single file)
mapfile -t TARGETS < <(
  find "$ARCH" -maxdepth 1 -mindepth 1 -type d \
    \( -name '_HP_GRAVEYARD_*' -o -name '_HP_QUARANTINE_*' -o -name '_QUARANTINE_DUPLICATES_*' \) \
    -printf '%p\n' | sort
)

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "[OK] no graveyard/quarantine dirs found"
  exit 0
fi

echo "== TARGETS =="
for p in "${TARGETS[@]}"; do
  du -sh "$p" | awk '{print "  " $0}'
done
echo

if [ "$MODE" = "dry" ]; then
  echo "[DRY] would create tar.gz + sha256 in: $OUTDIR"
  echo "[DRY] would remove original dirs after successful pack+verify"
  exit 0
fi

if [ "$MODE" != "apply" ]; then
  echo "[FAIL] mode must be dry|apply"
  exit 2
fi

echo "[OK] packing..."
for p in "${TARGETS[@]}"; do
  bn="$(basename "$p")"
  tgz="$OUTDIR/${bn}.tar.gz"

  echo "[OK] tar -> $tgz"
  tar -C "$ARCH" -czf "$tgz" "$bn"

  if [ ! -s "$tgz" ]; then
    echo "[FAIL] tar is empty: $tgz"
    exit 9
  fi

  echo "[OK] sha256 -> ${tgz}.sha256"
  sha256sum "$tgz" > "${tgz}.sha256"

  echo "[OK] remove dir: $p"
  rm -rf "$p"
done

echo
echo "[OK] pack complete"
echo "[OK] packed_at=$OUTDIR"
echo "[OK] remaining_top_level_in_ARCH:"
ls -lah "$ARCH" | head -n 50
