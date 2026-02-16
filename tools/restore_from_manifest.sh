#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MAN="${1:-}"
if [ -z "$MAN" ] || [ ! -f "$MAN" ]; then
  echo "[FAIL] usage: restore_from_manifest.sh /path/to/manifest.tsv"
  exit 2
fi

# Safety: default DRY_RUN=1. Apply with: DRY_RUN=0 restore_from_manifest.sh manifest.tsv
DRY_RUN="${DRY_RUN:-1}"

echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] MANIFEST=$MAN"
echo

tail -n +2 "$MAN" | while IFS=$'\t' read -r from to; do
  [ -e "$to" ] || { echo "[SKIP] missing archived: $to"; continue; }
  if [ "$DRY_RUN" = "1" ]; then
    echo "[PLAN] $to -> $from"
  else
    echo "[MOVE] $to -> $from"
    mkdir -p "$(dirname "$from")"
    mv "$to" "$from"
  fi
done

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] To apply: DRY_RUN=0 ~/hpfa/tools/restore_from_manifest.sh $MAN"
else
  echo "[OK] restore complete"
fi
