#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

usage(){
  echo "usage: hpfa_batch_run.sh <limit:int> <glob> <mode:continue|all>"
  echo "env:"
  echo "  HPFA_MATCHES_ROOT=/abs/path/to/matches   (default: \$HOME/HP_PLATFORM/06_NORMALIZED/matches)"
  echo "  HPFA_SKIP_DOCTOR=1                      (skip doctor pre-flight)"
  echo "  HPFA_DOCTOR_SMOKE=0|1                   (default: 0 for batch stability)"
  echo "  HPFA_DOCTOR_STRICT_GIT=0|1              (default: 0 for batch stability)"
  echo "example:"
  echo "  HPFA_MATCHES_ROOT=\$HOME/HP_PLATFORM/05_STAGING/matches hpfa_batch_run.sh 5 '*SL*' continue"
}

LIMIT="${1:-}"
GLOB="${2:-}"
MODE="${3:-continue}"
if [ -z "${LIMIT}" ] || [ -z "${GLOB}" ]; then usage; exit 2; fi
if [ "$MODE" != "continue" ] && [ "$MODE" != "all" ]; then usage; exit 2; fi

HOME="${HOME:-/data/data/com.termux/files/home}"
REPO="${REPO:-$HOME/hpfa}"

cd "$REPO" 2>/dev/null || { echo "[FATAL] cannot cd REPO=$REPO"; exit 2; }

ts="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPO/_diag"

LOG="${LOG:-$REPO/_diag/batch_${ts}.log}"
SUMMARY="${SUMMARY:-$REPO/_diag/batch_${ts}.tsv}"

trap 'rc=$?; echo "[TRAP] rc=$rc line=$LINENO cmd=$BASH_COMMAND" | tee -a "$LOG" >/dev/null; exit $rc' ERR

MATCHES_ROOT_DEFAULT="$HOME/HP_PLATFORM/06_NORMALIZED/matches"
MATCHES_ROOT="${HPFA_MATCHES_ROOT:-$MATCHES_ROOT_DEFAULT}"

echo "HPFA BATCH RUN" | tee "$LOG"
echo "ts=${ts}" | tee -a "$LOG"
echo "matches_root=${MATCHES_ROOT}" | tee -a "$LOG"
echo "glob=${GLOB} limit=${LIMIT} mode=${MODE}" | tee -a "$LOG"
echo "log=${LOG}" | tee -a "$LOG"
echo "summary=${SUMMARY}" | tee -a "$LOG"
echo "----------------------------------------" | tee -a "$LOG"

echo -e "ts\tmatch_dir\trun_dir\trc_run\trc_val\tstatus\tmode" > "$SUMMARY"

echo "[STEP] doctor pre-flight" | tee -a "$LOG"
if [ "${HPFA_SKIP_DOCTOR:-0}" = "1" ]; then
  echo "[SKIP] doctor pre-flight disabled (HPFA_SKIP_DOCTOR=1)" | tee -a "$LOG"
else
  HPFA_DOCTOR_SMOKE="${HPFA_DOCTOR_SMOKE:-0}" \
  HPFA_DOCTOR_STRICT_GIT="${HPFA_DOCTOR_STRICT_GIT:-0}" \
  "$REPO/tools/hpfa-doctor" >>"$LOG" 2>&1 || { echo "[FAIL] doctor pre-flight failed" | tee -a "$LOG"; exit 1; }
fi
echo "----------------------------------------" | tee -a "$LOG"

mapfile -t matches < <(find "$MATCHES_ROOT" -mindepth 1 -maxdepth 1 -type d -name "$GLOB" 2>/dev/null | sort | head -n "$LIMIT" || true)
echo "[INFO] discovered_matches=${#matches[@]}" | tee -a "$LOG"

declare -A PASSED=()
HIST="$REPO/_diag/doctor_history.tsv"
if [ "$MODE" = "continue" ] && [ -f "$HIST" ]; then
  NORM="$REPO/tools/hpfa_doctor_history_normalize.sh"
  [ -x "$NORM" ] && "$NORM" >/dev/null 2>&1 || true
  while IFS=$'\t' read -r ts_h head_h doc_h pack_h _ignore_ dir_h; do
    [ "${doc_h:-}" = "PASS" ] || continue
    [ -n "${dir_h:-}" ] || continue
    PASSED["$dir_h"]=1
  done < "$HIST"
fi

processed=0

for m in "${matches[@]}"; do
  echo "----------------------------------------" | tee -a "$LOG"
  echo "[MATCH] $m" | tee -a "$LOG"

  if [ "$MODE" = "continue" ] && [ "${PASSED[$m]+x}" = "x" ]; then
    echo "[SKIP] already PASS: $m" | tee -a "$LOG"
    continue
  fi

  if ! hpfa-set-primary "$m" >>"$LOG" 2>&1; then
    echo "[FAIL] set-primary failed: $m" | tee -a "$LOG"
    continue
  fi

  out=""
  rc_run=0
  run_dir=""

  set +e
  out="$(hpfa-run 2>&1)"
  rc_run=$?
  set -e

  echo "$out" | sed -n '1,220p' | sed 's/^/[RUN_LOG] /' | tee -a "$LOG" >/dev/null
  run_dir="$(printf '%s\n' "$out" | awk -F= '/OUT_DIR=/{print $2}' | tail -n1 | tr -d ' ' || true)"
  echo "[RUN] rc=${rc_run} run_dir=${run_dir:-NA}" | tee -a "$LOG"

  rc_val=99
  if [ "$rc_run" != "0" ]; then
    echo "[SKIP] validator: hpfa-run failed (rc_run=$rc_run)" | tee -a "$LOG"
    rc_val=99
  elif [ -z "${run_dir:-}" ] || [ ! -d "$run_dir" ]; then
    echo "[FAIL] validator: run_dir missing/invalid" | tee -a "$LOG"
    rc_val=98
  else
    if "$REPO/tools/hpfa_validator_run_strict_core.sh" "$run_dir" >>"$LOG" 2>&1; then
      rc_val=0
    else
      rc_val=$?
    fi
  fi
  echo "[VAL] rc=${rc_val}" | tee -a "$LOG"

  status="FAIL"
  if [ "$rc_run" = "0" ] && [ "$rc_val" = "0" ]; then
    status="PASS"
    echo "[OK] match passed: $m" | tee -a "$LOG"
  else
    echo "[FAIL] match failed: $m" | tee -a "$LOG"
  fi

  echo -e "${ts}\t${m}\t${run_dir:-}\t${rc_run}\t${rc_val}\t${status}\t${MODE}" >> "$SUMMARY"
  processed=$((processed + 1))
done

echo "----------------------------------------" | tee -a "$LOG"
echo "[DONE] processed=${processed}" | tee -a "$LOG"
echo "[DONE] summary=${SUMMARY}" | tee -a "$LOG"
