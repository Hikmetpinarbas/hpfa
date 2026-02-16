#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
TS="$(date +%Y%m%d_%H%M%S)"
ADIR="$HOME/_HP_ARCHIVE_$TS"
LIST="$ADIR/plan.tsv"
mkdir -p "$ADIR"

keep_regex='^(hpfa|HPFA_MASTER|HP_PROJELERI|HP_LIBRARY|HP_PLATFORM|HPFA|HPFA_TRASH|hp_platform|hp_storage|storage|downloads|data|logs|bin|tmp|out|src|tools|.config|.termux|.ssh|.cache|.venv)$'

# Taşınacak adaylar (home kökü)
candidates=()
while IFS= read -r name; do
  base="$(basename "$name")"
  # keep list
  if [[ "$base" =~ $keep_regex ]]; then
    continue
  fi
  # hedef patterns
  if [[ "$base" == _HP_GRAVEYARD_* ]] || [[ "$base" == _HP_QUARANTINE_* ]] || [[ "$base" == _QUARANTINE_DUPLICATES_* ]]; then
    candidates+=("$name")
    continue
  fi
  if [[ "$base" == drive_dump* ]] || [[ "$base" == *snapshot*.zip ]] || [[ "$base" == *dump*.zip ]] || [[ "$base" == HP-Motor-main.zip ]]; then
    candidates+=("$name")
    continue
  fi
  if [[ "$base" == hp_motor_backup_*.tgz ]] || [[ "$base" == hp_motor_cleanup_backup_*.tgz ]]; then
    candidates+=("$name")
    continue
  fi
  if [[ "$base" == HP_LIBRARY_*.zip ]] || [[ "$base" == HP_LIBRARY_*.tar.gz ]] || [[ "$base" == HP_LIBRARY_FINAL_*.zip ]]; then
    candidates+=("$name")
    continue
  fi
done < <(find "$HOME" -maxdepth 1 -mindepth 1 -printf "%p\n" | sort)

echo -e "from\ttype\tsize_bytes\tmtime" > "$LIST"

total=0
for p in "${candidates[@]}"; do
  if [ -e "$p" ]; then
    t="$(stat -c %F "$p" 2>/dev/null || echo "unknown")"
    s="$(stat -c %s "$p" 2>/dev/null || echo 0)"
    m="$(stat -c %y "$p" 2>/dev/null | cut -d'.' -f1 || echo "n/a")"
    echo -e "$p\t$t\t$s\t$m" >> "$LIST"
    total=$((total + s))
  fi
done

echo "[OK] PLAN_DIR=$ADIR"
echo "[OK] PLAN_FILE=$LIST"
echo "[OK] CANDIDATES_N=${#candidates[@]}"
echo "[OK] TOTAL_BYTES=$total"
echo
echo "== TOP 25 by size =="
sort -t$'\t' -k3,3nr "$LIST" | head -n 26
