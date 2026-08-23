#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){
  local value="${1:-}"
  value="${value%/}"; value="${value%.git}"
  value="${value#https://github.com/}"; value="${value#http://github.com/}"
  value="${value#git@github.com:}"; value="${value#ssh://git@github.com/}"
  printf '%s\n' "${value,,}"
}

[[ -n "$BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in
  */runtime/active_single_match/current) ;;
  *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;;
esac

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac
mkdir -p "$OUT"

[[ -d "$REPO" ]] || fail "product_repo_missing:$REPO"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "product_repo_not_git_checkout:$REPO"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "product_repo_worktree_not_clean:$REPO"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"

git -C "$REPO" fetch origin "$BRANCH"
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch -c "$BRANCH" --track "origin/$BRANCH"
fi
git -C "$REPO" merge --ff-only "origin/$BRANCH"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "execution_branch_mismatch:$ACTUAL_BRANCH expected:$BRANCH"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "execution_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "product_repo_worktree_not_clean_after_ff:$REPO"

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-c3-reconstruction.XXXXXX")" || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP
EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"

RUN_RC=0
set +e
(
  cd "$REPO"
  python visible_action_sequence_candidates_current_v1.py \
    --input-dir "$ACTIVE_RESOLVED" \
    --out-dir "$EVIDENCE"
) >"$TMP_ROOT/c3_runtime.log" 2>&1
RUN_RC=$?
set -e

REPORT="$EVIDENCE/visible_action_sequence_candidates_lite_v1.json"
CONTRACT="$REPO/hpfa/modules/core/visible_action_sequence_candidates_lite/contract/visible_action_sequence_candidates_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_C3_RECONSTRUCTION_KISA_SONUC.txt"
ZIP="$OUT/HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_*.zip.partial

python - "$REPORT" "$CONTRACT" "$MANIFEST" "$SUMMARY" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
contract_path = Path(sys.argv[2])
manifest_path = Path(sys.argv[3])
summary_path = Path(sys.argv[4])
branch, head, runtime, run_rc_raw = sys.argv[5:9]
run_rc = int(run_rc_raw)

try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    report = {}
try:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
except Exception:
    contract = {}

partial = contract.get("partial_order_audit") or {}
time_rules = contract.get("time_layer_rules") or {}
claim = contract.get("claim_boundary") or {}
relation_states = partial.get("relation_states") or []
required_states = [
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
]
contract_pass = bool(
    relation_states == required_states
    and partial.get("ordering_evidence_scope") == "VISIBLE_TIMESTAMP_ONLY"
    and partial.get("same_timestamp_default") == "SAME_TIME_UNORDERED"
    and partial.get("missing_or_ambiguous_order_default") == "ORDER_INDETERMINATE"
    and partial.get("source_row_index_relation") == "PROVENANCE_ORDER_ONLY"
    and partial.get("directly_follows_truth") is False
    and partial.get("relation_records_may_create_action_volume") is False
    and partial.get("relation_records_may_create_possession_truth") is False
    and partial.get("relation_records_may_create_sequence_truth") is False
    and time_rules.get("same_timestamp_internal_ordering_allowed") is False
    and time_rules.get("source_row_order_is_temporal_truth") is False
    and claim.get("sequence_truth") is False
    and claim.get("possession_truth") is False
    and claim.get("canonical_event_count") == "UNKNOWN"
    and claim.get("true_action_count") == "UNKNOWN"
    and claim.get("production_release") is False
)

status = report.get("status") if report else "FAIL_CLOSED"
bridge = report.get("current_content_source_role_bridge_status")
source_trace_count = int(report.get("source_trackable_action_trace_candidate_count") or 0)
source_consequence_count = int(report.get("source_trackable_action_consequence_candidate_count") or 0)
sequence_count = int(report.get("visible_action_sequence_candidate_count") or 0)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge == "PASS"
    and contract_pass
    and source_trace_count > 0
    and source_consequence_count == source_trace_count
    and sequence_count > 0
    and report.get("trace_assignment_complete") is True
    and report.get("same_timestamp_internal_ordering_allowed") is False
    and report.get("source_row_order_is_temporal_truth") is False
    and report.get("visible_sequence_candidate_is_sequence_truth") is False
    and report.get("visible_sequence_candidate_is_possession_truth") is False
    and report.get("single_team_continuity_is_control_truth") is False
    and report.get("sequence_duration_is_physical_action_duration") is False
    and report.get("phase_truth") is False
    and report.get("possession_truth") is False
    and report.get("sequence_truth") is False
    and report.get("tactical_truth") is False
    and report.get("event_instance_count") == 0
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("true_action_count") == "UNKNOWN"
    and report.get("production_release") is False
    and not (report.get("hard_block_hits") or [])
)

