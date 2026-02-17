#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

P="${1:-$HOME/HP_ARCHIVES/_PACKED}"
[ -d "$P" ] || { echo "[FAIL] PACKED dir missing: $P"; exit 2; }

PACKDIR="$(ls -1dt "$P"/PACK_* 2>/dev/null | head -n 1 || true)"
[ -n "$PACKDIR" ] || { echo "[FAIL] no PACK_* under: $P"; exit 3; }

echo "[INFO] packdir=$PACKDIR"

# Strategy:
# - run sha256 checks inside PACKDIR so relative paths resolve
# - if sha256 files contain absolute paths, strip dir prefix on-the-fly and verify via a temp file
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

fail=0
shas=( "$PACKDIR"/*.sha256 )
if [ ! -e "${shas[0]}" ]; then
  echo "[FAIL] no .sha256 files in $PACKDIR"
  exit 4
fi

cd "$PACKDIR"
for f in *.sha256; do
  echo "[INFO] checking $f"
  # Detect absolute paths
  if grep -qE '^[0-9a-f]{64}[[:space:]]+/' "$f"; then
    # Convert absolute path lines to basenames (assumes tar.gz files are in PACKDIR)
    awk '{h=$1; p=$2; gsub(/^.*\//,"",p); print h"  "p}' "$f" > "$tmp"
    sha256sum -c "$tmp" >/dev/null || fail=1
  else
    sha256sum -c "$f" >/dev/null || fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "[FAIL] PACK checksum fail"
  exit 11
fi

echo "[OK] PACK checksum ok"
