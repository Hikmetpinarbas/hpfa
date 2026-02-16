#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
PROJ="$HOME/HP_PROJELERI"
KEEP_MOTOR="$PROJ/HP-Motor-main"

INV="$HOME/hpfa/_diag/hp_projeleri_inventory.tsv"

TS="$(date +%Y%m%d_%H%M%S)"
ADIR="$HOME/HP_ARCHIVES/_HP_PROJELERI_PRUNE_INV_$TS"
MAN="$ADIR/manifest.tsv"
mkdir -p "$ADIR"

# Safety: default DRY_RUN=1. Apply with: DRY_RUN=0 prune_hp_projeleri_by_inventory.sh
DRY_RUN="${DRY_RUN:-1}"

sha1() { printf "%s" "$1" | sha1sum | awk '{print $1}'; }

mv_guard() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "[FAIL] mv invoked while DRY_RUN=1 (script corruption or misuse)"
    exit 99
  fi
  command mv "$@"
}

plan_move() {
  local p="$1"
  [ -e "$p" ] || return 0
  [ "$p" = "$KEEP_MOTOR" ] && return 0

  local base; base="$(basename "$p")"
  local h; h="$(sha1 "$p")"
  local to="$ADIR/${base}__${h:0:10}"

  local i=0
  local final="$to"
  while [ -e "$final" ]; do
    i=$((i+1))
    final="${to}__${i}"
  done

  if [ "$DRY_RUN" = "1" ]; then
    echo "[PLAN] $p -> $final"
  else
    echo "[MOVE] $p -> $final"
    mv_guard "$p" "$final"
    echo -e "$p\t$final" >> "$MAN"
  fi
}

if [ ! -f "$INV" ]; then
  echo "[FAIL] inventory missing: $INV"
  echo "[HINT] run: python ~/hpfa/tools/hp_projeleri_inventory.py"
  exit 2
fi

echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] INVENTORY=$INV"
echo "[OK] ARCHIVE_DIR=$ADIR"
echo "[OK] KEEP_MOTOR=$KEEP_MOTOR"
echo

if [ "$DRY_RUN" != "1" ]; then
  echo -e "from\tto" > "$MAN"
fi

# TSV: path name kind ... label (last column)
# label=ARCHIVE olan path’leri çek
tail -n +2 "$INV" | awk -F'\t' '$NF=="ARCHIVE"{print $1}' | while IFS= read -r p; do
  # sadece PROJ altındakiler
  case "$p" in
    "$PROJ"/*) plan_move "$p" ;;
    *) ;;
  esac
done

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] To apply: DRY_RUN=0 ~/hpfa/tools/prune_hp_projeleri_by_inventory.sh"
else
  echo "[OK] MANIFEST=$MAN"
  echo "[OK] moved_n=$(( $(wc -l < "$MAN") - 1 ))"
fi