manifest = {
    "bundle_version": "HPFA_C3_RECONSTRUCTION_ACTIVE_MATCH_EVIDENCE_V1",
    "branch": branch,
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "partial_order_contract_pass": contract_pass,
    "content_source_role_bridge_status": bridge,
    "source_trackable_action_trace_candidate_count": report.get("source_trackable_action_trace_candidate_count"),
    "source_trackable_action_consequence_candidate_count": report.get("source_trackable_action_consequence_candidate_count"),
    "visible_action_time_layer_candidate_count": report.get("visible_action_time_layer_candidate_count"),
    "single_team_primary_layer_count": report.get("single_team_primary_layer_count"),
    "mixed_team_primary_layer_review_required_count": report.get("mixed_team_primary_layer_review_required_count"),
    "visible_action_sequence_candidate_count": report.get("visible_action_sequence_candidate_count"),
    "pass_multi_layer_visible_sequence_candidate_count": report.get("pass_multi_layer_visible_sequence_candidate_count"),
    "pass_single_layer_visible_trace_candidate_count": report.get("pass_single_layer_visible_trace_candidate_count"),
    "review_required_sequence_context_count": report.get("review_required_sequence_context_count"),
    "primary_sequence_member_trace_count": report.get("primary_sequence_member_trace_count"),
    "review_layer_member_trace_count": report.get("review_layer_member_trace_count"),
    "trace_assignment_complete": report.get("trace_assignment_complete"),
    "boundary_reason_counts": report.get("boundary_reason_counts") or {},
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
    "partial_order_relation_states": required_states,
    "ordering_evidence_scope": "VISIBLE_TIMESTAMP_ONLY",
    "partial_order_same_timestamp_default": "SAME_TIME_UNORDERED",
    "partial_order_missing_or_ambiguous_default": "ORDER_INDETERMINATE",
    "source_row_index_relation": "PROVENANCE_ORDER_ONLY",
    "same_timestamp_internal_ordering_allowed": False,
    "source_row_order_is_temporal_truth": False,
    "directly_follows_truth": False,
    "visible_sequence_candidate_is_sequence_truth": False,
    "visible_sequence_candidate_is_possession_truth": False,
    "sequence_truth": False,
    "possession_truth": False,
    "phase_truth": False,
    "tactical_truth": False,
    "event_instance_count": 0,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "==============================",
    "HPFA C3 RECONSTRUCTION KISA SONUÇ",
    "==============================",
    f"branch={branch}",
    f"head_sha={head}",
    f"run_rc={run_rc}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"partial_order_contract_pass={contract_pass}",
    f"content_source_role_bridge_status={bridge}",
    f"source_trackable_action_trace_candidate_count={manifest['source_trackable_action_trace_candidate_count']}",
    f"visible_action_time_layer_candidate_count={manifest['visible_action_time_layer_candidate_count']}",
    f"mixed_team_primary_layer_review_required_count={manifest['mixed_team_primary_layer_review_required_count']}",
    f"visible_action_sequence_candidate_count={manifest['visible_action_sequence_candidate_count']}",
    f"trace_assignment_complete={manifest['trace_assignment_complete']}",
    "partial_order_same_timestamp_default=SAME_TIME_UNORDERED",
    "same_timestamp_internal_ordering_allowed=false",
    "source_row_order_is_temporal_truth=false",
    "visible_sequence_candidate_is_sequence_truth=false",
    "visible_sequence_candidate_is_possession_truth=false",
    "sequence_truth=false",
    "possession_truth=false",
    "canonical_event_count=UNKNOWN",
    "true_action_count=UNKNOWN",
    "production_release=false",
    "==============================",
]
summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

ACTIVE_PASS="$(python - "$MANIFEST" <<'PY'
import json, sys
print("true" if json.load(open(sys.argv[1], encoding="utf-8")).get("active_match_evidence_pass") else "false")
PY
)"

if [[ "$ACTIVE_PASS" == "true" ]]; then
  python - "$EVIDENCE" "$MANIFEST" "$SUMMARY" "$TMP_ROOT/c3_runtime.log" "$ZIP_TMP" <<'PY'
import sys
import zipfile
from pathlib import Path

evidence = Path(sys.argv[1])
manifest = Path(sys.argv[2])
summary = Path(sys.argv[3])
log = Path(sys.argv[4])
out = Path(sys.argv[5])
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(evidence.iterdir()):
        if path.is_file():
            zf.write(path, arcname=path.name)
    zf.write(manifest, arcname=manifest.name)
    zf.write(summary, arcname=summary.name)
    zf.write(log, arcname=log.name)
PY
  mv "$ZIP_TMP" "$ZIP"
else
  rm -f "$ZIP_TMP" "$ZIP"
fi

cat "$SUMMARY"
if [[ -f "$ZIP" ]]; then
  echo "ZIP=$ZIP"
else
  echo "ZIP=NOT_CREATED"
fi

[[ "$ACTIVE_PASS" == "true" ]] || exit 2
