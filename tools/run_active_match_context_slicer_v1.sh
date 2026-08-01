#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/match-context-slicer-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

BUNDLE_NAME="match_context_slicer_active_match_bundle_v1.zip"
MANIFEST_NAME="match_context_slicer_active_match_bundle_manifest_v1.json"
BUNDLE_SHA_NAME="match_context_slicer_active_match_bundle_v1.sha256"
RUN_MARKER_NAME=".match_context_slicer_bundle_run_marker_v1"

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

BUNDLE="$OUT/$BUNDLE_NAME"
MANIFEST="$OUT/$MANIFEST_NAME"
BUNDLE_SHA="$OUT/$BUNDLE_SHA_NAME"
RUN_MARKER="$OUT/$RUN_MARKER_NAME"

rm -f \
  "$OUT/match_context_slicer_lite_v1.json" \
  "$OUT/match_context_slicer_lite_v1.txt" \
  "$OUT/match_context_slicer_analyst_audit_v1.txt" \
  "$OUT/match_context_slicer_runtime_audit_v1.txt" \
  "$OUT/match_context_slicer_result_v1.txt" \
  "$OUT/match_context_slicer_pytest_v1.txt" \
  "$OUT/match_context_slicer_active_match_v1.txt" \
  "$BUNDLE" \
  "$MANIFEST" \
  "$BUNDLE_SHA" \
  "$RUN_MARKER"

: > "$RUN_MARKER"

python -m py_compile \
  match_context_slicer_lite.py \
  hpfa/modules/core/match_context_slicer_lite/src/match_context_slicer.py
python -m pytest -q \
  hpfa/modules/core/match_context_slicer_lite/tests \
  | tee "$OUT/match_context_slicer_pytest_v1.txt"

set +e
HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_MATCH" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
  bash "$REPO/tools/run_active_match_phase_aware_sequence_refinement_v1.sh"
UPSTREAM_RC="$?"
set -e
[[ "$UPSTREAM_RC" -eq 0 ]] || fail "phase_refinement_spine_failed:$UPSTREAM_RC"

ACTION_INPUT="$OUT/selected_action_consequence_surface_lite_v1.json"
PHASE_INPUT="$OUT/event_derived_phase_state_lite_v1.json"
REFINEMENT_INPUT="$OUT/phase_aware_sequence_refinement_lite_v1.json"
[[ -f "$ACTION_INPUT" ]] || fail "selected_action_output_missing"
[[ -f "$PHASE_INPUT" ]] || fail "event_derived_phase_output_missing"
[[ -f "$REFINEMENT_INPUT" ]] || fail "phase_refinement_output_missing"

set +e
python match_context_slicer_lite.py \
  --selected-action-consequence "$ACTION_INPUT" \
  --event-derived-phase "$PHASE_INPUT" \
  --phase-refinement "$REFINEMENT_INPUT" \
  --out "$OUT" \
  | tee "$OUT/match_context_slicer_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

OUTPUT="$OUT/match_context_slicer_lite_v1.json"
[[ -f "$OUTPUT" ]] || fail "match_context_slicer_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" "$ACTUAL_HEAD" <<'PY' \
  | tee "$OUT/match_context_slicer_runtime_audit_v1.txt"
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

print("HPFA MATCH CONTEXT SLICER ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "runtime_evidence_status",
    "release_status",
    "runtime_code_head_sha",
    "match_surface_binding_id",
    "time_axis_candidate",
    "source_selected_action_node_count",
    "source_event_derived_phase_segment_count",
    "source_phase_refinement_decision_count",
    "goal_context_candidate_count",
    "match_context_slice_count",
    "micro_action_overlay_context_slice_count",
    "separate_phase_display_suppressed_count",
    "source_phase_segments_preserved",
    "team_relative_score_state_candidate_counts",
    "same_time_goal_context_review_count",
    "card_state_status",
    "lineup_state_status",
    "hard_block_hits",
    "review_hits",
    "active_match_execution_completed",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
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
} | tee "$OUT/match_context_slicer_result_v1.txt"

python - \
  "$OUT" \
  "$RUN_MARKER" \
  "$BUNDLE" \
  "$MANIFEST" \
  "$BUNDLE_SHA" \
  "$ACTUAL_BRANCH" \
  "$ACTUAL_HEAD" \
  "$ACTIVE_RESOLVED" \
  "$RUN_RC" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

(
    out_text,
    marker_text,
    bundle_text,
    manifest_text,
    bundle_sha_text,
    branch,
    runtime_head,
    runtime_authority,
    run_rc_text,
) = sys.argv[1:]

out = Path(out_text)
marker = Path(marker_text)
bundle = Path(bundle_text)
manifest = Path(manifest_text)
bundle_sha = Path(bundle_sha_text)
run_rc = int(run_rc_text)

required = (
    "selected_action_consequence_surface_lite_v1.json",
    "event_derived_phase_state_lite_v1.json",
    "phase_aware_sequence_refinement_lite_v1.json",
    "match_context_slicer_lite_v1.json",
)
missing = [name for name in required if not (out / name).is_file()]
if missing:
    raise SystemExit("bundle_required_output_missing:" + ",".join(missing))

marker_mtime_ns = marker.stat().st_mtime_ns
allowed_suffixes = {".json", ".txt", ".tsv", ".csv", ".log"}
excluded_names = {
    marker.name,
    bundle.name,
    manifest.name,
    bundle_sha.name,
}

candidates = sorted(
    (
        path
        for path in out.iterdir()
        if path.is_file()
        and path.name not in excluded_names
        and path.suffix.lower() in allowed_suffixes
        and path.stat().st_mtime_ns >= marker_mtime_ns
    ),
    key=lambda path: path.name,
)

candidate_names = {path.name for path in candidates}
missing_from_current_run = [name for name in required if name not in candidate_names]
if missing_from_current_run:
    raise SystemExit(
        "bundle_required_output_not_current_run:"
        + ",".join(missing_from_current_run)
    )

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

files = [
    {
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    for path in candidates
]

payload = {
    "schema": "hpfa.match_context_slicer_active_match_bundle_manifest",
    "version": "1.0.0",
    "status": "BUNDLE_CREATED",
    "branch": branch,
    "runtime_code_head_sha": runtime_head,
    "runtime_authority": runtime_authority,
    "run_rc": run_rc,
    "included_file_count": len(files),
    "files": files,
    "canonical_event_count": "UNKNOWN",
    "production_release": False,
}
manifest.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

with zipfile.ZipFile(
    bundle,
    mode="w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=9,
) as archive:
    for path in candidates:
        archive.write(path, arcname=path.name)
    archive.write(manifest, arcname=manifest.name)

bundle_digest = sha256(bundle)
bundle_sha.write_text(
    f"{bundle_digest}  {bundle.name}\n",
    encoding="utf-8",
)

print("HPFA ACTIVE_MATCH BUNDLE")
print(f"bundle_file={bundle}")
print(f"bundle_manifest={manifest}")
print(f"bundle_sha256={bundle_digest}")
print(f"included_file_count={len(files)}")
print("bundle_internal_paths=FLAT")
PY

rm -f "$RUN_MARKER"

exit "$RUN_RC"
