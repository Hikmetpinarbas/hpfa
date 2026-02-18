#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HPFA_REPO="${HOME}/hpfa"
OUT_DIR="${HPFA_REPO}/_out"
DIAG_DIR="${HPFA_REPO}/_diag"
LOG="${DIAG_DIR}/validator_last.log"

GUARD="${HPFA_REPO}/tools/hp_engine_artifact_guard_strict_core.py"

if [ ! -f "${GUARD}" ]; then
  echo "[FAIL] guard not found: ${GUARD}" >&2
  exit 2
fi

if [ ! -d "${OUT_DIR}" ]; then
  echo "[FAIL] out dir missing: ${OUT_DIR}" >&2
  exit 2
fi

RUN_DIR="$(find "${OUT_DIR}" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | awk '{print $2}')"

if [ -z "${RUN_DIR}" ] || [ ! -d "${RUN_DIR}" ]; then
  echo "[FAIL] no engine_run_* found under: ${OUT_DIR}" >&2
  exit 3
fi

mkdir -p "${DIAG_DIR}"

{
  echo "HPFA VALIDATOR RUN (strict core)"
  echo "ts=$(date -Iseconds)"
  echo "run_dir=${RUN_DIR}"
  echo "guard=${GUARD}"
  echo "----------------------------------------"
  python "${GUARD}" "${RUN_DIR}" 2>&1
} | tee "${LOG}"

if rg -n "^\[OK\] CORE_ARTIFACTS_MATCH" "${LOG}" >/dev/null 2>&1; then
  echo "[PASS] CORE_ARTIFACTS_MATCH evidence in ${LOG}"
  exit 0
fi

echo "[FAIL] CORE_ARTIFACTS_MATCH not found in ${LOG}" >&2
exit 10
