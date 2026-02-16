#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
CUR="$HOME/hpfa/_diag/hp_projeleri_inventory.tsv"
BASE="$HOME/hpfa/_diag/hp_projeleri_inventory.BASELINE.sig"

python ~/hpfa/tools/hp_projeleri_inventory.py >/dev/null

# signature: ignore size/mtime, keep structural signals
sig() {
  awk -F'\t' 'NR==1{next}{print $1"\t"$3"\t"$6"\t"$NF}' "$CUR" \
    | sort \
    | sha1sum \
    | awk '{print $1}'
}

CURSIG="$(sig)"

if [ ! -f "$BASE" ]; then
  printf "%s\n" "$CURSIG" > "$BASE"
  echo "[OK] baseline signature created: $BASE"
  exit 0
fi

BASESIG="$(cat "$BASE" | tr -d '\r\n')"
if [ "$CURSIG" != "$BASESIG" ]; then
  echo "[FAIL] HP_PROJELERI inventory drift detected (signature mismatch)."
  echo "[HINT] show diff (path kind repo label):"
  tmp1="$(mktemp)"; tmp2="$(mktemp)"
  awk -F'\t' 'NR==1{next}{print $1"\t"$3"\t"$6"\t"$NF}' "$HOME/hpfa/_diag/hp_projeleri_inventory.tsv" | sort > "$tmp2"
  # reconstruct baseline view is not possible from sig alone; show current view only
  echo "[INFO] current snapshot (first 80 lines):"
  sed -n '1,80p' "$tmp2"
  rm -f "$tmp1" "$tmp2"
  exit 42
fi

echo "[OK] inventory drift: none"
