#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
PROJ="$HOME/HP_PROJELERI"
KEEP_MOTOR="$PROJ/HP-Motor-main"   # SSOT motor
OUT="$HOME/hpfa/_diag/plan_hp_projeleri_cleanup.tsv"

mkdir -p "$(dirname "$OUT")"

if [ ! -d "$PROJ" ]; then
  echo "[OK] no HP_PROJELERI at: $PROJ"
  exit 0
fi

echo -e "path\tsize_bytes\tmtime\trepo_signal\tkeep_reason" > "$OUT"

# maxdepth 2: üst düzey + bir alt
while IFS= read -r p; do
  [ -e "$p" ] || continue
  base="$(basename "$p")"

  size="$(du -sb "$p" 2>/dev/null | awk '{print $1}' || echo 0)"
  mtime="$(stat -c %y "$p" 2>/dev/null | cut -d'.' -f1 || echo n/a)"

  repo_signal="no"
  if [ -d "$p/.git" ] || [ -f "$p/pyproject.toml" ] || [ -f "$p/setup.py" ] || [ -f "$p/setup.cfg" ]; then
    repo_signal="yes"
  fi

  keep_reason=""
  if [ "$p" = "$KEEP_MOTOR" ]; then
    keep_reason="SSOT_MOTOR"
  fi

  echo -e "$p\t$size\t$mtime\t$repo_signal\t$keep_reason" >> "$OUT"
done < <(find "$PROJ" -maxdepth 2 -mindepth 1 -printf "%p\n" | sort)

echo "[OK] wrote: $OUT"
echo
echo "== TOP 30 by size =="
sort -t$'\t' -k2,2nr "$OUT" | head -n 31
echo
echo "== candidates (not SSOT_MOTOR) =="
awk -F'\t' 'NR>1 && $5=="" {print " - " $1}' "$OUT" | head -n 120
