#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-evidence-atom-current-v1"
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

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-evidence-atom-current.XXXXXX")" \
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
ADAPTER="$WORK/evidence_atom_inventory_lite.py"
[[ -f "$ADAPTER" ]] || fail "evidence_atom_runtime_adapter_missing"

RUN_RC=0
FAILED_STEP=""
set +e
python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then
  FAILED_STEP="evidence_atom_inventory"
fi

REPORT="$EVIDENCE/evidence_atom_inventory_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_EVIDENCE_ATOM_KISA_SONUC.txt"
ZIP="$OUT/HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_*.zip \
      "$OUT"/.HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_*.zip.partial

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
bridge = report.get("current_content_source_role_bridge_status")
atom_count = int(report.get("evidence_atom_count") or 0)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge == "PASS"
    and atom_count > 0
    and report.get("canonical_event_count") == "UNKNOWN"
    and report.get("physical_action_identity_truth") is False
    and report.get("event_instance_allowed") is False
    and report.get("cross_role_fusion_allowed") is False
    and report.get("xlsx_row_identity_allowed") is False
    and report.get("production_release") is False
    and not (report.get("hard_block_hits") or [])
)

manifest = {
    "bundle_version": "HPFA_EVIDENCE_ATOM_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "current_row_nucleus_status": report.get("current_row_nucleus_status"),
    "content_source_role_bridge_status": bridge,
    "source_row_nucleus_candidate_count": report.get("source_row_nucleus_candidate_count"),
    "evidence_atom_count": report.get("evidence_atom_count"),
    "evidence_atom_pass_count": report.get("evidence_atom_pass_count"),
    "evidence_atom_review_required_count": report.get("evidence_atom_review_required_count"),
    "atom_class_counts": report.get("atom_class_counts") or {},
    "dependent_reflection_adds_support_vote": report.get("dependent_reflection_adds_support_vote"),
    "xlsx_row_identity_allowed": report.get("xlsx_row_identity_allowed"),
    "source_row_index_is_temporal_order_truth": report.get("source_row_index_is_temporal_order_truth"),
    "same_time_artificial_order_allowed": report.get("same_time_artificial_order_allowed"),
    "event_instance_allowed": report.get("event_instance_allowed"),
    "cross_role_fusion_allowed": report.get("cross_role_fusion_allowed"),
    "physical_action_identity_truth": report.get("physical_action_identity_truth"),
    "validated_event_identity": report.get("validated_event_identity"),
    "canonical_event_count": "UNKNOWN",
    "true_action_count": "UNKNOWN",
    "production_release": False,
    "hard_block_hits": report.get("hard_block_hits") or [],
    "review_hits": report.get("review_hits") or [],
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

lines = [
    "==============================",
    "HPFA EVIDENCE ATOM KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={bridge}",
    f"source_row_nucleus_candidate_count={manifest['source_row_nucleus_candidate_count']}",
    f"evidence_atom_count={manifest['evidence_atom_count']}",
    f"evidence_atom_pass_count={manifest['evidence_atom_pass_count']}",
    f"evidence_atom_review_required_count={manifest['evidence_atom_review_required_count']}",
    "atom_class_counts=" + json.dumps(manifest["atom_class_counts"], ensure_ascii=False, sort_keys=True),
    f"dependent_reflection_adds_support_vote={manifest['dependent_reflection_adds_support_vote']}",
    f"xlsx_row_identity_allowed={manifest['xlsx_row_identity_allowed']}",
    f"same_time_artificial_order_allowed={manifest['same_time_artificial_order_allowed']}",
    f"event_instance_allowed={manifest['event_instance_allowed']}",
    f"cross_role_fusion_allowed={manifest['cross_role_fusion_allowed']}",
    f"physical_action_identity_truth={manifest['physical_action_identity_truth']}",
    "canonical_event_count=UNKNOWN",
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
