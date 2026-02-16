#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MAN="${1:-}"
if [ -z "$MAN" ] || [ ! -f "$MAN" ]; then
  echo "[FAIL] usage: reapply_manifest_moves.sh /path/to/manifest.tsv"
  exit 2
fi

DRY_RUN="${DRY_RUN:-1}"

echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] MANIFEST=$MAN"
echo

# header'ı geç
tail -n +2 "$MAN" | while IFS=$'\t' read -r FROM TO; do
  [ -n "${FROM:-}" ] || continue
  [ -n "${TO:-}" ] || continue

  if [ ! -e "$FROM" ]; then
    echo "[SKIP] missing FROM: $FROM"
    continue
  fi

  mkdir -p "$(dirname "$TO")"

  if [ "$DRY_RUN" = "1" ]; then
    echo "[PLAN] $FROM -> $TO"
  else
    echo "[MOVE] $FROM -> $TO"
    mv "$FROM" "$TO"
  fi
done

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] To apply: DRY_RUN=0 ~/hpfa/tools/reapply_manifest_moves.sh $MAN"
else
  echo "[OK] reapply complete"
fi
