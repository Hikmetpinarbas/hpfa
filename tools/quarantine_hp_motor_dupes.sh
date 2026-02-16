#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SSOT="${1:?SSOT motor root path required (e.g. ~/hpfa/_ssot/motor)}"
QROOT="${2:?QROOT required}"

SSOT="$(realpath "$SSOT")"
QROOT="$(realpath "$QROOT")"

echo "[INFO] SSOT=$SSOT"
echo "[INFO] QROOT=$QROOT"

# find hp_motor dirs, exclude SSOT subtree + exclude quarantine itself
mapfile -t DIRS < <(find "$HOME" -type d -name "hp_motor" 2>/dev/null \
  | while read -r p; do
      rp="$(realpath "$p" 2>/dev/null || echo "")"
      [ -z "$rp" ] && continue
      [[ "$rp" == "$SSOT"* ]] && continue
      [[ "$rp" == "$QROOT"* ]] && continue
      echo "$rp"
    done | sort -u)

echo "[INFO] candidates: ${#DIRS[@]}"
for d in "${DIRS[@]}"; do
  # Move parent of hp_motor folder, not only leaf, to keep context
  parent="$(dirname "$d")"
  tag="$(echo "$parent" | sed 's|/|__|g')"
  dest="$QROOT/$tag"
  echo "[MOVE] $parent -> $dest"
  mkdir -p "$dest"
  mv "$parent" "$dest/" || true
done

echo "[OK] quarantine complete"
