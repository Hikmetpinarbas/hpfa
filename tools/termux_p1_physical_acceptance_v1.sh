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
SEQUENCE_RC=$?
kill "$MONITOR" >/dev/null 2>&1 || true
MONITOR=""
CHILD=""
log "SEQUENCE_RETURN_CODE=$SEQUENCE_RC"

SAFE_RC=99
CLAIM_RC=99
if [ "$SEQUENCE_RC" -eq 0 ]; then
  log "CHECKPOINT=PRE_SAFE_FINDING_ADMISSION"
  python -u "$SRC/safe_finding_admission_current_v1.py" \
    --sequence-json "$WORK/visible_action_sequence_candidates_lite_v1.json" \
    --out-dir "$WORK" \
    >> "$LOG" 2>&1
  SAFE_RC=$?
  log "SAFE_FINDING_RETURN_CODE=$SAFE_RC"
else
  log "SAFE_FINDING_SKIPPED=SEQUENCE_NONZERO"
fi

if [ "$SEQUENCE_RC" -eq 0 ] && [ "$SAFE_RC" -eq 0 ]; then
  log "CHECKPOINT=PRE_CLAIM_SATISFIABILITY"
  python -u "$SRC/analyst_output_claim_admission_current_v1.py" \
    --sequence-json "$WORK/visible_action_sequence_candidates_lite_v1.json" \
    --admission-json "$WORK/safe_finding_admission_projection_v1.json" \
    --out-dir "$WORK" \
    >> "$LOG" 2>&1
  CLAIM_RC=$?
  log "CLAIM_SATISFIABILITY_RETURN_CODE=$CLAIM_RC"
else
  log "CLAIM_SATISFIABILITY_SKIPPED=UPSTREAM_NONZERO"
fi

LINEAGE_SUMMARY="$WORK/HPFA_LINEAGE_PHYSICAL_SUMMARY_${SHORT}.txt"
python - "$WORK/analyst_output_claim_contract_projection_v1.json" "$LINEAGE_SUMMARY" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
payload = {}
if source.is_file():
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            payload = value
    except (OSError, json.JSONDecodeError):
        payload = {}

summary = payload.get("derived_lineage_runtime_binding_summary")
if not isinstance(summary, dict):
    summary = payload.get("derived_lineage_runtime_binding")
if not isinstance(summary, dict):
    summary = {}

def value(key, default="UNKNOWN"):
    current = summary.get(key, default)
    if isinstance(current, bool):
        return "true" if current else "false"
    return str(current)

rows = [
    ("derived_lineage_runtime_binding_consumed", payload.get("derived_lineage_runtime_binding_consumed", False)),
    ("derived_lineage_runtime_binding_status", payload.get("derived_lineage_runtime_binding_status", "NOT_EVALUATED")),
    ("bounded_occurrence_ancestor_count", value("bounded_occurrence_ancestor_count")),
    ("shared_occurrence_ancestor_count", value("shared_occurrence_ancestor_count")),
    ("divergence_with_shared_ancestor_count", value("divergence_with_shared_ancestor_count")),
    ("divergence_without_shared_ancestor_within_tracked_scope_count", value("divergence_without_shared_ancestor_within_tracked_scope_count")),
    ("unresolved_divergence_ancestry_count", value("unresolved_divergence_ancestry_count")),
    ("bounded_ancestry_distinctness_is_independence_proof", value("bounded_ancestry_distinctness_is_independence_proof", False)),
    ("shared_ancestor_can_add_independent_support", value("shared_ancestor_can_add_independent_support", False)),
    ("lineage_can_increase_existing_independent_support", value("lineage_can_increase_existing_independent_support", False)),
    ("lineage_can_authorize_emit", value("lineage_can_authorize_emit", False)),
    ("lineage_can_strengthen_claim_ceiling", value("lineage_can_strengthen_claim_ceiling", False)),
    ("lineage_creates_new_evidence", value("lineage_creates_new_evidence", False)),
    ("canonical_event_count", payload.get("canonical_event_count", "UNKNOWN")),
    ("true_action_count", payload.get("true_action_count", "UNKNOWN")),
    ("production_release", payload.get("production_release", False)),
]
with target.open("w", encoding="utf-8") as handle:
    for key, current in rows:
        if isinstance(current, bool):
            current = "true" if current else "false"
        handle.write(f"{key}={current}\n")
PY

if [ -f "$LINEAGE_SUMMARY" ]; then
  while IFS= read -r line; do
    log "LINEAGE_$line"
  done < "$LINEAGE_SUMMARY"
else
  log "LINEAGE_SUMMARY=NOT_CREATED"
fi

if [ "$SEQUENCE_RC" -eq 137 ] || [ "$SEQUENCE_RC" -eq 9 ]; then
  CLASSIFICATION="PROCESS_KILL_CANDIDATE"
  FINAL_RC="$SEQUENCE_RC"
elif [ "$SEQUENCE_RC" -ne 0 ]; then
  CLASSIFICATION="P1_SEQUENCE_RETURNED_NONZERO"
  FINAL_RC="$SEQUENCE_RC"
elif [ "$SAFE_RC" -ne 0 ]; then
  CLASSIFICATION="SAFE_FINDING_ADMISSION_RETURNED_NONZERO"
  FINAL_RC="$SAFE_RC"
elif [ "$CLAIM_RC" -ne 0 ]; then
  CLASSIFICATION="CLAIM_SATISFIABILITY_RETURNED_NONZERO"
  FINAL_RC="$CLAIM_RC"
else
  CLASSIFICATION="P1_SEQUENCE_SAFE_FINDING_CLAIM_COMPLETED"
  FINAL_RC=0
fi
log "CLASSIFICATION=$CLASSIFICATION"

MANIFEST="$WORK/HPFA_P1_PHONE_MANIFEST_${SHORT}.txt"
{
  echo "expected_sha=$EXPECTED_SHA"
  echo "source=$SRC"
  echo "runtime=$RUNTIME"
  echo "sequence_return_code=$SEQUENCE_RC"
  echo "safe_finding_return_code=$SAFE_RC"
  echo "claim_satisfiability_return_code=$CLAIM_RC"
  echo "final_return_code=$FINAL_RC"
  echo "classification=$CLASSIFICATION"
  [ -f "$LINEAGE_SUMMARY" ] && cat "$LINEAGE_SUMMARY"
  echo "canonical_event_count=UNKNOWN"
  echo "true_action_count=UNKNOWN"
  echo "production_release=false"
} > "$MANIFEST"

cp "$LOG" "$WORK/HPFA_P1_PHONE_${SHORT}.txt" 2>/dev/null || true

FILES=(
  "HPFA_P1_PHONE_MANIFEST_${SHORT}.txt"
  "HPFA_P1_PHONE_${SHORT}.txt"
  "HPFA_LINEAGE_PHYSICAL_SUMMARY_${SHORT}.txt"
  "action_occurrence_admission_lite_v1.json"
  "trackable_action_trace_candidates_lite_v1.json"
  "trackable_action_consequence_candidates_lite_v1.json"
  "occurrence_consequence_projection_v1.json"
  "occurrence_state_transition_projection_v1.json"
  "visible_action_sequence_candidates_lite_v1.json"
  "safe_finding_admission_projection_v1.json"
  "puzzle_finding_contract_projection_v1.json"
  "analyst_output_claim_contract_projection_v1.json"
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
exit "$FINAL_RC"
