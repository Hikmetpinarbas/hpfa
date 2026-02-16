#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
TS="$(date +%Y%m%d_%H%M%S)"
QDIR="$HOME/_QUARANTINE_DUPLICATES_$TS"
MANIFEST="$QDIR/manifest.tsv"
mkdir -p "$QDIR"

HPFA_SSOT="$HOME/HPFA_MASTER/base/hpfa-monorepo"
MOTOR_SSOT="$HOME/HP_PROJELERI/HP-Motor-main"

echo "[OK] QDIR=$QDIR"
echo "[OK] HPFA_SSOT=$HPFA_SSOT"
echo "[OK] MOTOR_SSOT=$MOTOR_SSOT"
echo -e "kind\tfrom\tto\tstatus" > "$MANIFEST"

# Bul: hp_motor klasörleri
mapfile -t MOTOR_DIRS < <(find "$HOME" -type d -name "hp_motor" 2>/dev/null | sort)
# Bul: hpfa klasörleri (paket klasörü)
mapfile -t HPFA_DIRS  < <(find "$HOME" -type d -name "hpfa" 2>/dev/null | sort)

sha1() { printf "%s" "$1" | sha1sum | awk '{print $1}'; }

move_one() {
  local kind="$1"
  local d="$2"

  # varsa taşınır; yoksa temiz skip
  if [ ! -e "$d" ]; then
    echo "[SKIP] (gone/already moved) $d"
    echo -e "${kind}\t${d}\t-\tSKIP_GONE" >> "$MANIFEST"
    return 0
  fi

  # güvenlik: site-packages içini ASLA taşıma
  if [[ "$d" == *"/site-packages/"* ]]; then
    echo "[SKIP] (site-packages) $d"
    echo -e "${kind}\t${d}\t-\tSKIP_SITEPKG" >> "$MANIFEST"
    return 0
  fi

  local h; h="$(sha1 "$d")"
  local base="$QDIR/${kind}__${h}"
  local final="$base"
  local i=0
  while [ -e "$final" ]; do
    i=$((i+1))
    final="${base}__${i}"
  done

  echo "[MOVE] $d -> $final"
  mv "$d" "$final"
  echo -e "${kind}\t${d}\t${final}\tMOVED" >> "$MANIFEST"
}

should_keep_motor() {
  local d="$1"
  [[ "$d" == "$MOTOR_SSOT/src/hp_motor" ]]
}

should_keep_hpfa_pkg() {
  local d="$1"
  [[ "$d" == "$HPFA_SSOT/src/hpfa" ]]
}

echo
echo "== MOTOR (hp_motor) quarantine =="
for d in "${MOTOR_DIRS[@]}"; do
  if should_keep_motor "$d"; then
    echo "[KEEP] $d"
    echo -e "hp_motor\t${d}\t-\tKEEP_SSOT" >> "$MANIFEST"
  else
    move_one "hp_motor" "$d"
  fi
done

echo
echo "== HPFA (hpfa pkg) quarantine =="
for d in "${HPFA_DIRS[@]}"; do
  if should_keep_hpfa_pkg "$d"; then
    echo "[KEEP] $d"
    echo -e "hpfa\t${d}\t-\tKEEP_SSOT" >> "$MANIFEST"
    continue
  fi

  # hpfa çalışma klasörü; asla taşıma
  if [[ "$d" == "$HOME/hpfa" ]]; then
    echo "[KEEP] (workspace) $d"
    echo -e "hpfa\t${d}\t-\tKEEP_WORKSPACE" >> "$MANIFEST"
    continue
  fi

  move_one "hpfa" "$d"
done

echo
echo "[OK] quarantine done."
echo "[OK] manifest: $MANIFEST"
echo
echo "== SUMMARY =="
awk -F'\t' 'NR>1{c[$4]++} END{for(k in c) printf("%s\t%d\n", k, c[k])}' "$MANIFEST" | sort
