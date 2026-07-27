#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/visible-action-sequence-candidate-admission-lite-v1}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin() {
  local origin="${1:-}"
  origin="${origin%/}"
  origin="${origin%.git}"
  origin="${origin#https://github.com/}"
  origin="${origin#http://github.com/}"
  origin="${origin#git@github.com:}"
  origin="${origin#ssh://git@github.com/}"
  printf '%s\n' "${origin,,}"
}

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_missing_or_invalid:${EXPECTED_HEAD:-EMPTY}"
EXPECTED_HEAD="${EXPECTED_HEAD,,}"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
EXPECTED_RESOLVED="$(cd "$EXPECTED_ACTIVE_MATCH" && pwd -P)"
[[ "$ACTIVE_RESOLVED" == "$EXPECTED_RESOLVED" ]] || fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED expected:$EXPECTED_RESOLVED"
case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

mkdir -p "$OUT"
cd "$REPO"
rm -f \
  "$OUT/visible_action_sequence_candidate_admission_lite_v1.json" \
  "$OUT/visible_action_sequence_candidate_admission_lite_v1.txt" \
  "$OUT/visible_action_sequence_candidate_admission_analyst_audit_v1.txt" \
  "$OUT/visible_action_sequence_candidate_admission_runtime_audit_v1.txt" \
  "$OUT/visible_action_sequence_candidate_admission_result_v1.txt"

python -m py_compile \
  visible_action_sequence_candidate_admission_lite.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/common.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/time_layers.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/sequence_admission.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/sequence_engine.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/sequence_record.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/sequence_profiles.py \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/src/visible_action_sequence_candidate_admission.py
python -m pytest -q \
  hpfa/modules/core/visible_action_sequence_candidate_admission_lite/tests \
  | tee "$OUT/visible_action_sequence_candidate_admission_pytest_v1.txt"

set +e
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
  bash "$REPO/tools/run_active_match_selected_event_consequence_surface_v1.sh"
UPSTREAM_RC="$?"
set -e
[[ "$UPSTREAM_RC" -eq 0 ]] || fail "selected_event_consequence_spine_failed:$UPSTREAM_RC"

ACTION_INPUT="$OUT/selected_action_consequence_surface_lite_v1.json"
EVENT_INPUT="$OUT/selected_event_consequence_surface_lite_v1.json"
[[ -f "$ACTION_INPUT" ]] || fail "selected_action_consequence_output_missing"
[[ -f "$EVENT_INPUT" ]] || fail "selected_event_consequence_output_missing"

set +e
python visible_action_sequence_candidate_admission_lite.py \
  --selected-action-consequence "$ACTION_INPUT" \
  --selected-event-consequence "$EVENT_INPUT" \
  --out "$OUT" \
  | tee "$OUT/visible_action_sequence_candidate_admission_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

OUTPUT="$OUT/visible_action_sequence_candidate_admission_lite_v1.json"
[[ -f "$OUTPUT" ]] || fail "visible_action_sequence_candidate_admission_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" "$ACTUAL_HEAD" <<'PY' \
  | tee "$OUT/visible_action_sequence_candidate_admission_runtime_audit_v1.txt"
import json
import sys

path, actual_authority, expected_authority, run_rc_text, runtime_head = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    payload = json.load(handle)
run_rc = int(run_rc_text)
authority_equal = actual_authority == expected_authority
hard_blocks = payload.get("hard_block_hits") or []
module_status = payload.get("module_status") or payload.get("status")
execution_completed = run_rc == 0 and authority_equal and not hard_blocks
active_match_evidence_pass = execution_completed and module_status == "PASS"
payload["runtime_authority"] = actual_authority
payload["runtime_authority_equal"] = authority_equal
payload["runtime_code_head_sha"] = runtime_head
payload["run_rc"] = run_rc
payload["active_match_execution_completed"] = execution_completed
payload["active_match_evidence_pass"] = active_match_evidence_pass
payload["runtime_evidence_status"] = (
    "ACTIVE_MATCH_EVIDENCE_PASS"
    if active_match_evidence_pass
    else (
        "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
        if execution_completed
        else "ACTIVE_MATCH_EXECUTION_NOT_COMPLETED"
    )
)
payload["release_status"] = "NOT_PRODUCTION"
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

print("HPFA VISIBLE ACTION SEQUENCE CANDIDATE ADMISSION ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "module_status",
    "runtime_evidence_status",
    "release_status",
    "runtime_code_head_sha",
    "match_surface_binding_id",
    "source_selected_action_node_count",
    "visible_action_time_layer_candidate_count",
    "primary_sequence_eligible_node_count",
    "team_context_support_node_count",
    "visible_action_sequence_candidate_count",
    "sequence_context_review_required_count",
    "visible_sequence_boundary_candidate_count",
    "review_or_context_only_time_layer_count",
    "node_assignment_count",
    "cross_team_context_support_review_count",
    "team_action_family_visible_sequence_profile_count",
    "actor_action_family_visible_sequence_profile_count",
    "hard_block_hits",
    "review_hits",
    "active_match_execution_completed",
    "active_match_evidence_pass",
    "event_instance_count",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
print(f"time_layer_state_counts={payload.get('time_layer_state_counts')}")
print(f"sequence_admission_status_counts={payload.get('sequence_admission_status_counts')}")
print(f"sequence_start_reason_candidate_counts={payload.get('sequence_start_reason_candidate_counts')}")
print(f"sequence_end_reason_candidate_counts={payload.get('sequence_end_reason_candidate_counts')}")
print(f"trace_signal_candidate_counts={payload.get('trace_signal_candidate_counts')}")
print(f"sequence_zone_span_candidate_counts={payload.get('sequence_zone_span_candidate_counts')}")
print(f"sequence_consequence_composition_candidate_counts={payload.get('sequence_consequence_composition_candidate_counts')}")
print(f"node_assignment_type_counts={payload.get('node_assignment_type_counts')}")
PY

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_RESOLVED"
  echo "upstream_rc=$UPSTREAM_RC"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUTPUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/visible_action_sequence_candidate_admission_result_v1.txt"

exit "$RUN_RC"
