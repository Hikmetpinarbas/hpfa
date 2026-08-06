#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/coordinate-frame-precondition-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *) printf 'status=FAIL_CLOSED\nreason=nested_phone_output_directory_rejected\n' >&2; exit 2 ;;
esac

mkdir -p "$OUT"
RUN_MARKER="$OUT/.coordinate_frame_precondition_run_marker_v1"
STATE="$OUT/coordinate_frame_precondition_operator_state_v1.txt"
FAILURE_INVENTORY="$OUT/coordinate_frame_precondition_failure_inventory_v1.txt"
FAILURE_BUNDLE="$OUT/coordinate_frame_precondition_failure_bundle_v1.zip"
SUCCESS_BUNDLE="$OUT/coordinate_frame_precondition_active_match_bundle_v1.zip"
SUCCESS_MANIFEST="$OUT/coordinate_frame_precondition_active_match_bundle_manifest_v1.json"
SUCCESS_SHA="$OUT/coordinate_frame_precondition_manifest_v1.sha256"
: > "$RUN_MARKER"

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

write_inventory() {
  {
    printf 'provider_label_output=%s\n' "$OUT/provider_label_value_semantics_lite_v1.json"
    printf 'provider_label_exists=%s\n' "$([ -s "$OUT/provider_label_value_semantics_lite_v1.json" ] && echo true || echo false)"
    printf 'action_bundle_output=%s\n' "$OUT/semantic_role_action_bundle_candidates_lite_v1.json"
    printf 'action_bundle_exists=%s\n' "$([ -s "$OUT/semantic_role_action_bundle_candidates_lite_v1.json" ] && echo true || echo false)"
    printf 'selected_action_output=%s\n' "$OUT/selected_action_consequence_surface_lite_v1.json"
    printf 'selected_action_exists=%s\n' "$([ -s "$OUT/selected_action_consequence_surface_lite_v1.json" ] && echo true || echo false)"
    printf 'selected_event_output=%s\n' "$OUT/selected_event_consequence_surface_lite_v1.json"
    printf 'selected_event_exists=%s\n' "$([ -s "$OUT/selected_event_consequence_surface_lite_v1.json" ] && echo true || echo false)"
    printf 'runtime_authority=%s\n' "$ACTIVE"
    printf 'canonical_event_count=UNKNOWN\n'
    printf 'production_release=false\n'
  } > "$FAILURE_INVENTORY"
}

make_failure_bundle() {
  python - "$OUT" "$RUN_MARKER" "$FAILURE_BUNDLE" "$STATE" "$FAILURE_INVENTORY" <<'PY'
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

out, marker, bundle, state, inventory = map(Path, sys.argv[1:])
cutoff = marker.stat().st_mtime_ns if marker.exists() else 0
excluded = {marker.name, bundle.name}
allowed = {".json", ".txt", ".log", ".sha256"}
files = [
    path for path in out.iterdir()
    if path.is_file()
    and path.name not in excluded
    and path.suffix.lower() in allowed
    and (path.stat().st_mtime_ns >= cutoff or path in {state, inventory})
]
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(set(files), key=lambda item: item.name):
        archive.write(path, arcname=path.name)
PY
}

fail() {
  local reason="$1"
  write_inventory || true
  {
    printf 'status=FAIL_CLOSED\n'
    printf 'reason=%s\n' "$reason"
    printf 'product_repo=%s\n' "$PRODUCT_REPO"
    printf 'branch=%s\n' "${CURRENT_BRANCH:-UNKNOWN}"
    printf 'runtime_code_head_sha=%s\n' "${CURRENT_HEAD:-UNKNOWN}"
    printf 'expected_branch=%s\n' "$EXPECTED_BRANCH"
    printf 'expected_head_sha=%s\n' "${EXPECTED_HEAD:-UNKNOWN}"
    printf 'runtime_authority=%s\n' "$ACTIVE"
    printf 'upstream_rc=%s\n' "${UPSTREAM_RC:-NOT_RUN}"
    printf 'selected_event_rc=%s\n' "${SELECTED_EVENT_RC:-NOT_RUN}"
    printf 'run_rc=%s\n' "${RUN_RC:-NOT_RUN}"
    printf 'failure_bundle=%s\n' "$FAILURE_BUNDLE"
    printf 'canonical_event_count=UNKNOWN\n'
    printf 'production_release=false\n'
  } > "$STATE" || true
  make_failure_bundle || true
  printf 'status=FAIL_CLOSED\nreason=%s\nfailure_bundle=%s\n' "$reason" "$FAILURE_BUNDLE" >&2
  exit 2
}

