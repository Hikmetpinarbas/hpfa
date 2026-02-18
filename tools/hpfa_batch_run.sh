#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"
OUT="$REPO/_out"
DIAG="$REPO/_diag"
MATCHES_ROOT="$HOME/HP_PLATFORM/06_NORMALIZED/matches"

PY="$REPO/.venv/bin/python"
DOCTOR="$REPO/tools/hpfa-doctor"
VAL="$REPO/tools/hpfa_validator_run_strict_core.sh"

# ---- args ----
LIMIT="${1:-0}"          # 0 = no limit
GLOB="${2:-*}"           # match dir glob filter
MODE="${3:-continue}"    # continue | stop
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$DIAG/batch_${TS}.log"
SUMMARY="$DIAG/batch_${TS}.tsv"

mkdir -p "$DIAG" "$OUT"

echo "HPFA BATCH RUN"
echo "ts=$TS"
echo "matches_root=$MATCHES_ROOT"
echo "glob=$GLOB limit=$LIMIT mode=$MODE"
echo "log=$LOG"
echo "summary=$SUMMARY"
echo "----------------------------------------" | tee "$LOG"

if [ ! -d "$MATCHES_ROOT" ]; then
  echo "[FAIL] matches root missing: $MATCHES_ROOT" | tee -a "$LOG" >&2
  exit 2
fi
if [ ! -x "$DOCTOR" ]; then
  echo "[FAIL] doctor missing: $DOCTOR" | tee -a "$LOG" >&2
  exit 2
fi
if [ ! -x "$VAL" ]; then
  echo "[FAIL] validator missing: $VAL" | tee -a "$LOG" >&2
  exit 2
fi

# Pre-flight gate once
echo "[STEP] doctor pre-flight" | tee -a "$LOG"
if ! "$DOCTOR" >>"$LOG" 2>&1; then
  echo "[FAIL] doctor pre-flight failed" | tee -a "$LOG" >&2
  exit 10
fi

# Summary header
printf "ts\tmatch_dir\trc_run\trc_val\trun_dir\n" > "$SUMMARY"

count=0

# Deterministic order
mapfile -t dirs < <(find "$MATCHES_ROOT" -maxdepth 1 -mindepth 1 -type d -name "$GLOB" | sort)

if [ "${#dirs[@]}" -eq 0 ]; then
  echo "[FAIL] no match dirs for glob=$GLOB under $MATCHES_ROOT" | tee -a "$LOG" >&2
  exit 3
fi

for d in "${dirs[@]}"; do
  count=$((count+1))
  if [ "$LIMIT" != "0" ] && [ "$count" -gt "$LIMIT" ]; then
    echo "[STOP] limit reached: $LIMIT" | tee -a "$LOG"
    break
  fi

  echo "----------------------------------------" | tee -a "$LOG"
  echo "[MATCH] $d" | tee -a "$LOG"

  # Set PRIMARY_DIR for this run (without editing user env file)
  export PRIMARY_DIR="$d"

  # Run hpfa-run; capture last run dir from output marker if present
  tmp="$HOME/tmp.batch.$$.$count"
  rc_run=0
  (cd "$REPO" && hpfa-run >"$tmp" 2>&1) || rc_run=$?

  # Try to extract OUT_DIR line; fallback to newest engine_run_*
  run_dir="$(rg -n "^\[OK\] OUT_DIR=" "$tmp" | tail -n 1 | sed 's/.*OUT_DIR=//')"
  if [ -z "${run_dir:-}" ]; then
    run_dir="$(find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | awk '{print $2}')"
  fi

  # Always append run log tail for debugging
  echo "[RUN] rc=$rc_run run_dir=${run_dir:-UNKNOWN}" | tee -a "$LOG"
  tail -n 40 "$tmp" | sed 's/^/[RUN_LOG] /' | tee -a "$LOG" >/dev/null
  rm -f "$tmp" || true

  # Validator (strict core) — uses latest run under _out internally
  rc_val=0
  (cd "$REPO" && "$VAL" >>"$LOG" 2>&1) || rc_val=$?

  echo "[VAL] rc=$rc_val" | tee -a "$LOG"

  printf "%s\t%s\t%s\t%s\t%s\n" \
    "$(date -Iseconds)" "$d" "$rc_run" "$rc_val" "${run_dir:-}" >> "$SUMMARY"

  if [ "$rc_run" != "0" ] || [ "$rc_val" != "0" ]; then
    echo "[FAIL] match failed: $d (run_rc=$rc_run val_rc=$rc_val)" | tee -a "$LOG" >&2
    if [ "$MODE" = "stop" ]; then
      echo "[STOP] mode=stop; exiting on first failure" | tee -a "$LOG" >&2
      exit 20
    fi
  else
    echo "[OK] match passed: $d" | tee -a "$LOG"
  fi
done

echo "----------------------------------------" | tee -a "$LOG"
echo "[DONE] processed=$count" | tee -a "$LOG"
echo "[DONE] summary=$SUMMARY" | tee -a "$LOG"
