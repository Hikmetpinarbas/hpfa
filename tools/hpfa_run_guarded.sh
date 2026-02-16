#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
OUTROOT="$HOME/hpfa/_out"
VENV_PY="$HOME/hpfa/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "[FAIL] missing venv python: $VENV_PY"
  echo "[HINT] activate venv or recreate: python -m venv ~/hpfa/.venv"
  exit 10
fi

# Guards (pre)
~/hpfa/tools/hp_projeleri_root_guard.sh
"$VENV_PY" ~/hpfa/tools/ssot_guard_strict.py
~/hpfa/tools/hp_projeleri_drift_guard.sh

PRIMARY_DIR="${1:-}"
if [ -z "$PRIMARY_DIR" ]; then
  echo "[FAIL] missing PRIMARY_DIR (arg1)"
  exit 11
fi
shift 1

# Optional: --out OUT_DIR
OUT_DIR=""
if [ "${1:-}" = "--out" ]; then
  OUT_DIR="${2:-}"
  if [ -z "$OUT_DIR" ]; then
    echo "[FAIL] --out requires a value"
    exit 12
  fi
  shift 2
fi

# Default OUT_DIR if not provided
if [ -z "$OUT_DIR" ]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  OUT_DIR="$OUTROOT/engine_run_$TS"
fi

# Avoid collision
if [ -e "$OUT_DIR" ]; then
  i=1
  while [ -e "${OUT_DIR}__${i}" ]; do
    i=$((i+1))
  done
  OUT_DIR="${OUT_DIR}__${i}"
fi

mkdir -p "$OUT_DIR"

echo "[OK] python=$VENV_PY"
echo "[OK] PRIMARY_DIR=$PRIMARY_DIR"
echo "[OK] OUT_DIR=$OUT_DIR"
echo

"$VENV_PY" -m hpfa.cli_engine run "$PRIMARY_DIR" "$OUT_DIR" "$@"

"$VENV_PY" ~/hpfa/tools/hp_engine_artifact_guard_strict_core.py "$OUT_DIR" --strict

echo
echo "[OK] RUN_GUARDED_COMPLETE"
echo "[OK] OUT_DIR=$OUT_DIR"