[ -d "$PRODUCT_REPO/.git" ] || fail "product_repo_missing_or_not_git"
[ -d "$ACTIVE" ] || fail "active_match_runtime_missing"
[ -d "$EXPECTED_ACTIVE" ] || fail "expected_active_match_runtime_missing"

CURRENT_BRANCH="$(git -C "$PRODUCT_REPO" branch --show-current)"
CURRENT_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD)"
ORIGIN_URL="$(git -C "$PRODUCT_REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"

[ "$ORIGIN_SLUG" = "$EXPECTED_REPO_SLUG" ] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[ "$CURRENT_BRANCH" = "$EXPECTED_BRANCH" ] || fail "branch_mismatch:$CURRENT_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_missing_or_invalid:${EXPECTED_HEAD:-EMPTY}"
EXPECTED_HEAD="${EXPECTED_HEAD,,}"
[ "$CURRENT_HEAD" = "$EXPECTED_HEAD" ] || fail "head_mismatch:$CURRENT_HEAD"
[ -z "$(git -C "$PRODUCT_REPO" status --porcelain --untracked-files=no)" ] || fail "tracked_worktree_dirty"

ACTIVE_RESOLVED="$(cd "$ACTIVE" && pwd -P)"
EXPECTED_ACTIVE_RESOLVED="$(cd "$EXPECTED_ACTIVE" && pwd -P)"
[ "$ACTIVE_RESOLVED" = "$EXPECTED_ACTIVE_RESOLVED" ] || fail "active_match_runtime_authority_mismatch"

cd "$PRODUCT_REPO"
rm -f \
  "$OUT/coordinate_frame_precondition_lite_v1.json" \
  "$OUT/coordinate_frame_precondition_lite_v1.txt" \
  "$OUT/coordinate_frame_precondition_analyst_audit_v1.txt" \
  "$OUT/coordinate_frame_precondition_pytest_v1.txt" \
  "$OUT/coordinate_frame_precondition_active_match_v1.txt" \
  "$OUT/coordinate_frame_precondition_upstream_refresh_v1.txt" \
  "$OUT/coordinate_frame_precondition_selected_event_refresh_v1.txt" \
  "$STATE" "$FAILURE_INVENTORY" "$FAILURE_BUNDLE" \
  "$SUCCESS_BUNDLE" "$SUCCESS_MANIFEST" "$SUCCESS_SHA"

set +e
HPFA_REPO="$PRODUCT_REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_RESOLVED" \
HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_RESOLVED" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
HPFA_PHONE_OUTPUT="$OUT" \
  bash "$PRODUCT_REPO/tools/run_active_match_context_slicer_v1.sh" 2>&1 \
  | tee "$OUT/coordinate_frame_precondition_upstream_refresh_v1.txt"
UPSTREAM_RC="${PIPESTATUS[0]}"
set -e
[ "$UPSTREAM_RC" -eq 0 ] || fail "context_spine_failed:$UPSTREAM_RC"

PROVIDER="$OUT/provider_label_value_semantics_lite_v1.json"
BUNDLES="$OUT/semantic_role_action_bundle_candidates_lite_v1.json"
SELECTED_ACTION="$OUT/selected_action_consequence_surface_lite_v1.json"
SELECTED_EVENT="$OUT/selected_event_consequence_surface_lite_v1.json"

[ -s "$PROVIDER" ] || fail "provider_label_output_missing_after_upstream_refresh"
[ -s "$BUNDLES" ] || fail "action_bundle_output_missing_after_upstream_refresh"
[ -s "$SELECTED_ACTION" ] || fail "selected_action_output_missing_after_upstream_refresh"

set +e
python selected_event_consequence_surface_lite.py \
  --selected-action-consequence "$SELECTED_ACTION" \
  --out "$OUT" 2>&1 \
  | tee "$OUT/coordinate_frame_precondition_selected_event_refresh_v1.txt"
SELECTED_EVENT_RC="${PIPESTATUS[0]}"
set -e
[ "$SELECTED_EVENT_RC" -ne 2 ] || fail "selected_event_consequence_fail_closed"
[ -s "$SELECTED_EVENT" ] || fail "selected_event_output_missing_after_refresh"

if ! python - "$RUN_MARKER" "$PROVIDER" "$BUNDLES" "$SELECTED_ACTION" "$SELECTED_EVENT" <<'PY'
import sys
from pathlib import Path

marker = Path(sys.argv[1]).stat().st_mtime_ns
stale = [
    Path(value).name
    for value in sys.argv[2:]
    if Path(value).stat().st_mtime_ns < marker
]
if stale:
    raise SystemExit("required_input_not_current_run:" + ",".join(stale))
