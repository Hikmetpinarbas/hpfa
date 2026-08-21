#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-cross-role-relation-current-v1"
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

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-cross-role-current.XXXXXX")" || fail "tempdir_create_failed"
cleanup(){ rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM HUP

WORK="$TMP_ROOT/work"
git clone -q --branch "$BRANCH" --single-branch "$ORIGIN_URL" "$WORK" || fail "trusted_repo_clone_failed"
ACTUAL_HEAD="$(git -C "$WORK" rev-parse HEAD 2>/dev/null || true)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "remote_head_mismatch:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$WORK" status --porcelain --untracked-files=all)" ]] || fail "trusted_worktree_not_clean"

EVIDENCE="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE"
ADAPTER="$WORK/cross_role_relation_candidate_resolver_current_v1.py"
[[ -f "$ADAPTER" ]] || fail "cross_role_relation_current_adapter_missing"

RUN_RC=0
FAILED_STEP=""
set +e
python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then
  FAILED_STEP="cross_role_relation_candidate_resolver"
fi

REPORT="$EVIDENCE/cross_role_relation_candidate_resolver_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_CROSS_ROLE_RELATION_KISA_SONUC.txt"
ZIP="$OUT/HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_*.zip.partial

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
source_count = int(report.get("source_cross_role_relation_candidate_count") or 0)
resolved_count = int(report.get("resolved_relation_candidate_count") or 0)
bridge = report.get("current_content_source_role_bridge_status")
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge == "PASS"
    and source_count > 0
    and resolved_count == source_count
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("true_action_count") == "UNKNOWN"
    and report.get("same_time_only_link_allowed") is False
    and report.get("source_row_order_is_temporal_truth") is False
    and report.get("relation_candidate_is_event_truth") is False
    and report.get("reflection_equivalence_truth") is False
    and report.get("double_count_suppression_is_final") is False
    and report.get("count_value_output_allowed") is False
    and report.get("cross_role_fusion_allowed") is False
    and report.get("event_instance_count") == 0
    and report.get("production_release") is False
    and not (report.get("hard_block_hits") or [])
)

manifest = {
    "bundle_version": "HPFA_CROSS_ROLE_RELATION_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "content_source_role_bridge_status": bridge,
    "current_semantic_status": report.get("current_semantic_status"),
    "current_taxonomy_status": report.get("current_taxonomy_status"),
    "source_action_bundle_candidate_count": report.get("source_action_bundle_candidate_count"),
    "source_cross_role_relation_candidate_count": report.get("source_cross_role_relation_candidate_count"),
    "resolved_relation_candidate_count": report.get("resolved_relation_candidate_count"),
    "candidate_clear_relation_count": report.get("candidate_clear_relation_count"),
    "review_required_relation_count": report.get("review_required_relation_count"),
    "double_count_suppression_candidate_count": report.get("double_count_suppression_candidate_count"),
    "relation_classification_counts": report.get("relation_classification_counts") or {},
    "relation_role_pair_counts": report.get("relation_role_pair_counts") or {},
    "relation_family_counts": report.get("relation_family_counts") or {},
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
    "same_time_only_link_allowed": False,
    "source_row_order_is_temporal_truth": False,
    "relation_candidate_is_event_truth": False,
    "reflection_equivalence_truth": False,
    "double_count_suppression_is_final": False,
    "count_value_output_allowed": False,
    "cross_role_fusion_allowed": False,
    "event_instance_count": 0,
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "==============================",
    "HPFA CROSS-ROLE RELATION KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={bridge}",
    f"current_semantic_status={manifest['current_semantic_status']}",
    f"current_taxonomy_status={manifest['current_taxonomy_status']}",
    f"source_cross_role_relation_candidate_count={manifest['source_cross_role_relation_candidate_count']}",
    f"resolved_relation_candidate_count={manifest['resolved_relation_candidate_count']}",
    f"candidate_clear_relation_count={manifest['candidate_clear_relation_count']}",
    f"review_required_relation_count={manifest['review_required_relation_count']}",
    f"double_count_suppression_candidate_count={manifest['double_count_suppression_candidate_count']}",
    "relation_classification_counts=" + json.dumps(manifest["relation_classification_counts"], ensure_ascii=False, sort_keys=True),
    "relation_role_pair_counts=" + json.dumps(manifest["relation_role_pair_counts"], ensure_ascii=False, sort_keys=True),
    "same_time_only_link_allowed=false",
    "source_row_order_is_temporal_truth=false",
    "relation_candidate_is_event_truth=false",
    "reflection_equivalence_truth=false",
    "double_count_suppression_is_final=false",
    "count_value_output_allowed=false",
    "cross_role_fusion_allowed=false",
    "event_instance_count=0",
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
