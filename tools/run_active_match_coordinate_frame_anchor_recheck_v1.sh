#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/coordinate-frame-anchor-recheck-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *) printf 'status=FAIL_CLOSED\nreason=nested_phone_output_directory_rejected\n' >&2; exit 2 ;;
esac
mkdir -p "$OUT"

normalize_origin() {
  local origin="${1:-}"
  origin="${origin%/}"; origin="${origin%.git}"
  origin="${origin#https://github.com/}"; origin="${origin#http://github.com/}"
  origin="${origin#git@github.com:}"; origin="${origin#ssh://git@github.com/}"
  printf '%s\n' "${origin,,}"
}

fail() {
  local reason="$1"
  printf 'status=FAIL_CLOSED\nreason=%s\ncanonical_event_count=UNKNOWN\nproduction_release=false\n' "$reason" >&2
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

set +e
HPFA_PRODUCT_REPO="$PRODUCT_REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_RESOLVED" \
HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_RESOLVED" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
HPFA_PHONE_OUTPUT="$OUT" \
  bash "$PRODUCT_REPO/tools/run_active_match_provider_coordinate_attachment_semantics_v1.sh" \
  > "$OUT/coordinate_frame_anchor_recheck_upstream_refresh_v1.txt" 2>&1
UPSTREAM_RC=$?
set -e
[ "$UPSTREAM_RC" -eq 0 ] || fail "provider_coordinate_attachment_upstream_failed:$UPSTREAM_RC"

FRAME="$OUT/coordinate_frame_precondition_lite_v1.json"
ATTACHMENT="$OUT/provider_coordinate_attachment_semantics_lite_v1.json"
[ -s "$FRAME" ] || fail "required_upstream_output_missing:coordinate_frame_precondition_lite_v1.json"
[ -s "$ATTACHMENT" ] || fail "required_upstream_output_missing:provider_coordinate_attachment_semantics_lite_v1.json"

PYTEST_OUT="$OUT/coordinate_frame_anchor_recheck_pytest_v1.txt"
python -m pytest -q hpfa/modules/core/coordinate_frame_anchor_recheck_lite/tests \
  | tee "$PYTEST_OUT"

ACTIVE_LOG="$OUT/coordinate_frame_anchor_recheck_active_match_v1.txt"
set +e
python coordinate_frame_anchor_recheck_lite.py \
  --coordinate-frame "$FRAME" \
  --coordinate-attachment "$ATTACHMENT" \
  --out "$OUT" \
  | tee "$ACTIVE_LOG"
RUN_RC="${PIPESTATUS[0]}"
set -e
[ "$RUN_RC" -ne 2 ] || fail "coordinate_frame_anchor_recheck_fail_closed"

OUTPUT="$OUT/coordinate_frame_anchor_recheck_lite_v1.json"
[ -s "$OUTPUT" ] || fail "coordinate_frame_anchor_recheck_output_missing"

python - "$OUTPUT" "$ACTIVE_RESOLVED" "$CURRENT_HEAD" <<'PY'
import json, sys
from pathlib import Path
path, authority, head = sys.argv[1:]
payload = json.loads(Path(path).read_text(encoding="utf-8"))
payload["runtime_authority"] = authority
payload["runtime_code_head_sha"] = head
payload["active_match_execution_completed"] = True
payload["runtime_evidence_status"] = (
    "ACTIVE_MATCH_EVIDENCE_PASS"
    if payload.get("status") == "PASS"
    else "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
)
payload["release_status"] = "NOT_PRODUCTION"
Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

OPERATOR_STATE="$OUT/coordinate_frame_anchor_recheck_operator_state_v1.txt"
{
  printf 'status=COMPLETED\n'
  printf 'runtime_authority=%s\n' "$ACTIVE_RESOLVED"
  printf 'product_repo=%s\n' "$PRODUCT_REPO"
  printf 'branch=%s\n' "$CURRENT_BRANCH"
  printf 'runtime_code_head_sha=%s\n' "$CURRENT_HEAD"
  printf 'expected_head_sha=%s\n' "$EXPECTED_HEAD"
  printf 'upstream_rc=%s\n' "$UPSTREAM_RC"
  printf 'run_rc=%s\n' "$RUN_RC"
  printf 'canonical_event_count=UNKNOWN\n'
  printf 'production_release=false\n'
} > "$OPERATOR_STATE"

BUNDLE="$OUT/coordinate_frame_anchor_recheck_active_match_bundle_v1.zip"
MANIFEST="$OUT/coordinate_frame_anchor_recheck_manifest_v1.sha256"
rm -f "$BUNDLE" "$MANIFEST"
python - "$OUT" "$BUNDLE" "$MANIFEST" <<'PY'
from __future__ import annotations
import hashlib, sys, zipfile
from pathlib import Path
out, bundle, manifest = map(Path, sys.argv[1:])
names = [
    "coordinate_frame_precondition_lite_v1.json",
    "provider_coordinate_attachment_semantics_lite_v1.json",
    "coordinate_frame_anchor_recheck_lite_v1.json",
    "coordinate_frame_anchor_recheck_lite_v1.txt",
    "coordinate_frame_anchor_recheck_analyst_audit_v1.txt",
    "coordinate_frame_anchor_recheck_pytest_v1.txt",
    "coordinate_frame_anchor_recheck_active_match_v1.txt",
    "coordinate_frame_anchor_recheck_upstream_refresh_v1.txt",
    "coordinate_frame_anchor_recheck_operator_state_v1.txt",
]
missing = [name for name in names if not (out / name).is_file()]
if missing:
    raise SystemExit("bundle_required_output_missing:" + ",".join(missing))
lines=[]
for name in names:
    data=(out/name).read_bytes()
    lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
manifest.write_text("\n".join(lines)+"\n", encoding="utf-8")
with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name in names:
        archive.write(out/name, arcname=name)
    archive.write(manifest, arcname=manifest.name)
PY

printf 'status=COMPLETED\nbundle=%s\n' "$BUNDLE"