PY
then
  fail "required_input_not_current_run"
fi

PYTEST_OUT="$OUT/coordinate_frame_precondition_pytest_v1.txt"
python -m pytest -q \
  hpfa/modules/core/coordinate_frame_precondition_lite/tests \
  | tee "$PYTEST_OUT"

set +e
python coordinate_frame_precondition_lite.py \
  --provider-labels "$PROVIDER" \
  --action-bundles "$BUNDLES" \
  --selected-event "$SELECTED_EVENT" \
  --out "$OUT"
RUN_RC="$?"
set -e

[ -s "$OUT/coordinate_frame_precondition_lite_v1.json" ] || fail "coordinate_frame_precondition_output_missing"
[ "$RUN_RC" -ne 2 ] || fail "coordinate_frame_precondition_fail_closed"

{
  printf 'status=COMPLETED\n'
  printf 'runtime_authority=%s\n' "$ACTIVE_RESOLVED"
  printf 'product_repo=%s\n' "$PRODUCT_REPO"
  printf 'origin_url=%s\n' "$ORIGIN_URL"
  printf 'branch=%s\n' "$CURRENT_BRANCH"
  printf 'runtime_code_head_sha=%s\n' "$CURRENT_HEAD"
  printf 'expected_head_sha=%s\n' "$EXPECTED_HEAD"
  printf 'upstream_rc=%s\n' "$UPSTREAM_RC"
  printf 'selected_event_rc=%s\n' "$SELECTED_EVENT_RC"
  printf 'run_rc=%s\n' "$RUN_RC"
  printf 'canonical_event_count=UNKNOWN\n'
  printf 'production_release=false\n'
} > "$STATE"

python - "$OUT" "$RUN_MARKER" "$SUCCESS_BUNDLE" "$SUCCESS_MANIFEST" "$SUCCESS_SHA" "$CURRENT_BRANCH" "$CURRENT_HEAD" "$ACTIVE_RESOLVED" "$RUN_RC" <<'PY'
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
    sha_text,
    branch,
    head,
    authority,
    run_rc_text,
) = sys.argv[1:]

out = Path(out_text)
marker = Path(marker_text)
bundle = Path(bundle_text)
manifest = Path(manifest_text)
sha_file = Path(sha_text)
run_rc = int(run_rc_text)

required = (
    "provider_label_value_semantics_lite_v1.json",
    "semantic_role_action_bundle_candidates_lite_v1.json",
    "selected_action_consequence_surface_lite_v1.json",
    "selected_event_consequence_surface_lite_v1.json",
    "coordinate_frame_precondition_lite_v1.json",
    "coordinate_frame_precondition_lite_v1.txt",
    "coordinate_frame_precondition_analyst_audit_v1.txt",
    "coordinate_frame_precondition_pytest_v1.txt",
    "coordinate_frame_precondition_operator_state_v1.txt",
)
missing = [name for name in required if not (out / name).is_file()]
if missing:
    raise SystemExit("bundle_required_output_missing:" + ",".join(missing))

cutoff = marker.stat().st_mtime_ns
excluded = {marker.name, bundle.name, manifest.name, sha_file.name}
allowed = {".json", ".txt", ".tsv", ".csv", ".log"}
files = sorted(
    (
        path for path in out.iterdir()
        if path.is_file()
        and path.name not in excluded
        and path.suffix.lower() in allowed
        and path.stat().st_mtime_ns >= cutoff
    ),
    key=lambda path: path.name,
)
names = {path.name for path in files}
stale = [name for name in required if name not in names]
if stale:
    raise SystemExit("bundle_required_output_not_current_run:" + ",".join(stale))

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

payload = {
    "schema": "hpfa.coordinate_frame_precondition_active_match_bundle_manifest",
    "version": "1.1.0",
    "status": "BUNDLE_CREATED",
    "branch": branch,
    "runtime_code_head_sha": head,
    "runtime_authority": authority,
    "run_rc": run_rc,
    "included_file_count": len(files),
    "files": [
        {"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ],
    "canonical_event_count": "UNKNOWN",
    "production_release": False,
}
manifest.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        archive.write(path, arcname=path.name)
    archive.write(manifest, arcname=manifest.name)
sha_file.write_text(f"{sha256(bundle)}  {bundle.name}\n", encoding="utf-8")
print(f"bundle={bundle}")
print(f"bundle_file_count={len(files) + 1}")
PY

rm -f "$RUN_MARKER"
printf 'bundle=%s\n' "$SUCCESS_BUNDLE"
exit "$RUN_RC"
