#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
PROJ="$HOME/HP_PROJELERI"
KEEP_MOTOR="$PROJ/HP-Motor-main"

TS="$(date +%Y%m%d_%H%M%S)"
ADIR="$HOME/HP_ARCHIVES/_HP_PROJELERI_PRUNE_$TS"
MAN="$ADIR/manifest.tsv"
mkdir -p "$ADIR"

# Safety: default DRY_RUN=1. Apply with: DRY_RUN=0 prune_hp_projeleri_unused.sh
DRY_RUN="${DRY_RUN:-1}"

# only these are eligible per strict audit output
UNUSED_DIRS=(
  "$PROJ/_UNKNOWN"
  "$PROJ/apps"
  "$PROJ/football_metrics_system"
  "$PROJ/hp_engine_contracts"
  "$PROJ/hp_engine_core"
  "$PROJ/hp_engine_origin_bundle"
  "$PROJ/hp_engine_playbook"
  "$PROJ/hp_engine_scaffold"
  "$PROJ/hp_engine_v0_2"
)

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

echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] ARCHIVE_DIR=$ADIR"
echo "[OK] KEEP_MOTOR=$KEEP_MOTOR"
echo

if [ ! -d "$PROJ" ]; then
  echo "[OK] missing PROJ dir: $PROJ"
  exit 0
fi

if [ "$DRY_RUN" != "1" ]; then
  echo -e "from\tto" > "$MAN"
fi

for d in "${UNUSED_DIRS[@]}"; do
  plan_move "$d"
done

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] To apply: DRY_RUN=0 ~/hpfa/tools/prune_hp_projeleri_unused.sh"
else
  echo "[OK] MANIFEST=$MAN"
  echo "[OK] moved_n=$(( $(wc -l < "$MAN") - 1 ))"
fi
