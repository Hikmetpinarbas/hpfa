#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
ARCHROOT="$HOME/HP_ARCHIVES/_HP_CLEANUP_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHROOT"

ALLOW_HPFA="$HOME/HPFA_MASTER/base/hpfa-monorepo/src/hpfa"
ALLOW_HPM="$HOME/HP_PROJELERI/HP-Motor-main/src/hp_motor"

APPLY=0
if [ "${1:-}" = "--apply" ]; then
  APPLY=1
  shift || true
fi

is_archived() {
  case "$1" in
    "$HOME/HP_ARCHIVES/"*) return 0 ;;
    *) return 1 ;;
  esac
}

should_move_hpfa() {
  local d="$1"
  [ "$d" = "$ALLOW_HPFA" ] && return 1
  is_archived "$d" && return 1

  case "$d" in
    *HP_ARCHIVES*|*QUARANTINE*|*GRAVEYARD*|*QUARANTINED*) return 0 ;;
    *hpfa_work__QUARANTINED*|*hpfa_unified*|*hpfa-main*) return 0 ;;
    # Intentionally DO NOT move monorepo internal components
    *HPFA_MASTER/base/hpfa-monorepo/external/*) return 1 ;;
    *HPFA_MASTER/base/hpfa-monorepo/resources/*) return 1 ;;
    *HPFA_MASTER/base/hpfa-monorepo/src/hpfa) return 1 ;;
    *) return 1 ;;
  esac
}

should_move_hpm() {
  local d="$1"
  [ "$d" = "$ALLOW_HPM" ] && return 1
  is_archived "$d" && return 1

  case "$d" in
    *HP_ARCHIVES*|*QUARANTINE*|*GRAVEYARD*|*QUARANTINED*) return 0 ;;
    */vendor/*/hp_motor) return 0 ;;
    *hp_motor__QUARANTINED*) return 0 ;;
    *) return 1 ;;
  esac
}

plan_move() {
  local src="$1"
  local tag="$2"
  # stable-ish target name
  local base
  base="$(echo "$src" | sed 's#^'"$HOME"'/#HOME__#; s#/#__#g')"
  echo "$ARCHROOT/${tag}__${base}"
}

echo "[OK] ARCHROOT=$ARCHROOT"
echo "[OK] APPLY=$APPLY"
echo

moves=0

echo "== PLAN: hpfa candidates =="
find "$HOME" -type d -name hpfa 2>/dev/null | while read -r d; do
  if should_move_hpfa "$d"; then
    tgt="$(plan_move "$d" "hpfa")"
    echo "[MOVE] $d"
    echo "       -> $tgt"
  fi
done

echo
echo "== PLAN: hp_motor candidates =="
find "$HOME" -type d -name hp_motor 2>/dev/null | while read -r d; do
  if should_move_hpm "$d"; then
    tgt="$(plan_move "$d" "hp_motor")"
    echo "[MOVE] $d"
    echo "       -> $tgt"
  fi
done

if [ "$APPLY" -eq 0 ]; then
  echo
  echo "[OK] PLAN_ONLY (noop). Re-run with --apply to move."
  exit 0
fi

echo
echo "== APPLY MOVES =="
# Apply hpfa
find "$HOME" -type d -name hpfa 2>/dev/null | while read -r d; do
  if should_move_hpfa "$d"; then
    tgt="$(plan_move "$d" "hpfa")"
    mkdir -p "$(dirname "$tgt")"
    mv "$d" "$tgt"
    echo "[OK] moved hpfa: $d -> $tgt"
  fi
done

# Apply hp_motor
find "$HOME" -type d -name hp_motor 2>/dev/null | while read -r d; do
  if should_move_hpm "$d"; then
    tgt="$(plan_move "$d" "hp_motor")"
    mkdir -p "$(dirname "$tgt")"
    mv "$d" "$tgt"
    echo "[OK] moved hp_motor: $d -> $tgt"
  fi
done

echo
echo "[OK] CLEANUP_APPLIED"
echo "[OK] ARCHROOT=$ARCHROOT"
