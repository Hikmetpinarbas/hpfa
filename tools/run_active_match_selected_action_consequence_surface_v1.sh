#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/selected-action-consequence-surface-lite-v1}"
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
  "$OUT/selected_action_consequence_surface_lite_v1.json" \
  "$OUT/selected_action_consequence_surface_lite_v1.txt" \
  "$OUT/selected_action_consequence_surface_analyst_audit_v1.txt" \
  "$OUT/selected_action_consequence_surface_runtime_audit_v1.txt" \
  "$OUT/selected_action_consequence_surface_result_v1.txt"

python -m py_compile \
  selected_action_consequence_surface_lite.py \
  hpfa/modules/core/selected_action_consequence_surface_lite/src/selected_action_consequence_surface.py \
  hpfa/modules/core/selected_action_consequence_surface_lite/src/field_semantics.py \
  cross_role_relation_candidate_resolver_lite.py \
  hpfa/modules/core/cross_role_relation_candidate_resolver_lite/src/cross_role_relation_candidate_resolver.py \
  action_bundle_multi_family_review_taxonomy_lite.py \
  semantic_role_action_bundle_candidates_lite.py \
  match_local_identity_candidates_lite.py
python -m pytest -q \
  hpfa/modules/core/selected_action_consequence_surface_lite/tests \
  | tee "$OUT/selected_action_consequence_surface_pytest_v1.txt"

set +e
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
  bash "$REPO/tools/run_active_match_evidence_atom_inventory_v1.sh"
UPSTREAM_RC="$?"
set -e
[[ "$UPSTREAM_RC" -eq 0 ]] || fail "evidence_atom_spine_failed:$UPSTREAM_RC"

EVIDENCE_ATOM="$OUT/evidence_atom_inventory_lite_v1.json"
IDENTITY="$OUT/match_local_identity_candidates_lite_v1.json"
ACTION_BUNDLE="$OUT/semantic_role_action_bundle_candidates_lite_v1.json"
TAXONOMY="$OUT/action_bundle_multi_family_review_taxonomy_lite_v1.json"
RELATIONS="$OUT/cross_role_relation_candidate_resolver_lite_v1.json"
[[ -f "$EVIDENCE_ATOM" ]] || fail "evidence_atom_inventory_output_missing"

set +e
python match_local_identity_candidates_lite.py \
  --evidence-atom "$EVIDENCE_ATOM" \
  --out "$OUT" \
  | tee "$OUT/selected_action_consequence_surface_identity_refresh_v1.txt"
IDENTITY_RC="${PIPESTATUS[0]}"
set -e
[[ "$IDENTITY_RC" -eq 0 ]] || fail "identity_candidate_refresh_failed:$IDENTITY_RC"
[[ -f "$IDENTITY" ]] || fail "match_local_identity_candidates_output_missing"

set +e
python semantic_role_action_bundle_candidates_lite.py \
  --evidence-atoms "$EVIDENCE_ATOM" \
  --identity-candidates "$IDENTITY" \
  --out "$OUT" \
  | tee "$OUT/selected_action_consequence_surface_action_bundle_refresh_v1.txt"
ACTION_BUNDLE_RC="${PIPESTATUS[0]}"
set -e
[[ "$ACTION_BUNDLE_RC" -eq 0 ]] || fail "action_bundle_refresh_failed:$ACTION_BUNDLE_RC"
[[ -f "$ACTION_BUNDLE" ]] || fail "semantic_role_action_bundle_candidates_output_missing"

set +e
python action_bundle_multi_family_review_taxonomy_lite.py \
  --action-bundle "$ACTION_BUNDLE" \
  --out "$OUT" \
  | tee "$OUT/selected_action_consequence_surface_taxonomy_refresh_v1.txt"
TAXONOMY_RC="${PIPESTATUS[0]}"
set -e
[[ "$TAXONOMY_RC" -eq 0 ]] || fail "multi_family_taxonomy_refresh_failed:$TAXONOMY_RC"
[[ -f "$TAXONOMY" ]] || fail "multi_family_taxonomy_output_missing"

set +e
python cross_role_relation_candidate_resolver_lite.py \
  --action-bundle "$ACTION_BUNDLE" \
  --multi-family-taxonomy "$TAXONOMY" \
  --out "$OUT" \
  | tee "$OUT/selected_action_consequence_surface_relation_refresh_v1.txt"
RELATION_RC="${PIPESTATUS[0]}"
set -e
[[ "$RELATION_RC" -eq 0 ]] || fail "cross_role_relation_refresh_failed:$RELATION_RC"
[[ -f "$RELATIONS" ]] || fail "cross_role_relation_candidate_resolver_output_missing"

set +e
python selected_action_consequence_surface_lite.py \
  --action-bundle "$ACTION_BUNDLE" \
  --multi-family-taxonomy "$TAXONOMY" \
  --cross-role-relations "$RELATIONS" \
  --evidence-atoms "$EVIDENCE_ATOM" \
  --out "$OUT" \
  | tee "$OUT/selected_action_consequence_surface_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

OUTPUT="$OUT/selected_action_consequence_surface_lite_v1.json"
[[ -f "$OUTPUT" ]] || fail "selected_action_consequence_surface_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" "$ACTUAL_HEAD" <<'PY' \
  | tee "$OUT/selected_action_consequence_surface_runtime_audit_v1.txt"
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
print("HPFA SELECTED ACTION CONSEQUENCE SURFACE ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "module_status",
    "runtime_evidence_status",
    "release_status",
    "runtime_code_head_sha",
    "match_surface_binding_id",
    "field_semantics_version",
    "field_semantics_record_count",
    "source_action_bundle_candidate_count",
    "selected_action_surface_candidate_count",
    "suppressed_team_reflection_candidate_count",
    "quarantined_unresolved_surface_count",
    "selected_action_node_count",
    "same_time_multi_family_node_count",
    "selected_action_consequence_candidate_count",
    "team_action_family_consequence_profile_count",
    "actor_action_family_consequence_profile_count",
    "hard_block_hits",
    "review_hits",
    "active_match_execution_completed",
    "active_match_evidence_pass",
    "event_instance_count",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
print(f"selected_source_role_counts={payload.get('selected_source_role_counts')}")
print(f"selected_action_family_counts={payload.get('selected_action_family_counts')}")
print(f"primary_consequence_candidate_counts={payload.get('primary_consequence_candidate_counts')}")
print(f"first_layer_team_state_counts={payload.get('first_layer_team_state_counts')}")
print(f"retention_after_action_candidate_counts={payload.get('retention_after_action_candidate_counts')}")
print(f"same_team_response_latency_class_counts={payload.get('same_team_response_latency_class_counts')}")
print(f"opponent_response_latency_class_counts={payload.get('opponent_response_latency_class_counts')}")
print(f"turnover_response_candidate_counts={payload.get('turnover_response_candidate_counts')}")
print(f"coordinate_displacement_status_counts={payload.get('coordinate_displacement_status_counts')}")
print(f"raw_coordinate_displacement_class_counts={payload.get('raw_coordinate_displacement_class_counts')}")
print(f"actor_identity_applicability_counts={payload.get('actor_identity_applicability_counts')}")
print(f"support_atom_class_counts={payload.get('support_atom_class_counts')}")
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
  echo "identity_rc=$IDENTITY_RC"
  echo "action_bundle_rc=$ACTION_BUNDLE_RC"
  echo "taxonomy_rc=$TAXONOMY_RC"
  echo "relation_rc=$RELATION_RC"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUTPUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/selected_action_consequence_surface_result_v1.txt"

exit "$RUN_RC"
