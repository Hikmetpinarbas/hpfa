#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-row-nucleus-research-hardened-v1"
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

TMP_ROOT="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hpfa-row-nucleus.XXXXXX")" \
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
ADAPTER="$WORK/row_nucleus_inventory.py"
[[ -f "$ADAPTER" ]] || fail "row_nucleus_runtime_adapter_missing"

RUN_RC=0
FAILED_STEP=""
set +e
python "$ADAPTER" --input-dir "$ACTIVE_RESOLVED" --out-dir "$EVIDENCE" >/dev/null
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then
  FAILED_STEP="row_nucleus_inventory"
fi

REPORT="$EVIDENCE/row_nucleus_inventory_lite_v1.json"
MANIFEST="$TMP_ROOT/HPFA_ROW_NUCLEUS_ACTIVE_MATCH_EVIDENCE_MANIFEST.json"
SUMMARY="$TMP_ROOT/HPFA_ROW_NUCLEUS_KISA_SONUC.txt"
ZIP="$OUT/HPFA_ROW_NUCLEUS_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.zip"
ZIP_TMP="$OUT/.HPFA_ROW_NUCLEUS_ACTIVE_MATCH_${ACTUAL_HEAD:0:7}.$$.zip.partial"
rm -f "$OUT"/HPFA_ROW_NUCLEUS_ACTIVE_MATCH_*.zip \
      "$OUT"/.HPFA_ROW_NUCLEUS_ACTIVE_MATCH_*.zip.partial

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

bridge = report.get("content_source_role_bridge") or {}
bridge_status = report.get("content_source_role_bridge_status") or bridge.get("status")
status = report.get("status") if report else "FAIL_CLOSED"
candidate_count = int(report.get("row_nucleus_candidate_count") or 0)
active_pass = bool(
    run_rc == 0
    and status in {"PASS", "REVIEW_REQUIRED"}
    and bridge_status == "PASS"
    and candidate_count > 0
)

g09 = None
for gate in (report.get("g01_g18_rollup") or {}).get("gates", []) or []:
    if gate.get("gate_id") == "G09":
        g09 = gate.get("status")
        break

manifest = {
    "bundle_version": "HPFA_ROW_NUCLEUS_ACTIVE_MATCH_EVIDENCE_V1",
    "head_sha": head,
    "runtime_authority": runtime,
    "run_rc": run_rc,
    "failed_step": failed_step or None,
    "status": status if active_pass else "FAIL_CLOSED",
    "runtime_evidence_status": "ACTIVE_MATCH_EVIDENCE_PASS" if active_pass else "FAIL_CLOSED",
    "active_match_evidence_pass": active_pass,
    "content_source_role_bridge_status": bridge_status,
    "row_nucleus_candidate_count": report.get("row_nucleus_candidate_count"),
    "row_nucleus_pass_count": report.get("row_nucleus_pass_count"),
    "row_nucleus_review_required_count": report.get("row_nucleus_review_required_count"),
    "surface_row_count": report.get("surface_row_count"),
    "source_role_candidate_counts": report.get("source_role_candidate_counts") or {},
    "serialization_relation_candidate_counts": report.get("serialization_relation_candidate_counts") or {},
    "g09_status": g09,
    "duplicate_surface_file_reflection_count": report.get("duplicate_surface_file_reflection_count"),
    "xlsx_used_for_row_nucleus_identity": report.get("xlsx_used_for_row_nucleus_identity"),
    "filename_support_used_for_role_admission": False,
    "filename_role_used_for_nucleus_grouping": False,
    "row_nucleus_is_canonical_event": False,
    "physical_action_identity_truth": False,
    "independent_source_vote_allowed": False,
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
    "HPFA ROW NUCLEUS KISA SONUÇ",
    "==============================",
    f"run_rc={run_rc}",
    f"failed_step={failed_step}",
    f"status={manifest['status']}",
    f"active_match_evidence_pass={active_pass}",
    f"content_source_role_bridge_status={bridge_status}",
    f"surface_row_count={manifest['surface_row_count']}",
    f"row_nucleus_candidate_count={manifest['row_nucleus_candidate_count']}",
    f"row_nucleus_pass_count={manifest['row_nucleus_pass_count']}",
    f"row_nucleus_review_required_count={manifest['row_nucleus_review_required_count']}",
    "source_role_candidate_counts=" + json.dumps(manifest["source_role_candidate_counts"], ensure_ascii=False, sort_keys=True),
    "serialization_relation_candidate_counts=" + json.dumps(manifest["serialization_relation_candidate_counts"], ensure_ascii=False, sort_keys=True),
    f"g09_status={g09}",
    f"duplicate_surface_file_reflection_count={manifest['duplicate_surface_file_reflection_count']}",
    f"xlsx_used_for_row_nucleus_identity={manifest['xlsx_used_for_row_nucleus_identity']}",
    "filename_support_used_for_role_admission=false",
    "filename_role_used_for_nucleus_grouping=false",
    "physical_action_identity_truth=false",
    "independent_source_vote_allowed=false",
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
