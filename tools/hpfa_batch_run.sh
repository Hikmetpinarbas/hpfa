#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"
ROOT="$HOME/HP_PLATFORM/06_NORMALIZED/matches"
DIAG="$REPO/_diag"

LIMIT="${1:-}"
GLOB="${2:-}"
MODE="${3:-continue}"

if [ -z "${LIMIT}" ] || [ -z "${GLOB}" ]; then
  echo "usage: hpfa_batch_run.sh <limit:int> <glob> <mode:continue|all>" >&2
  echo "example: hpfa_batch_run.sh 5 '*SL*' continue" >&2
  exit 2
fi

mkdir -p "$DIAG"

TS="$(date +%Y%m%d_%H%M%S)"
LOG="$DIAG/batch_${TS}.log"
SUMMARY="$DIAG/batch_${TS}.tsv"

echo "HPFA BATCH RUN" | tee "$LOG"
echo "ts=${TS}" | tee -a "$LOG"
echo "matches_root=${ROOT}" | tee -a "$LOG"
echo "glob=${GLOB} limit=${LIMIT} mode=${MODE}" | tee -a "$LOG"
echo "log=${LOG}" | tee -a "$LOG"
echo "summary=${SUMMARY}" | tee -a "$LOG"
echo "----------------------------------------" | tee -a "$LOG"

canon_path() { realpath -m "$1" 2>/dev/null || printf "%s" "$1"; }

echo "[STEP] doctor pre-flight" | tee -a "$LOG"
"$REPO/tools/hpfa-doctor" >>"$LOG" 2>&1 || { echo "[FAIL] doctor pre-flight failed" | tee -a "$LOG"; exit 10; }
echo "----------------------------------------" | tee -a "$LOG"

declare -A PASSED=()
HIST="$REPO/_diag/doctor_history.tsv"
if [ "$MODE" = "continue" ] && [ -f "$HIST" ]; then
  NORM="$REPO/tools/hpfa_doctor_history_normalize.sh"
  if [ -x "$NORM" ]; then "$NORM" >/dev/null 2>&1 || true; fi

  while IFS=$'\t' read -r ts tag rh sh doc fail dir; do
    [ "${doc:-}" = "PASS" ] || continue
    [ "${fail:-1}" = "0" ] || continue
    [ -n "${dir:-}" ] || continue
    PASSED["$(canon_path "$dir")"]=1
  done < "$HIST"
fi

# ---- FIX: discover matches as ARRAY (never store the count as the list)
mapfile -t MATCHES < <(find "$ROOT" -maxdepth 1 -mindepth 1 -type d -name "$GLOB" | sort)
echo "[INFO] discovered_matches=${#MATCHES[@]}" | tee -a "$LOG"

printf "ts\tmatch_dir\trun_dir\trc_run\trc_val\tstatus\n" > "$SUMMARY"

processed=0

for m in "${MATCHES[@]}"; do
  [ "$processed" -lt "$LIMIT" ] || break

  m_canon="$(canon_path "$m")"

  if [ "$MODE" = "continue" ] && [ "${PASSED[$m_canon]+x}" = "x" ]; then
    echo "[SKIP] already PASS: $m_canon" | tee -a "$LOG"
    printf "%s\t%s\t\t\t\tSKIP_ALREADY_PASS\n" "$(date -Iseconds)" "$m_canon" >> "$SUMMARY"
    continue
  fi

  echo "----------------------------------------" | tee -a "$LOG"
  echo "[MATCH] $m_canon" | tee -a "$LOG"

  if ! hpfa-set-primary "$m_canon" >>"$LOG" 2>&1; then
    echo "[FAIL] set-primary failed: $m_canon" | tee -a "$LOG"
    printf "%s\t%s\t\t1\t\tFAIL_SET_PRIMARY\n" "$(date -Iseconds)" "$m_canon" >> "$SUMMARY"
    continue
  fi

  run_tmp="$(mktemp)"
  rc_run=0
  hpfa-run >"$run_tmp" 2>&1 || rc_run=$?

  run_dir="$(rg -n '^\[OK\] OUT_DIR=' "$run_tmp" | tail -n1 | sed -E 's/.*OUT_DIR=//')"
  echo "[RUN] rc=$rc_run run_dir=${run_dir:-}" | tee -a "$LOG"
  tail -n 80 "$run_tmp" | sed 's/^/[RUN_LOG] /' | tee -a "$LOG"
  rm -f "$run_tmp"

  if [ "$rc_run" != "0" ] || [ -z "${run_dir:-}" ] || [ ! -d "$run_dir" ]; then
    printf "%s\t%s\t%s\t%s\t\tFAIL_RUN\n" "$(date -Iseconds)" "$m_canon" "${run_dir:-}" "$rc_run" >> "$SUMMARY"
    continue
  fi

  rc_val=0
  "$REPO/tools/hpfa_validator_run_strict_core.sh" >>"$LOG" 2>&1 || rc_val=$?
  echo "[VAL] rc=$rc_val" | tee -a "$LOG"

  if [ "$rc_val" = "0" ]; then
    echo "[OK] match passed: $m_canon" | tee -a "$LOG"
    printf "%s\t%s\t%s\t%s\t%s\tPASS\n" "$(date -Iseconds)" "$m_canon" "$run_dir" "$rc_run" "$rc_val" >> "$SUMMARY"
    processed=$((processed + 1))
  else
    echo "[FAIL] match validator failed: $m_canon" | tee -a "$LOG"
    printf "%s\t%s\t%s\t%s\t%s\tFAIL_VALIDATOR\n" "$(date -Iseconds)" "$m_canon" "$run_dir" "$rc_run" "$rc_val" >> "$SUMMARY"
  fi
done

echo "----------------------------------------" | tee -a "$LOG"
echo "[DONE] processed=$processed" | tee -a "$LOG"
echo "[DONE] summary=$SUMMARY" | tee -a "$LOG"
