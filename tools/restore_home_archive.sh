#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: restore_home_archive </path/to/_HP_ARCHIVE_YYYYMMDD_HHMMSS>"
  exit 2
fi

ADIR="$1"
MAN="$ADIR/manifest.tsv"

if [ ! -f "$MAN" ]; then
  echo "[FAIL] manifest not found: $MAN"
  exit 2
fi

tail -n +2 "$MAN" | while IFS=$'\t' read -r from to; do
  [ -n "$from" ] || continue
  if [ -e "$to" ]; then
    mkdir -p "$(dirname "$from")"
    echo "[RESTORE] $to -> $from"
    mv "$to" "$from"
  else
    echo "[SKIP] missing payload: $to"
  fi
done

echo "[OK] restore complete"
