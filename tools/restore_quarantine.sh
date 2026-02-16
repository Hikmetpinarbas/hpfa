#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: restore_quarantine </path/to/_QUARANTINE_DUPLICATES_...>"
  exit 2
fi

QDIR="$1"
MANIFEST="$QDIR/manifest.tsv"

if [ ! -f "$MANIFEST" ]; then
  echo "[FAIL] manifest not found: $MANIFEST"
  exit 2
fi

# header skip
tail -n +2 "$MANIFEST" | while IFS=$'\t' read -r kind from to; do
  if [ -e "$to" ]; then
    mkdir -p "$(dirname "$from")"
    echo "[RESTORE] $to -> $from"
    mv "$to" "$from"
  else
    echo "[SKIP] missing payload: $to"
  fi
done

echo "[OK] restore complete"
