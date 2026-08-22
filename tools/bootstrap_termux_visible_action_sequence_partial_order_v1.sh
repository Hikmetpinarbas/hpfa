#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-visible-sequence-partial-order-v1"
ORIGIN_URL="https://github.com/Hikmetpinarbas/hpfa.git"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }

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
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-visible-sequence-partial-order.XXXXXX")" || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP
WORK="$TMP_ROOT/work"
git clone -q --branch "$BRANCH" --single-branch "$ORIGIN_URL" "$WORK" || fail "trusted_repo_clone_failed"
ACTUAL_HEAD="$(git -C "$WORK" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "remote_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$WORK" status --porcelain --untracked-files=all)" ]] || fail "trusted_worktree_not_clean"

CONTRACT="$WORK/hpfa/modules/core/visible_action_sequence_candidates_lite/contract/visible_action_sequence_candidates_lite_v1.json"
python - "$CONTRACT" <<'PY' || fail "partial_order_contract_guard_failed"
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
q = p.get("partial_order_audit") or {}
assert q.get("relation_states") == [
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
]
assert q.get("ordering_evidence_scope") == "VISIBLE_TIMESTAMP_ONLY"
assert q.get("same_timestamp_default") == "SAME_TIME_UNORDERED"
assert q.get("missing_or_ambiguous_order_default") == "ORDER_INDETERMINATE"
assert q.get("source_row_index_relation") == "PROVENANCE_ORDER_ONLY"
assert q.get("directly_follows_truth") is False
assert q.get("relation_records_may_create_action_volume") is False
assert q.get("relation_records_may_create_possession_truth") is False
assert q.get("relation_records_may_create_sequence_truth") is False
PY

EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"
ADAPTER="$WORK/visible_action_sequence_candidates_current_v1.py"
[[ -f "$ADAPTER" ]] || fail "visible_sequence_runtime_adapter_missing"

RUN_RC=0
FAILED_STEP=""
set +e
(
  cd "$WORK"
  python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null
)
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then FAILED_STEP="visible_action_sequence_candidates"; fi

REPORT="$EVIDENCE/visible_action_sequence_candidates_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_KISA_SONUC.txt"
ZIP="$OUT/HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_*.zip.partial

python - "$REPORT" "$MANIFEST" "$SUMMARY" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" "$FAILED_STEP" <<'PY'
import json, sys
from pathlib import Path

