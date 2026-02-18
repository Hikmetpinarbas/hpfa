#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"
ROOT="$HOME/HP_PLATFORM/06_NORMALIZED/matches"
DIAG="$REPO/_diag"

DOCTOR="$REPO/tools/hpfa-doctor"
SET_PRIMARY="$(command -v hpfa-set-primary || true)"
RUN="$(command -v hpfa-run || true)"
VAL="$REPO/tools/hpfa_validator_run_strict_core.sh"

usage(){
  echo "usage: hpfa_batch_run.sh <limit:int> <glob> <mode:continue|all>"
  echo "example: hpfa_batch_run.sh 5 '*SL*' continue"
}

LIMIT="${1:-}"
GLOB="${2:-}"
MODE="${3:-continue}"

if [ -z "${LIMIT}" ] || [ -z "${GLOB}" ]; then
  usage >&2
  exit 2
fi

mkdir -p "$DIAG"
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$DIAG/batch_${TS}.log"
TSV="$DIAG/batch_${TS}.tsv"

echo "HPFA BATCH RUN" | tee "$LOG"
echo "ts=${TS}" | tee -a "$LOG"
echo "matches_root=${ROOT}" | tee -a "$LOG"
echo "glob=${GLOB} limit=${LIMIT} mode=${MODE}" | tee -a "$LOG"
echo "log=${LOG}" | tee -a "$LOG"
echo "summary=${TSV}" | tee -a "$LOG"
echo "----------------------------------------" | tee -a "$LOG"

# Pre-flight doctor
echo "[STEP] doctor pre-flight" | tee -a "$LOG"
if [ -x "$DOCTOR" ]; then
  if ! "$DOCTOR" >>"$LOG" 2>&1; then
    echo "[FAIL] doctor pre-flight failed" | tee -a "$LOG"
    exit 10
  fi
else
  echo "[FAIL] doctor not found/executable: $DOCTOR" | tee -a "$LOG"
  exit 11
fi
echo "----------------------------------------" | tee -a "$LOG"

# Discover matches (recursive, but only immediate match dirs)
# Rule: match dir = directory under ROOT that contains events_canonical.csv (provider contract input)
# This prevents picking random folders that just match the glob.
mapfile -t MATCHES < <(
  find "$ROOT" -type f -name 'events_canonical.csv' -print 2>/dev/null \
  | sed 's|/events_canonical\.csv$||' \
  | rg -n --pcre2 -e "$(printf '%s' "$GLOB" | sed 's/\*/.*/g' | sed 's/\?/./g')" -o \
  | awk -F: '{print $1}' \
  | sort -u
)

# The rg trick above is brittle; safer fallback if it returns nothing:
if [ "${#MATCHES[@]}" -eq 0 ]; then
  mapfile -t MATCHES < <(
    find "$ROOT" -type d -name "$GLOB" -print 2>/dev/null | sort -u
  )
fi

echo "[INFO] discovered_matches=${#MATCHES[@]}" | tee -a "$LOG"
if [ "${#MATCHES[@]}" -eq 0 ]; then
  echo "[FAIL] no matches found for glob=${GLOB} under ${ROOT}" | tee -a "$LOG"
  exit 12
fi

# Build a set of already-passed matches for continue mode
HIST="$REPO/_diag/doctor_history.tsv"
declare -A PASSED
if [ "$MODE" = "continue" ] && [ -f "$HIST" ]; then
  # Normalize to be safe (if tool exists)
  NORM="$REPO/tools/hpfa_doctor_history_normalize.sh"
  if [ -x "$NORM" ]; then
    "$NORM" >/dev/null 2>&1 || true
  fi

  # Field 5 = doctor (PASS/FAIL/0/--help etc.), field 7 = primary_dir
  # Consider PASS only
  while IFS=$'\t' read -r ts tag rh sh doc fail dir; do
    [ "${doc:-}" = "PASS" ] || continue
    [ -n "${dir:-}" ] || continue
    PASSED["$dir"]=1
  done < "$HIST"
fi

# Summary header
printf "ts\tmatch_dir\trc_run\trc_val\trun_dir\n" > "$TSV"

processed=0
for m in "${MATCHES[@]}"; do
  # continue mode skip
  if [ "$MODE" = "continue" ] && [ "${PASSED[$m]+x}" = "x" ]; then
    echo "[SKIP] already PASS: $m" | tee -a "$LOG"
    continue
  fi

  echo "[MATCH] $m" | tee -a "$LOG"

  # Must set PRIMARY_DIR per match
  if [ -z "$SET_PRIMARY" ]; then
    echo "[FAIL] hpfa-set-primary not found in PATH" | tee -a "$LOG"
    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Iseconds)" "$m" "127" "NA" "NA" >> "$TSV"
    continue
  fi

  if ! hpfa-set-primary "$m" >>"$LOG" 2>&1; then
    echo "[FAIL] set-primary failed: $m" | tee -a "$LOG"
    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Iseconds)" "$m" "20" "NA" "NA" >> "$TSV"
    continue
  fi

  # Run engine
  if [ -z "$RUN" ]; then
    echo "[FAIL] hpfa-run not found in PATH" | tee -a "$LOG"
    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Iseconds)" "$m" "127" "NA" "NA" >> "$TSV"
    continue
  fi

  # Capture last OUT_DIR from run output
  tmp="$(mktemp)"
  rc_run=0
  hpfa-run >"$tmp" 2>&1 || rc_run=$?
  run_dir="$(rg -n '^\[OK\] OUT_DIR=' "$tmp" | tail -n 1 | sed 's/.*OUT_DIR=//')"
  echo "[RUN] rc=${rc_run} run_dir=${run_dir:-NA}" | tee -a "$LOG"

  # Append run log snippet
  rg -n "^\[(OK|WARN|FAIL|INFO)\]" "$tmp" | sed 's/^/[RUN_LOG] /' | tee -a "$LOG" || true

  rm -f "$tmp"

  # Validate strict-core
  rc_val="NA"
  if [ -x "$VAL" ] && [ -n "${run_dir:-}" ] && [ "$run_dir" != "NA" ]; then
    "$VAL" >>"$LOG" 2>&1 || rc_val=$?
    rc_val="${rc_val:-0}"
    echo "[VAL] rc=${rc_val}" | tee -a "$LOG"
  fi

  printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Iseconds)" "$m" "$rc_run" "$rc_val" "${run_dir:-NA}" >> "$TSV"

  if [ "$rc_run" = "0" ] && [ "$rc_val" = "0" ]; then
    echo "[OK] match passed: $m" | tee -a "$LOG"
  else
    echo "[FAIL] match failed: $m (rc_run=$rc_run rc_val=$rc_val)" | tee -a "$LOG"
  fi

  echo "----------------------------------------" | tee -a "$LOG"

  processed=$((processed + 1))
  if [ "$processed" -ge "$LIMIT" ]; then
    break
  fi
done

echo "[DONE] processed=${processed}" | tee -a "$LOG"
echo "[DONE] summary=${TSV}" | tee -a "$LOG"
