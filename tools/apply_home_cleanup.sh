#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
TS="$(date +%Y%m%d_%H%M%S)"
ADIR="$HOME/HP_ARCHIVES/_HP_ARCHIVE_$TS"
MAN="$ADIR/manifest.tsv"
mkdir -p "$ADIR"

# Safety: default DRY_RUN=1. To actually move, run: DRY_RUN=0 apply_home_cleanup.sh
DRY_RUN="${DRY_RUN:-1}"

keep_regex='^(hpfa|HPFA_MASTER|HP_PROJELERI|HP_LIBRARY|HP_PLATFORM|HPFA|HPFA_TRASH|hp_platform|hp_storage|storage|downloads|data|logs|bin|tmp|out|src|tools|HP_ARCHIVES|.config|.termux|.ssh|.cache|.venv)$'

candidates=()
while IFS= read -r p; do
  base="$(basename "$p")"

  # keep list
  if [[ "$base" =~ $keep_regex ]]; then
    continue
  fi

  # patterns
  if [[ "$base" == _HP_GRAVEYARD_* ]] || [[ "$base" == _HP_QUARANTINE_* ]] || [[ "$base" == _QUARANTINE_DUPLICATES_* ]] \
     || [[ "$base" == drive_dump* ]] || [[ "$base" == *snapshot*.zip ]] || [[ "$base" == *dump*.zip ]] || [[ "$base" == HP-Motor-main.zip ]] \
     || [[ "$base" == hp_motor_backup_*.tgz ]] || [[ "$base" == hp_motor_cleanup_backup_*.tgz ]] \
     || [[ "$base" == HP_LIBRARY_*.zip ]] || [[ "$base" == HP_LIBRARY_*.tar.gz ]] || [[ "$base" == HP_LIBRARY_FINAL_*.zip ]]; then
    candidates+=("$p")
  fi
done < <(find "$HOME" -maxdepth 1 -mindepth 1 -printf "%p\n" | sort)

echo -e "from\tto" > "$MAN"

sha1() { printf "%s" "$1" | sha1sum | awk '{print $1}'; }

moved=0
echo "[OK] DRY_RUN=$DRY_RUN"
echo "[OK] ARCHIVE_DIR=$ADIR"
echo "[OK] candidates_n=${#candidates[@]}"
echo

for p in "${candidates[@]}"; do
  [ -e "$p" ] || continue

  base="$(basename "$p")"
  h="$(sha1 "$p")"
  to="$ADIR/${base}__${h:0:10}"

  i=0
  final="$to"
  while [ -e "$final" ]; do
    i=$((i+1))
    final="${to}__${i}"
  done

  if [ "$DRY_RUN" = "1" ]; then
    echo "[PLAN] $p -> $final"
  else
    echo "[MOVE] $p -> $final"
    mv "$p" "$final"
    echo -e "$p\t$final" >> "$MAN"
    moved=$((moved+1))
  fi
done

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "[OK] DRY_RUN completed. No files moved."
  echo "[OK] If you want to apply, run: DRY_RUN=0 ~/hpfa/tools/apply_home_cleanup.sh"
else
  echo "[OK] MANIFEST=$MAN"
  echo "[OK] moved_n=$moved"
fi
