#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-trackable-action-consequence-current-v1"
ORIGIN_URL="https://github.com/Hikmetpinarbas/hpfa.git"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in */runtime/active_single_match/current) ;; *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;; esac
case "$OUT" in /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;; */HPFA/*) fail "nested_phone_output_directory_rejected" ;; *) fail "phone_output_directory_not_allowed:$OUT" ;; esac
mkdir -p "$OUT"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-trackable-action-consequence-current.XXXXXX")" || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP
WORK="$TMP_ROOT/work"
git clone -q --branch "$BRANCH" --single-branch "$ORIGIN_URL" "$WORK" || fail "trusted_repo_clone_failed"
ACTUAL_HEAD="$(git -C "$WORK" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "remote_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$WORK" status --porcelain --untracked-files=all)" ]] || fail "trusted_worktree_not_clean"

EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"
ADAPTER="$WORK/trackable_action_consequence_candidates_current_v1.py"
[[ -f "$ADAPTER" ]] || fail "trackable_action_consequence_runtime_adapter_missing"
RUN_RC=0
FAILED_STEP=""
set +e
( cd "$WORK" && python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null )
RUN_RC=$?
set -e
[[ "$RUN_RC" -eq 0 ]] || FAILED_STEP="trackable_action_consequence_candidates"

REPORT="$EVIDENCE/trackable_action_consequence_candidates_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_TRACKABLE_ACTION_CONSEQUENCE_KISA_SONUC.txt"
ZIP="$OUT/HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_*.zip.partial

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
source_count = int(report.get("source_trackable_action_trace_candidate_count") or 0)
consequence_count = int(report.get("trackable_action_consequence_candidate_count") or 0)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and report.get("current_content_source_role_bridge_status") == "PASS"
    and source_count > 0
    and consequence_count == source_count
    and not (report.get("hard_block_hits") or [])
    and report.get("same_time_link_allowed") is False
    and report.get("negative_time_link_allowed") is False
    and report.get("cross_period_link_allowed") is False
    and report.get("source_row_order_is_temporal_truth") is False
    and report.get("consequence_candidate_is_causal_truth") is False
    and report.get("continuation_candidate_is_possession_truth") is False
    and report.get("window_is_sequence_truth") is False
    and report.get("team_response_is_tactical_truth") is False
    and report.get("sequence_link_allowed") is False
    and report.get("event_instance_count") == 0
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("true_action_count") == "UNKNOWN"
    and report.get("production_release") is False
)
manifest = {
    "bundle_version": "HPFA_TRACKABLE_ACTION_CONSEQUENCE_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "content_source_role_bridge_status": report.get("current_content_source_role_bridge_status"),
    "current_trace_status": report.get("current_trace_status"),
    "source_trackable_action_trace_candidate_count": source_count,
    "trackable_action_consequence_candidate_count": consequence_count,
    "classified_consequence_candidate_count": report.get("classified_consequence_candidate_count"),
    "review_required_consequence_candidate_count": report.get("review_required_consequence_candidate_count"),
    "support_visible_trace_count": report.get("support_visible_trace_count"),
    "primary_consequence_candidate_counts": report.get("primary_consequence_candidate_counts") or {},
    "window_coverage_counts": report.get("window_coverage_counts") or {},
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
    "same_time_link_allowed": False,
    "negative_time_link_allowed": False,
    "cross_period_link_allowed": False,
    "source_row_order_is_temporal_truth": False,
    "consequence_candidate_is_causal_truth": False,
    "continuation_candidate_is_possession_truth": False,
    "window_is_sequence_truth": False,
    "team_response_is_tactical_truth": False,
    "sequence_link_allowed": False,
    "event_instance_count": 0,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
lines = [
    "==============================",
    "HPFA TRACKABLE ACTION CONSEQUENCE KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={manifest['content_source_role_bridge_status']}",
    f"current_trace_status={manifest['current_trace_status']}",
    f"source_trackable_action_trace_candidate_count={source_count}",
    f"trackable_action_consequence_candidate_count={consequence_count}",
    f"classified_consequence_candidate_count={manifest['classified_consequence_candidate_count']}",
    f"review_required_consequence_candidate_count={manifest['review_required_consequence_candidate_count']}",
    f"support_visible_trace_count={manifest['support_visible_trace_count']}",
    "primary_consequence_candidate_counts=" + json.dumps(manifest["primary_consequence_candidate_counts"], ensure_ascii=False, sort_keys=True),
    "window_coverage_counts=" + json.dumps(manifest["window_coverage_counts"], ensure_ascii=False, sort_keys=True),
    "same_time_link_allowed=false",
    "negative_time_link_allowed=false",
    "cross_period_link_allowed=false",
    "consequence_candidate_is_causal_truth=false",
    "continuation_candidate_is_possession_truth=false",
    "window_is_sequence_truth=false",
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
