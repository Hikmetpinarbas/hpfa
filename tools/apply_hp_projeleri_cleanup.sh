#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
PROJ="$HOME/HP_PROJELERI"
KEEP_MOTOR="$PROJ/HP-Motor-main"

TS="$(date +%Y%m%d_%H%M%S)"
ADIR="$HOME/HP_ARCHIVES/_HP_PROJELERI_ARCHIVE_$TS"
MAN="$ADIR/manifest.tsv"
mkdir -p "$ADIR"

# Safety: default DRY_RUN=1. Apply with: DRY_RUN=0 apply_hp_projeleri_cleanup.sh
DRY_RUN="${DRY_RUN:-1}"

MOVE_DIRS=(
  "$PROJ/HP_LIBRARY"
  "$PROJ/_ZIP_EXPLODED"
  "$PROJ/_ACTIVE"
  "$PROJ/_CANDIDATES"
  "$PROJ/sources"
  "$PROJ/Kitaplar makaleler"
)

FILE_GLOB_REGEX='\.(docx|pdf|xlsx|xls|csv|xml|json|mht|mp4|mp3|zip|tgz|tar\.gz|yaml|yml|md|txt)$'

sha1() { printf "%s" "$1" | sha1sum | awk '{print $1}'; }

# DRY_RUN guard: DRY_RUN=1 iken mv çağrılırsa hard fail.
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
  # SSOT motor asla
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

echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] ARCHIVE_DIR=$ADIR"
echo "[OK] KEEP_MOTOR=$KEEP_MOTOR"
echo

if [ "$DRY_RUN" != "1" ]; then
  echo -e "from\tto" > "$MAN"
fi

# 1) hedef klasörler
for d in "${MOVE_DIRS[@]}"; do
  plan_move "$d"
done

# 2) PROJ kökündeki tekil dosyalar (motor repo dışı)
while IFS= read -r f; do
  plan_move "$f"
done < <(find "$PROJ" -maxdepth 1 -type f 2>/dev/null | grep -E -i "$FILE_GLOB_REGEX" || true)

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] To apply: DRY_RUN=0 ~/hpfa/tools/apply_hp_projeleri_cleanup.sh"
else
  echo "[OK] MANIFEST=$MAN"
  echo "[OK] moved_n=$(( $(wc -l < "$MAN") - 1 ))"
fi
