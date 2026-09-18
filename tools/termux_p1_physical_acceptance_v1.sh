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

CONTEXT_RC=99
if [ "$SEQUENCE_RC" -eq 0 ]; then
  log "CHECKPOINT=PRE_CURRENT_INVOCATION_CONTEXT_SURFACES"
  python -u "$SRC/active_match_exact_head_run_v1.py" \
    --match-dir "$RUNTIME" \
    --out-dir "$WORK" \
    --expected-product-commit "$EXPECTED_SHA" \
    >> "$LOG" 2>&1
  CONTEXT_RC=$?
  log "CURRENT_INVOCATION_CONTEXT_RETURN_CODE=$CONTEXT_RC"
else
  log "CURRENT_INVOCATION_CONTEXT_SKIPPED=SEQUENCE_NONZERO"
fi

SAFE_RC=99
CLAIM_RC=99
if [ "$SEQUENCE_RC" -eq 0 ] && [ "$CONTEXT_RC" -eq 0 ]; then
  log "CHECKPOINT=VERIFY_SAFE_FINDING_CURRENT_INVOCATION_ARTIFACT"
  python - "$WORK/safe_finding_admission_projection_v1.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(2)
if not isinstance(payload, dict):
    raise SystemExit(2)
if payload.get("status") == "FAIL_CLOSED":
    raise SystemExit(2)
if payload.get("process_context_stale_process_variant_surface_reused") is True:
    raise SystemExit(2)
if payload.get("canonical_event_count") != "UNKNOWN":
    raise SystemExit(2)
if payload.get("true_action_count") != "UNKNOWN":
    raise SystemExit(2)
if payload.get("production_release") is not False:
    raise SystemExit(2)
raise SystemExit(0)
PY
  SAFE_RC=$?
  log "SAFE_FINDING_RETURN_CODE=$SAFE_RC"
else
  log "SAFE_FINDING_SKIPPED=UPSTREAM_SEQUENCE_OR_CONTEXT_NONZERO"
fi

if [ "$SEQUENCE_RC" -eq 0 ] && [ "$CONTEXT_RC" -eq 0 ] && [ "$SAFE_RC" -eq 0 ]; then
  log "CHECKPOINT=VERIFY_CLAIM_SATISFIABILITY_CURRENT_INVOCATION_ARTIFACT"
  python - "$WORK/analyst_output_claim_contract_projection_v1.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(2)
if not isinstance(payload, dict):
    raise SystemExit(2)
if payload.get("status") == "FAIL_CLOSED":
    raise SystemExit(2)
if payload.get("safe_finding_admission_consumed") is not True:
    raise SystemExit(2)
if payload.get("canonical_event_count") != "UNKNOWN":
    raise SystemExit(2)
if payload.get("true_action_count") != "UNKNOWN":
    raise SystemExit(2)
if payload.get("production_release") is not False:
    raise SystemExit(2)
raise SystemExit(0)
PY
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
    ("resolved_divergence_count", value("resolved_divergence_count")),
    ("bounded_occurrence_ancestor_count", value("bounded_occurrence_ancestor_count")),
    ("divergence_occurrence_ancestry_edge_count", value("divergence_occurrence_ancestry_edge_count")),
    ("reused_occurrence_ancestry_edge_count", value("reused_occurrence_ancestry_edge_count")),
    ("reused_occurrence_ancestry_edge_denominator", value("reused_occurrence_ancestry_edge_denominator")),
    ("provenance_multiplicity_state", value("provenance_multiplicity_state")),
    ("structural_multiplicity_equals_provenance_multiplicity", value("structural_multiplicity_equals_provenance_multiplicity", False)),
    ("structural_multiplicity_is_independent_support", value("structural_multiplicity_is_independent_support", False)),
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


RATE_BOUND_SUMMARY="$WORK/HPFA_RATE_BOUND_PHYSICAL_SUMMARY_${SHORT}.txt"
python - "$WORK/safe_finding_admission_projection_v1.json" "$RATE_BOUND_SUMMARY" <<'PY'
import json
import sys
from collections import Counter
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

