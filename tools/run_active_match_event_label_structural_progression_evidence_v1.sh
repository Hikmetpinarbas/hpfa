#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/event-label-structural-progression-evidence-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
MARKER="$OUT/.event_label_structural_progression_evidence_run_marker_v1"
BUNDLE="$OUT/event_label_structural_progression_evidence_bundle_v1.zip"
MANIFEST="$OUT/event_label_structural_progression_evidence_bundle_manifest_v1.json"
BUNDLE_SHA="$OUT/event_label_structural_progression_evidence_bundle_v1.sha256"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 2; }

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"

BRANCH="$(git -C "$REPO" branch --show-current)"
HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$BRANCH expected:$EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_missing_or_invalid:${EXPECTED_HEAD:-EMPTY}"
EXPECTED_HEAD="${EXPECTED_HEAD,,}"
[[ "$HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$HEAD expected:$EXPECTED_HEAD"
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
  "$OUT/event_label_structural_progression_evidence_lite_v1.json" \
  "$OUT/event_label_structural_progression_evidence_lite_v1.txt" \
  "$OUT/event_label_structural_progression_evidence_analyst_audit_v1.txt" \
  "$OUT/event_label_structural_progression_evidence_runtime_audit_v1.txt" \
  "$OUT/event_label_structural_progression_evidence_result_v1.txt" \
  "$OUT/event_label_structural_progression_evidence_pytest_v1.txt" \
  "$OUT/event_label_structural_progression_evidence_active_match_v1.txt" \
  "$BUNDLE" "$MANIFEST" "$BUNDLE_SHA" "$MARKER"
: > "$MARKER"

python -m py_compile \
  event_label_structural_progression_evidence_lite.py \
  hpfa/modules/core/event_label_structural_progression_evidence_lite/src/event_label_structural_progression_evidence.py
python -m pytest -q \
  hpfa/modules/core/event_label_structural_progression_evidence_lite/tests \
  | tee "$OUT/event_label_structural_progression_evidence_pytest_v1.txt"

set +e
HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_MATCH" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
HPFA_PHONE_OUTPUT="$OUT" \
  bash "$REPO/tools/run_active_match_context_slicer_v1.sh"
SPINE_RC=$?
set -e
[[ "$SPINE_RC" -eq 0 ]] || fail "context_spine_failed:$SPINE_RC"

PROVIDER_LABELS="$OUT/provider_label_value_semantics_lite_v1.json"
SELECTED_ACTION="$OUT/selected_action_consequence_surface_lite_v1.json"
XLSX_AUDIT="$OUT/xlsx_surface_audit_lite_v1.json"
SELECTED_EVENT="$OUT/selected_event_consequence_surface_lite_v1.json"
SEQUENCE_CONSEQUENCE="$OUT/eventonly_sequence_consequence_result_v1.json"
AGGREGATE_ALIGNMENT="$OUT/aggregate_definition_alignment_lite_v1.json"
AGGREGATE_REGISTRY="$REPO/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json"
OUTPUT="$OUT/event_label_structural_progression_evidence_lite_v1.json"

[[ -f "$PROVIDER_LABELS" ]] || fail "provider_label_semantics_output_missing"
[[ -f "$SELECTED_ACTION" ]] || fail "selected_action_consequence_output_missing"
[[ -f "$XLSX_AUDIT" ]] || fail "xlsx_surface_audit_output_missing"
[[ -f "$AGGREGATE_REGISTRY" ]] || fail "aggregate_definition_registry_missing"
[[ -d "$REPO/configs/metrics" ]] || fail "metric_config_directory_missing"

set +e
python selected_event_consequence_surface_lite.py \
  --selected-action-consequence "$SELECTED_ACTION" \
  --out "$OUT"
SELECTED_EVENT_RC=$?
python eventonly_sequence_consequence_engine_lite.py \
  --selected-action-consequence "$SELECTED_ACTION" \
  --out "$OUT"
SEQUENCE_RC=$?
python aggregate_definition_alignment_lite.py \
  --xlsx-audit "$XLSX_AUDIT" \
  --label-semantics "$PROVIDER_LABELS" \
  --metric-config-dir "$REPO/configs/metrics" \
  --registry "$AGGREGATE_REGISTRY" \
  --output "$AGGREGATE_ALIGNMENT"
AGGREGATE_RC=$?
set -e

[[ "$SELECTED_EVENT_RC" -ne 2 ]] || fail "selected_event_consequence_fail_closed"
[[ "$SEQUENCE_RC" -ne 2 ]] || fail "sequence_consequence_fail_closed"
[[ "$AGGREGATE_RC" -ne 2 ]] || fail "aggregate_alignment_fail_closed"
[[ -f "$SELECTED_EVENT" ]] || fail "selected_event_consequence_output_missing"
[[ -f "$SEQUENCE_CONSEQUENCE" ]] || fail "sequence_consequence_output_missing"
[[ -f "$AGGREGATE_ALIGNMENT" ]] || fail "aggregate_alignment_output_missing"

set +e
python event_label_structural_progression_evidence_lite.py \
  --provider-labels "$PROVIDER_LABELS" \
  --selected-action "$SELECTED_ACTION" \
  --selected-event "$SELECTED_EVENT" \
  --sequence-consequence "$SEQUENCE_CONSEQUENCE" \
  --aggregate-alignment "$AGGREGATE_ALIGNMENT" \
  --out "$OUT" \
  | tee "$OUT/event_label_structural_progression_evidence_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e
[[ -f "$OUTPUT" ]] || fail "progression_evidence_output_missing"

python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" "$HEAD" <<'PY' \
  | tee "$OUT/event_label_structural_progression_evidence_runtime_audit_v1.txt"
import json
import sys

path, actual, expected, rc_text, head = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    payload = json.load(handle)
rc = int(rc_text)
hard_blocks = payload.get("hard_block_hits") or []
complete = rc == 0 and actual == expected and not hard_blocks
passed = complete and (payload.get("module_status") or payload.get("status")) == "PASS"
payload.update({
    "runtime_authority": actual,
    "runtime_authority_equal": actual == expected,
    "runtime_code_head_sha": head,
    "run_rc": rc,
    "active_match_execution_completed": complete,
    "active_match_evidence_pass": passed,
    "runtime_evidence_status": (
        "ACTIVE_MATCH_EVIDENCE_PASS" if passed else
        "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED" if complete else
        "ACTIVE_MATCH_EXECUTION_NOT_COMPLETED"
    ),
    "release_status": "NOT_PRODUCTION",
})
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
print("HPFA EVENT LABEL STRUCTURAL PROGRESSION EVIDENCE ACTIVE_MATCH AUDIT")
for key in (
    "status", "runtime_evidence_status", "release_status", "runtime_code_head_sha",
    "match_surface_binding_id", "evidence_record_count", "verification_status_counts",
    "axis_eligibility_state_counts", "structural_progression_classification_counts",
    "persistence_classification_counts", "progression_metric_gate", "hard_block_hits",
    "review_hits", "active_match_execution_completed", "active_match_evidence_pass",
    "canonical_event_count", "production_release",
):
    print(f"{key}={payload.get(key)}")
PY

{
  echo "product_repo=$REPO"
  echo "branch=$BRANCH"
  echo "head_sha=$HEAD"
  echo "expected_head_sha=$EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_RESOLVED"
  echo "spine_rc=$SPINE_RC"
  echo "selected_event_rc=$SELECTED_EVENT_RC"
  echo "sequence_rc=$SEQUENCE_RC"
  echo "aggregate_rc=$AGGREGATE_RC"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUTPUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/event_label_structural_progression_evidence_result_v1.txt"

python - "$OUT" "$MARKER" "$BUNDLE" "$MANIFEST" "$BUNDLE_SHA" \
  "$BRANCH" "$HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

out, marker, bundle, manifest, bundle_sha = map(Path, sys.argv[1:6])
branch, head, authority, rc_text = sys.argv[6:]
required = (
    "provider_label_value_semantics_lite_v1.json",
    "selected_action_consequence_surface_lite_v1.json",
    "selected_event_consequence_surface_lite_v1.json",
    "eventonly_sequence_consequence_result_v1.json",
    "aggregate_definition_alignment_lite_v1.json",
    "event_label_structural_progression_evidence_lite_v1.json",
    "event_label_structural_progression_evidence_analyst_audit_v1.txt",
    "event_label_structural_progression_evidence_runtime_audit_v1.txt",
    "event_label_structural_progression_evidence_pytest_v1.txt",
)
missing = [name for name in required if not (out / name).is_file()]
if missing:
    raise SystemExit("bundle_required_output_missing:" + ",".join(missing))
cutoff = marker.stat().st_mtime_ns
excluded = {marker.name, bundle.name, manifest.name, bundle_sha.name}
files = sorted(
    (
        path for path in out.iterdir()
        if path.is_file()
        and path.name not in excluded
        and path.suffix.lower() in {".json", ".txt", ".tsv", ".csv", ".log"}
        and path.stat().st_mtime_ns >= cutoff
    ),
    key=lambda path: path.name,
)
names = {path.name for path in files}
stale = [name for name in required if name not in names]
if stale:
    raise SystemExit("bundle_required_output_not_current_run:" + ",".join(stale))

def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

manifest.write_text(
    json.dumps(
        {
            "schema": "HPFA_EVENT_LABEL_STRUCTURAL_PROGRESSION_EVIDENCE_BUNDLE_MANIFEST_V1",
            "branch": branch,
            "runtime_code_head_sha": head,
            "runtime_authority": authority,
            "run_rc": int(rc_text),
            "file_count": len(files),
            "files": [
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in files
            ],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        archive.write(path, arcname=path.name)
    archive.write(manifest, arcname=manifest.name)
bundle_sha.write_text(f"{sha256(bundle)}  {bundle.name}\n", encoding="utf-8")
print(f"bundle={bundle}")
print(f"bundle_file_count={len(files) + 1}")
PY

rm -f "$MARKER"
exit "$RUN_RC"
