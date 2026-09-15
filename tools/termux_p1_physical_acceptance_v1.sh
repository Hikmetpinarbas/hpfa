#!/data/data/com.termux/files/usr/bin/bash
set -u

EXPECTED_SHA="${1:-}"
if [ -z "$EXPECTED_SHA" ]; then
  echo "usage: $0 <expected_product_commit>"
  exit 2
fi

RUNTIME="$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"
DEST="/sdcard/Download/HPFA"
SHORT="${EXPECTED_SHA:0:7}"
LOG="$DEST/HPFA_P1_PHONE_${SHORT}.txt"
ARCHIVE="$DEST/HPFA_P1_PHONE_${SHORT}.tar.gz"
WORK="$HOME/.hpfa_p1_phone_${SHORT}_$$"
SRC=""
CHILD=""
MONITOR=""
START_TS="$(date +%s)"

mkdir -p "$DEST" "$WORK"
: > "$LOG"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"
  sync >/dev/null 2>&1 || true
}

sample() {
  printf '%s SAMPLE ' "$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
  if [ -r /proc/meminfo ]; then
    awk '/MemAvailable|SwapFree/ {printf "%s=%s%s ", $1, $2, $3}' /proc/meminfo >> "$LOG" 2>/dev/null || true
  fi
  if [ -n "$CHILD" ] && [ -r "/proc/$CHILD/status" ]; then
    awk '/VmPeak|VmSize|VmRSS|VmHWM|Threads/ {printf "%s=%s%s ", $1, $2, $3}' "/proc/$CHILD/status" >> "$LOG" 2>/dev/null || true
  fi
  if [ -r /proc/pressure/memory ]; then
    tr '\n' ' ' < /proc/pressure/memory >> "$LOG" 2>/dev/null || true
  fi
  printf '\n' >> "$LOG"
  sync >/dev/null 2>&1 || true
}

cleanup() {
  [ -n "$MONITOR" ] && kill "$MONITOR" >/dev/null 2>&1 || true
  [ -n "$CHILD" ] && kill -0 "$CHILD" >/dev/null 2>&1 && kill "$CHILD" >/dev/null 2>&1 || true
  command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock >/dev/null 2>&1 || true
}
trap cleanup INT TERM

log "HPFA P1 PHYSICAL ACCEPTANCE V1"
log "EXPECTED_SHA=$EXPECTED_SHA"
log "RUNTIME=$RUNTIME"

for d in "$HOME"/hpfa_p1_exact_* "$HOME/hpfa" "$HOME/hpfa_github" "$HOME/hpfa_claim_integrity/hpfa_product" "$HOME/_hpfa-main_upstream" "$HOME/hp/repos/hpfa"; do
  [ -d "$d/.git" ] || continue
  [ -f "$d/visible_action_sequence_candidates_current_v1.py" ] || continue
  HEAD_SHA="$(git -C "$d" rev-parse HEAD 2>/dev/null || true)"
  if [ "$HEAD_SHA" = "$EXPECTED_SHA" ]; then
    SRC="$d"
    break
  fi
done

if [ -z "$SRC" ]; then
  log "FAIL=EXACT_HEAD_CHECKOUT_NOT_FOUND"
  exit 2
fi
if [ ! -d "$RUNTIME" ]; then
  log "FAIL=ACTIVE_MATCH_RUNTIME_MISSING"
  exit 2
fi

log "SRC=$SRC"
log "CHECKPOINT=PRE_SEQUENCE"
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || true

PYTHONUNBUFFERED=1 python -u "$SRC/visible_action_sequence_candidates_current_v1.py" \
  --input-dir "$RUNTIME" \
  --out-dir "$WORK" \
  >> "$LOG" 2>&1 &
CHILD=$!
log "CHILD_PID=$CHILD"

(
  while kill -0 "$CHILD" 2>/dev/null; do
    sample
    sleep 1
  done
) &
MONITOR=$!

wait "$CHILD"
RC=$?
kill "$MONITOR" >/dev/null 2>&1 || true
MONITOR=""
log "CHILD_RETURN_CODE=$RC"

if [ "$RC" -eq 137 ] || [ "$RC" -eq 9 ]; then
  CLASSIFICATION="PROCESS_KILL_CANDIDATE"
elif [ "$RC" -eq 0 ]; then
  CLASSIFICATION="P1_SEQUENCE_COMPLETED"
else
  CLASSIFICATION="P1_SEQUENCE_RETURNED_NONZERO"
fi
log "CLASSIFICATION=$CLASSIFICATION"

MANIFEST="$WORK/HPFA_P1_PHONE_MANIFEST_${SHORT}.txt"
{
  echo "expected_sha=$EXPECTED_SHA"
  echo "source=$SRC"
  echo "runtime=$RUNTIME"
  echo "child_return_code=$RC"
  echo "classification=$CLASSIFICATION"
  echo "canonical_event_count=UNKNOWN"
  echo "true_action_count=UNKNOWN"
  echo "production_release=false"
} > "$MANIFEST"

cp "$LOG" "$WORK/HPFA_P1_PHONE_${SHORT}.txt" 2>/dev/null || true

FILES=(
  "HPFA_P1_PHONE_MANIFEST_${SHORT}.txt"
  "HPFA_P1_PHONE_${SHORT}.txt"
  "action_occurrence_admission_lite_v1.json"
  "trackable_action_trace_candidates_lite_v1.json"
  "trackable_action_consequence_candidates_lite_v1.json"
  "occurrence_consequence_projection_v1.json"
  "visible_action_sequence_candidates_lite_v1.json"
)
PRESENT=()
for name in "${FILES[@]}"; do
  [ -f "$WORK/$name" ] && PRESENT+=("$name")
done

if [ "${#PRESENT[@]}" -gt 0 ]; then
  rm -f "$ARCHIVE"
  tar -czf "$ARCHIVE" -C "$WORK" "${PRESENT[@]}" >> "$LOG" 2>&1 || true
  sync >/dev/null 2>&1 || true
  [ -f "$ARCHIVE" ] && log "ARCHIVE=$ARCHIVE" || log "ARCHIVE=NOT_CREATED"
fi

END_TS="$(date +%s)"
log "ELAPSED_SECONDS=$((END_TS-START_TS))"
rm -rf "$WORK" >/dev/null 2>&1 || true
command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock >/dev/null 2>&1 || true

echo "$ARCHIVE"
exit "$RC"
