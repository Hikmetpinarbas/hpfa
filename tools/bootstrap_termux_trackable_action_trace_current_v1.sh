#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-trackable-action-trace-current-v1"
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

[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] \
  || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-trackable-action-trace-current.XXXXXX")" \
  || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP

WORK="$TMP_ROOT/work"
git clone -q --branch "$BRANCH" --single-branch "$ORIGIN_URL" "$WORK" \
  || fail "trusted_repo_clone_failed"
ACTUAL_HEAD="$(git -C "$WORK" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] \
  || fail "remote_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$WORK" status --porcelain --untracked-files=all)" ]] \
  || fail "trusted_worktree_not_clean"

EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"
ADAPTER="$WORK/trackable_action_trace_candidates_current_v1.py"
[[ -f "$ADAPTER" ]] || fail "trackable_action_trace_runtime_adapter_missing"

RUN_RC=0
FAILED_STEP=""
set +e
(
  cd "$WORK"
  python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null
)
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then
  FAILED_STEP="trackable_action_trace_candidates"
fi

REPORT="$EVIDENCE/trackable_action_trace_candidates_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_TRACKABLE_ACTION_TRACE_KISA_SONUC.txt"
ZIP="$OUT/HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_*.zip \
      "$OUT"/.HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_*.zip.partial

python - "$REPORT" "$MANIFEST" "$SUMMARY" "$ACTUAL_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" "$FAILED_STEP" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
summary_path = Path(sys.argv[3])
head, runtime, run_rc_raw, failed_step = sys.argv[4:8]
run_rc = int(run_rc_raw)
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    report = {}

status = report.get("status") if report else "FAIL_CLOSED"
source_count = int(report.get("source_action_bundle_candidate_count") or 0)
selected_count = int(report.get("selected_primary_surface_candidate_count") or 0)
reflection_count = int(report.get("reflection_context_surface_candidate_count") or 0)
quarantine_count = int(report.get("quarantined_surface_candidate_count") or 0)
trace_count = int(report.get("trackable_action_trace_candidate_count") or 0)
bridge = report.get("current_content_source_role_bridge_status")
partition_ok = bool(
    report.get("selection_partition_complete") is True
    and selected_count + reflection_count + quarantine_count == source_count
    and int(report.get("selection_partition_coverage_count") or 0) == source_count
)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge == "PASS"
    and source_count > 0
    and trace_count > 0
    and partition_ok
    and report.get("trackable_action_candidate_is_event_truth") is False
    and report.get("physical_action_identity_truth") is False
    and report.get("trace_count_is_physical_action_count") is False
    and report.get("reflection_context_is_event_equivalence_truth") is False
    and report.get("final_double_count_suppression_admitted") is False
    and report.get("count_value_output_allowed") is False
    and report.get("consequence_classification_allowed") is False
    and report.get("sequence_link_allowed") is False
    and report.get("same_time_order_truth_admitted") is False
    and report.get("source_row_order_is_temporal_truth") is False
    and report.get("cross_role_fusion_allowed") is False
    and report.get("event_instance_count") == 0
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("true_action_count") == "UNKNOWN"
    and report.get("production_release") is False
    and not (report.get("hard_block_hits") or [])
)

manifest = {
    "bundle_version": "HPFA_TRACKABLE_ACTION_TRACE_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "content_source_role_bridge_status": bridge,
    "current_relation_status": report.get("current_relation_status"),
    "current_taxonomy_status": report.get("current_taxonomy_status"),
    "current_semantic_status": report.get("current_semantic_status"),
    "source_action_bundle_candidate_count": source_count,
    "selected_primary_surface_candidate_count": selected_count,
    "reflection_context_surface_candidate_count": reflection_count,
    "quarantined_surface_candidate_count": quarantine_count,
    "selection_partition_coverage_count": report.get("selection_partition_coverage_count"),
    "selection_partition_complete": report.get("selection_partition_complete"),
    "selected_surface_basis_counts": report.get("selected_surface_basis_counts") or {},
    "quarantine_basis_counts": report.get("quarantine_basis_counts") or {},
    "trackable_action_trace_candidate_count": trace_count,
    "relation_supported_trace_candidate_count": report.get("relation_supported_trace_candidate_count"),
    "standalone_primary_trace_candidate_count": report.get("standalone_primary_trace_candidate_count"),
    "same_surface_multi_family_trace_candidate_count": report.get("same_surface_multi_family_trace_candidate_count"),
    "trace_source_role_counts": report.get("trace_source_role_counts") or {},
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
    "trackable_action_candidate_is_event_truth": False,
    "physical_action_identity_truth": False,
    "trace_count_is_physical_action_count": False,
    "reflection_context_is_event_equivalence_truth": False,
    "final_double_count_suppression_admitted": False,
    "count_value_output_allowed": False,
    "consequence_classification_allowed": False,
    "sequence_link_allowed": False,
    "same_time_order_truth_admitted": False,
    "source_row_order_is_temporal_truth": False,
    "cross_role_fusion_allowed": False,
    "event_instance_count": 0,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

lines = [
    "==============================",
    "HPFA TRACKABLE ACTION TRACE KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={bridge}",
    f"current_relation_status={manifest['current_relation_status']}",
    f"source_action_bundle_candidate_count={source_count}",
    f"selected_primary_surface_candidate_count={selected_count}",
    f"reflection_context_surface_candidate_count={reflection_count}",
    f"quarantined_surface_candidate_count={quarantine_count}",
    f"selection_partition_complete={manifest['selection_partition_complete']}",
    f"trackable_action_trace_candidate_count={trace_count}",
    f"relation_supported_trace_candidate_count={manifest['relation_supported_trace_candidate_count']}",
    f"standalone_primary_trace_candidate_count={manifest['standalone_primary_trace_candidate_count']}",
    f"same_surface_multi_family_trace_candidate_count={manifest['same_surface_multi_family_trace_candidate_count']}",
    "selected_surface_basis_counts=" + json.dumps(manifest["selected_surface_basis_counts"], ensure_ascii=False, sort_keys=True),
    "quarantine_basis_counts=" + json.dumps(manifest["quarantine_basis_counts"], ensure_ascii=False, sort_keys=True),
    "trace_source_role_counts=" + json.dumps(manifest["trace_source_role_counts"], ensure_ascii=False, sort_keys=True),
    "trackable_action_candidate_is_event_truth=false",
    "physical_action_identity_truth=false",
    "trace_count_is_physical_action_count=false",
    "final_double_count_suppression_admitted=false",
    "count_value_output_allowed=false",
    "consequence_classification_allowed=false",
    "sequence_link_allowed=false",
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
import sys
import zipfile
from pathlib import Path

evidence = Path(sys.argv[1])
manifest = Path(sys.argv[2])
summary = Path(sys.argv[3])
out = Path(sys.argv[4])
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(evidence.iterdir()):
        if path.is_file():
            zf.write(path, arcname=path.name)
    zf.write(manifest, arcname=manifest.name)
    zf.write(summary, arcname=summary.name)
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
