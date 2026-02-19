#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

termux-wake-lock >/dev/null 2>&1 || true

HOME="${HOME:-/data/data/com.termux/files/home}"
REPO="${REPO:-$HOME/hpfa}"

cd "$REPO" 2>/dev/null || { echo "[FATAL] cannot cd REPO=$REPO"; exit 2; }

ts="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPO/_diag"
LOG="${LOG:-$REPO/_diag/_manual_doctor_gate_${ts}.log}"

echo "[STEP] doctor pre-flight" | tee -a "$LOG"

if [ "${HPFA_SKIP_DOCTOR:-0}" = "1" ]; then
  echo "[SKIP] doctor pre-flight disabled (HPFA_SKIP_DOCTOR=1)" | tee -a "$LOG"
  exit 0
fi

HPFA_DOCTOR_SMOKE="${HPFA_DOCTOR_SMOKE:-0}" \
HPFA_DOCTOR_STRICT_GIT="${HPFA_DOCTOR_STRICT_GIT:-0}" \
"$REPO/tools/hpfa-doctor" >>"$LOG" 2>&1

rc=$?
if [ "$rc" -ne 0 ]; then
  echo "[FAIL] doctor pre-flight failed (rc=$rc). log=$LOG" | tee -a "$LOG"
  exit 1
fi

echo "[OK] doctor pre-flight PASS. log=$LOG" | tee -a "$LOG"
