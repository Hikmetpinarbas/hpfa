#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"

# Allowed "active" roots (only these should be used at runtime)
ALLOW_HPFA="$HOME/HPFA_MASTER/base/hpfa-monorepo/src/hpfa"
ALLOW_HPM="$HOME/HP_PROJELERI/HP-Motor-main/src/hp_motor"

echo "[OK] HOME=$HOME"
echo "[OK] allow_hpfa=$ALLOW_HPFA"
echo "[OK] allow_hp_motor=$ALLOW_HPM"
echo

echo "== hpfa dirs (all) =="
find "$HOME" -type d -name hpfa 2>/dev/null | sed 's#^#[HPFA] #'

echo
echo "== hp_motor dirs (all) =="
find "$HOME" -type d -name hp_motor 2>/dev/null | sed 's#^#[HPM ] #'

echo
echo "== suspicious hpfa dirs (outside allow) =="
find "$HOME" -type d -name hpfa 2>/dev/null | while read -r d; do
  if [ "$d" != "$ALLOW_HPFA" ] && [ "${d#"$HOME/HP_ARCHIVES/"}" = "$d" ]; then
    # not the allowed one, and not under HP_ARCHIVES
    echo "[SUS_HPFA] $d"
  fi
done

echo
echo "== suspicious hp_motor dirs (outside allow) =="
find "$HOME" -type d -name hp_motor 2>/dev/null | while read -r d; do
  if [ "$d" != "$ALLOW_HPM" ] && [ "${d#"$HOME/HP_ARCHIVES/"}" = "$d" ]; then
    echo "[SUS_HPM ] $d"
  fi
done

echo
echo "[OK] DUP_SCAN_COMPLETE"