decisions = [
    row for row in (payload.get("safe_finding_admission_decisions") or [])
    if isinstance(row, dict)
]
states = Counter()
numeric_bound_count = 0
claim_ceiling_counts = Counter()
unsafe_flags = Counter()
for row in decisions:
    profile = row.get("consequence_observation_burden_profile")
    if not isinstance(profile, dict):
        states["BOUND_PROFILE_MISSING"] += 1
        continue
    state = str(profile.get("bound_state") or "BOUND_STATE_MISSING")
    states[state] += 1
    if isinstance(profile.get("lower_bound"), (int, float)) and isinstance(profile.get("upper_bound"), (int, float)):
        numeric_bound_count += 1
    claim_ceiling_counts[str(profile.get("claim_ceiling") or "CLAIM_CEILING_MISSING")] += 1
    if profile.get("identification_interval_is_confidence_interval") is not False:
        unsafe_flags["identification_interval_is_confidence_interval_not_false"] += 1
    if profile.get("rate_bound_can_authorize_emit") is not False:
        unsafe_flags["rate_bound_can_authorize_emit_not_false"] += 1
    if profile.get("rate_bound_can_strengthen_claim_ceiling") is not False:
        unsafe_flags["rate_bound_can_strengthen_claim_ceiling_not_false"] += 1
    if profile.get("rate_bound_creates_new_evidence") is not False:
        unsafe_flags["rate_bound_creates_new_evidence_not_false"] += 1
    if profile.get("rate_bound_is_true_probability") is not False:
        unsafe_flags["rate_bound_is_true_probability_not_false"] += 1
    if profile.get("rate_bound_is_population_rate") is not False:
        unsafe_flags["rate_bound_is_population_rate_not_false"] += 1
    if profile.get("rate_bound_is_causal_effect") is not False:
        unsafe_flags["rate_bound_is_causal_effect_not_false"] += 1

rows = [
    ("partial_identification_rate_bound_consumed", payload.get("partial_identification_rate_bound_consumed", False)),
    ("safe_finding_admission_decision_count", len(decisions)),
    ("bound_profile_state_counts", json.dumps(dict(sorted(states.items())), sort_keys=True)),
    ("numeric_bound_count", numeric_bound_count),
    ("point_identified_count", states.get("POINT_IDENTIFIED_OBSERVED_RATE", 0)),
    ("partially_identified_count", states.get("PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE", 0)),
    ("bound_unresolved_count", states.get("BOUND_UNRESOLVED", 0)),
    ("no_opportunity_count", states.get("NO_OPPORTUNITY", 0)),
    ("not_applicable_count", states.get("NOT_APPLICABLE_NO_MATCHED_PROCESS_VARIANT_LINEAGE", 0)),
    ("bound_claim_ceiling_counts", json.dumps(dict(sorted(claim_ceiling_counts.items())), sort_keys=True)),
    ("unsafe_rate_bound_flag_counts", json.dumps(dict(sorted(unsafe_flags.items())), sort_keys=True)),
    ("partial_identification_rate_bound_can_authorize_emit", payload.get("partial_identification_rate_bound_can_authorize_emit", False)),
    ("partial_identification_rate_bound_can_strengthen_claim_ceiling", payload.get("partial_identification_rate_bound_can_strengthen_claim_ceiling", False)),
    ("partial_identification_rate_bound_is_confidence_interval", payload.get("partial_identification_rate_bound_is_confidence_interval", False)),
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

if [ -f "$RATE_BOUND_SUMMARY" ]; then
  while IFS= read -r line; do
    log "RATE_BOUND_$line"
  done < "$RATE_BOUND_SUMMARY"
else
  log "RATE_BOUND_SUMMARY=NOT_CREATED"
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
  echo "current_invocation_context_return_code=$CONTEXT_RC"
  echo "safe_finding_return_code=$SAFE_RC"
  echo "claim_satisfiability_return_code=$CLAIM_RC"
  echo "final_return_code=$FINAL_RC"
  echo "classification=$CLASSIFICATION"
  [ -f "$LINEAGE_SUMMARY" ] && cat "$LINEAGE_SUMMARY"
  [ -f "$RATE_BOUND_SUMMARY" ] && cat "$RATE_BOUND_SUMMARY"
  echo "canonical_event_count=UNKNOWN"
  echo "true_action_count=UNKNOWN"
  echo "production_release=false"
} > "$MANIFEST"

cp "$LOG" "$WORK/HPFA_P1_PHONE_${SHORT}.txt" 2>/dev/null || true

FILES=(
  "HPFA_P1_PHONE_MANIFEST_${SHORT}.txt"
  "HPFA_P1_PHONE_${SHORT}.txt"
  "HPFA_LINEAGE_PHYSICAL_SUMMARY_${SHORT}.txt"
  "HPFA_RATE_BOUND_PHYSICAL_SUMMARY_${SHORT}.txt"
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
