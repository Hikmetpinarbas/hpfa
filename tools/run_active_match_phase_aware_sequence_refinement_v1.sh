#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/phase-aware-sequence-refinement-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 2; }

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_missing_or_invalid:${EXPECTED_HEAD:-EMPTY}"
[[ "$ACTUAL_HEAD" == "${EXPECTED_HEAD,,}" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
EXPECTED_RESOLVED="$(cd "$EXPECTED_ACTIVE_MATCH" && pwd -P)"
[[ "$ACTIVE_RESOLVED" == "$EXPECTED_RESOLVED" ]] || fail "active_match_runtime_authority_mismatch"
case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

mkdir -p "$OUT"
cd "$REPO"
rm -f \
  "$OUT/phase_aware_sequence_refinement_lite_v1.json" \
  "$OUT/phase_aware_sequence_refinement_lite_v1.txt" \
  "$OUT/phase_aware_sequence_refinement_analyst_audit_v1.txt" \
  "$OUT/phase_aware_sequence_refinement_runtime_audit_v1.txt" \
  "$OUT/phase_aware_sequence_refinement_result_v1.txt" \
  "$OUT/phase_aware_sequence_refinement_pytest_v1.txt"

python -m py_compile \
  phase_aware_sequence_refinement_lite.py \
  hpfa/modules/core/phase_aware_sequence_refinement_lite/src/phase_aware_sequence_refinement.py
python -m pytest -q \
  hpfa/modules/core/phase_aware_sequence_refinement_lite/tests \
  | tee "$OUT/phase_aware_sequence_refinement_pytest_v1.txt"

set +e
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
  bash "$REPO/tools/run_active_match_event_derived_phase_state_v1.sh"
UPSTREAM_RC="$?"
set -e
[[ "$UPSTREAM_RC" -eq 0 ]] || fail "event_derived_phase_spine_failed:$UPSTREAM_RC"

PHASE_INPUT="$OUT/event_derived_phase_state_lite_v1.json"
[[ -f "$PHASE_INPUT" ]] || fail "event_derived_phase_output_missing"

set +e
python phase_aware_sequence_refinement_lite.py \
  --event-derived-phase "$PHASE_INPUT" \
  --out "$OUT" \
  | tee "$OUT/phase_aware_sequence_refinement_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

OUTPUT="$OUT/phase_aware_sequence_refinement_lite_v1.json"
[[ -f "$OUTPUT" ]] || fail "phase_aware_sequence_refinement_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" "$ACTUAL_HEAD" <<'PY' \
  | tee "$OUT/phase_aware_sequence_refinement_runtime_audit_v1.txt"
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

print("HPFA PHASE-AWARE SEQUENCE REFINEMENT ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "runtime_evidence_status",
    "release_status",
    "runtime_code_head_sha",
    "match_surface_binding_id",
    "source_event_derived_phase_segment_count",
    "source_visible_sequence_count",
    "phase_refinement_decision_count",
    "A_B_A_phase_oscillation_count",
    "refinement_candidate_count",
    "insufficient_anchor_review_count",
    "retained_source_phase_segment_count",
    "automatic_merge_count",
    "automatic_delete_count",
    "hard_block_hits",
    "review_hits",
    "active_match_execution_completed",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
print(f"decision_class_counts={payload.get('decision_class_counts')}")
PY

{
  echo "product_repo=$REPO"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=${EXPECTED_HEAD,,}"
  echo "runtime_authority=$ACTIVE_RESOLVED"
  echo "upstream_rc=$UPSTREAM_RC"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUTPUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/phase_aware_sequence_refinement_result_v1.txt"

exit "$RUN_RC"