report_path, manifest_path, summary_path = map(Path, sys.argv[1:4])
head, runtime, run_rc_raw, failed_step = sys.argv[4:8]
run_rc = int(run_rc_raw)
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    report = {}
status = report.get("status") if report else "FAIL_CLOSED"
bridge = report.get("current_content_source_role_bridge_status")
trace_count = int(report.get("source_trackable_action_trace_candidate_count") or 0)
consequence_count = int(report.get("source_trackable_action_consequence_candidate_count") or 0)
layer_count = int(report.get("visible_action_time_layer_candidate_count") or 0)
sequence_count = int(report.get("visible_action_sequence_candidate_count") or 0)
assignment_count = int(report.get("trace_assignment_count") or 0)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge == "PASS"
    and trace_count > 0
    and consequence_count == trace_count
    and layer_count > 0
    and sequence_count > 0
    and assignment_count == trace_count
    and report.get("trace_assignment_complete") is True
    and report.get("strict_positive_inter_layer_time_required") is True
    and report.get("same_timestamp_internal_ordering_allowed") is False
    and report.get("source_row_order_is_temporal_truth") is False
    and report.get("visible_sequence_candidate_is_sequence_truth") is False
    and report.get("visible_sequence_candidate_is_possession_truth") is False
    and report.get("single_team_continuity_is_control_truth") is False
    and report.get("sequence_duration_is_physical_action_duration") is False
    and report.get("sequence_truth") is False
    and report.get("possession_truth") is False
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("true_action_count") == "UNKNOWN"
    and report.get("production_release") is False
    and not (report.get("hard_block_hits") or [])
)
manifest = {
    "bundle_version": "HPFA_VISIBLE_ACTION_SEQUENCE_PARTIAL_ORDER_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "content_source_role_bridge_status": bridge,
    "current_consequence_status": report.get("current_consequence_status"),
    "source_trackable_action_trace_candidate_count": trace_count,
    "source_trackable_action_consequence_candidate_count": consequence_count,
    "visible_action_time_layer_candidate_count": layer_count,
    "single_team_primary_layer_count": report.get("single_team_primary_layer_count"),
    "mixed_team_primary_layer_review_required_count": report.get("mixed_team_primary_layer_review_required_count"),
    "visible_action_sequence_candidate_count": sequence_count,
    "pass_multi_layer_visible_sequence_candidate_count": report.get("pass_multi_layer_visible_sequence_candidate_count"),
    "pass_single_layer_visible_trace_candidate_count": report.get("pass_single_layer_visible_trace_candidate_count"),
    "review_required_sequence_context_count": report.get("review_required_sequence_context_count"),
    "review_time_layer_count": report.get("review_time_layer_count"),
    "primary_sequence_member_trace_count": report.get("primary_sequence_member_trace_count"),
    "review_layer_member_trace_count": report.get("review_layer_member_trace_count"),
    "trace_assignment_count": assignment_count,
    "trace_assignment_complete": report.get("trace_assignment_complete"),
    "layer_state_counts": report.get("layer_state_counts") or {},
    "sequence_status_counts": report.get("sequence_status_counts") or {},
    "boundary_reason_counts": report.get("boundary_reason_counts") or {},
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
    "max_inter_layer_gap_seconds": report.get("max_inter_layer_gap_seconds"),
    "strict_positive_inter_layer_time_required": True,
    "same_timestamp_internal_ordering_allowed": False,
    "source_row_order_is_temporal_truth": False,
    "partial_order_relation_vocabulary": [
        "BEFORE_CONFIRMED",
        "AFTER_CONFIRMED",
        "SAME_TIME_UNORDERED",
        "ORDER_INDETERMINATE",
        "PROVENANCE_ORDER_ONLY",
    ],
    "visible_sequence_candidate_is_sequence_truth": False,
    "visible_sequence_candidate_is_possession_truth": False,
    "single_team_continuity_is_control_truth": False,
    "sequence_duration_is_physical_action_duration": False,
    "sequence_truth": False,
    "possession_truth": False,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
lines = [
    "==============================",
    "HPFA VISIBLE ACTION SEQUENCE + PARTIAL ORDER KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={bridge}",
    f"source_trackable_action_trace_candidate_count={trace_count}",
    f"visible_action_time_layer_candidate_count={layer_count}",
    f"mixed_team_primary_layer_review_required_count={manifest['mixed_team_primary_layer_review_required_count']}",
    f"visible_action_sequence_candidate_count={sequence_count}",
    f"trace_assignment_complete={manifest['trace_assignment_complete']}",
    "same_timestamp_internal_ordering_allowed=false",
    "source_row_order_is_temporal_truth=false",
    "partial_order_same_timestamp_default=SAME_TIME_UNORDERED",
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
  python - "$EVIDENCE" "$MANIFEST" "$SUMMARY" "$ZIP_TMP" <<'PY'
import sys, zipfile
from pathlib import Path
evidence, manifest, summary, out = map(Path, sys.argv[1:5])
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(evidence.iterdir()):
        if path.is_file(): zf.write(path, arcname=path.name)
    zf.write(manifest, arcname=manifest.name)
    zf.write(summary, arcname=summary.name)
PY
  mv "$ZIP_TMP" "$ZIP"
else
  rm -f "$ZIP_TMP" "$ZIP"
fi
cat "$SUMMARY"
if [[ -f "$ZIP" ]]; then echo "ZIP=$ZIP"; else echo "ZIP=NOT_CREATED"; fi
[[ "$ACTIVE_PASS" == "true" ]] || exit 2
