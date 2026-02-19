#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"

usage(){
  echo "usage: hpfa_batch_run.sh <limit:int> <glob> <mode:continue|all>"
  echo "env:"
  echo "  HPFA_MATCHES_ROOT=/abs/path/to/matches   (default: \$HOME/HP_PLATFORM/06_NORMALIZED/matches)"
  echo "example:"
  echo "  HPFA_MATCHES_ROOT=\$HOME/HP_PLATFORM/05_STAGING/matches hpfa_batch_run.sh 5 '*SL*' continue"
}

LIMIT="${1:-}"
GLOB="${2:-}"
MODE="${3:-continue}"
if [ -z "${LIMIT}" ] || [ -z "${GLOB}" ]; then usage; exit 2; fi
if [ "$MODE" != "continue" ] && [ "$MODE" != "all" ]; then usage; exit 2; fi

# IMPORTANT: allow override
MATCHES_ROOT_DEFAULT="$HOME/HP_PLATFORM/06_NORMALIZED/matches"
MATCHES_ROOT="${HPFA_MATCHES_ROOT:-$MATCHES_ROOT_DEFAULT}"

ts="$(date +%Y%m%d_%H%M%S)"
LOG="$REPO/_diag/batch_${ts}.log"
SUMMARY="$REPO/_diag/batch_${ts}.tsv"
mkdir -p "$REPO/_diag"

echo "HPFA BATCH RUN" | tee "$LOG"
echo "ts=${ts}" | tee -a "$LOG"
echo "matches_root=${MATCHES_ROOT}" | tee -a "$LOG"
echo "glob=${GLOB} limit=${LIMIT} mode=${MODE}" | tee -a "$LOG"
echo "log=${LOG}" | tee -a "$LOG"
echo "summary=${SUMMARY}" | tee -a "$LOG"
echo "----------------------------------------" | tee -a "$LOG"

echo -e "ts\tmatch_dir\trun_dir\trc_run\trc_val\tstatus\tmode" > "$SUMMARY"

echo "[STEP] doctor pre-flight" | tee -a "$LOG"
"$REPO/tools/hpfa-doctor" >>"$LOG" 2>&1 || { echo "[FAIL] doctor pre-flight failed" | tee -a "$LOG"; exit 1; }
echo "----------------------------------------" | tee -a "$LOG"

mapfile -t matches < <(find "$MATCHES_ROOT" -mindepth 1 -maxdepth 1 -type d -name "$GLOB" 2>/dev/null | sort | head -n "$LIMIT" || true)
echo "[INFO] discovered_matches=${#matches[@]}" | tee -a "$LOG"

# Build passed set for continue mode
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

  run_dir=""
  rc_run=0
  if out="$(hpfa-run 2>&1)"; then
    rc_run=0
  else
    rc_run=$?
  fi
  echo "$out" | sed -n '1,200p' | sed 's/^/[RUN_LOG] /' | tee -a "$LOG" >/dev/null
  run_dir="$(echo "$out" | awk -F= '/OUT_DIR=/{print $2}' | tail -n1 | tr -d ' ' || true)"
  echo "[RUN] rc=${rc_run} run_dir=${run_dir:-NA}" | tee -a "$LOG"

  rc_val=1
  if [ -n "${run_dir:-}" ] && [ -d "$run_dir" ]; then
    if "$REPO/tools/hpfa_validator_run_strict_core.sh" "$run_dir" >>"$LOG" 2>&1; then
      rc_val=0
    else
      rc_val=$?
    fi
  else
    echo "[FAIL] run_dir missing/invalid" | tee -a "$LOG"
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
