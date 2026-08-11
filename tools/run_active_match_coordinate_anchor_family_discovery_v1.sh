#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hpfa_claim_integrity/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/coordinate-anchor-family-discovery-v1}"
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
  printf 'status=FAIL_CLOSED\nreason=%s\ncanonical_event_count=UNKNOWN\nproduction_release=false\n' "$reason" \
    | tee "$OUT/coordinate_anchor_family_discovery_operator_state_v1.txt" >&2
  exit 2
}

[ -d "$PRODUCT_REPO/.git" ] || fail "product_repo_missing_or_not_git"
[ -d "$ACTIVE" ] || fail "active_match_runtime_missing"
[ -d "$EXPECTED_ACTIVE" ] || fail "expected_active_match_runtime_missing"

CURRENT_BRANCH="$(git -C "$PRODUCT_REPO" branch --show-current)"
CURRENT_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD)"
ORIGIN_URL="$(git -C "$PRODUCT_REPO" remote get-url origin 2>/dev/null || true)"
[ "$(normalize_origin "$ORIGIN_URL")" = "$EXPECTED_REPO_SLUG" ] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
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
  "$OUT/coordinate_anchor_family_discovery_v1.json" \
  "$OUT/coordinate_anchor_family_discovery_v1.txt" \
  "$OUT/coordinate_anchor_family_discovery_analyst_audit_v1.txt" \
  "$OUT/coordinate_anchor_family_discovery_pytest_v1.txt" \
  "$OUT/coordinate_anchor_family_discovery_active_match_v1.txt" \
  "$OUT/coordinate_anchor_family_discovery_operator_state_v1.txt" \
  "$OUT/coordinate_anchor_family_discovery_active_match_bundle_v1.zip"

set +e
HPFA_PRODUCT_REPO="$PRODUCT_REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_RESOLVED" \
HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_RESOLVED" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
HPFA_PHONE_OUTPUT="$OUT" \
  bash tools/run_active_match_coordinate_frame_precondition_v1.sh \
  > "$OUT/coordinate_anchor_family_discovery_upstream_refresh_v1.txt" 2>&1
UPSTREAM_RC=$?
set -e
[ "$UPSTREAM_RC" -eq 0 ] || fail "coordinate_frame_upstream_refresh_failed:$UPSTREAM_RC"

PROVIDER="$OUT/provider_label_value_semantics_lite_v1.json"
BUNDLES="$OUT/semantic_role_action_bundle_candidates_lite_v1.json"
FRAME="$OUT/coordinate_frame_precondition_lite_v1.json"
[ -s "$PROVIDER" ] || fail "provider_label_output_missing"
[ -s "$BUNDLES" ] || fail "action_bundle_output_missing"
[ -s "$FRAME" ] || fail "coordinate_frame_output_missing"

python -m pytest -q tools/tests/test_coordinate_anchor_family_discovery_v1.py \
  | tee "$OUT/coordinate_anchor_family_discovery_pytest_v1.txt"

set +e
python tools/coordinate_anchor_family_discovery_v1.py \
  --provider-labels "$PROVIDER" \
  --action-bundles "$BUNDLES" \
  --coordinate-frame "$FRAME" \
  --out "$OUT" \
  | tee "$OUT/coordinate_anchor_family_discovery_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e
[ "$RUN_RC" -eq 0 ] || fail "coordinate_anchor_family_discovery_failed:$RUN_RC"

OUTPUT="$OUT/coordinate_anchor_family_discovery_v1.json"
[ -s "$OUTPUT" ] || fail "coordinate_anchor_family_discovery_output_missing"

python - "$OUTPUT" "$ACTIVE_RESOLVED" "$CURRENT_HEAD" <<'PY'
import json, sys
from pathlib import Path
path, authority, head = sys.argv[1:]
payload = json.loads(Path(path).read_text(encoding="utf-8"))
if payload.get("status") == "FAIL_CLOSED":
    raise SystemExit("discovery_fail_closed")
payload["runtime_authority"] = authority
payload["runtime_code_head_sha"] = head
payload["active_match_execution_completed"] = True
payload["runtime_evidence_status"] = "ACTIVE_MATCH_EVIDENCE_PASS"
payload["release_status"] = "DISCOVERY_PASS_PLAN_ONLY"
payload["canonical_event_count"] = "UNKNOWN"
payload["production_release"] = False
Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

{
  printf 'status=COMPLETED\n'
  printf 'runtime_authority=%s\n' "$ACTIVE_RESOLVED"
  printf 'branch=%s\n' "$CURRENT_BRANCH"
  printf 'runtime_code_head_sha=%s\n' "$CURRENT_HEAD"
  printf 'upstream_rc=%s\n' "$UPSTREAM_RC"
  printf 'run_rc=%s\n' "$RUN_RC"
  printf 'canonical_event_count=UNKNOWN\n'
  printf 'production_release=false\n'
} > "$OUT/coordinate_anchor_family_discovery_operator_state_v1.txt"

python - "$OUT" <<'PY'
import sys, zipfile
from pathlib import Path
out = Path(sys.argv[1])
names = [
    "provider_label_value_semantics_lite_v1.json",
    "semantic_role_action_bundle_candidates_lite_v1.json",
    "coordinate_frame_precondition_lite_v1.json",
    "coordinate_anchor_family_discovery_v1.json",
    "coordinate_anchor_family_discovery_v1.txt",
    "coordinate_anchor_family_discovery_analyst_audit_v1.txt",
    "coordinate_anchor_family_discovery_pytest_v1.txt",
    "coordinate_anchor_family_discovery_active_match_v1.txt",
    "coordinate_anchor_family_discovery_upstream_refresh_v1.txt",
    "coordinate_anchor_family_discovery_operator_state_v1.txt",
]
missing = [name for name in names if not (out / name).is_file()]
if missing:
    raise SystemExit("bundle_required_output_missing:" + ",".join(missing))
bundle = out / "coordinate_anchor_family_discovery_active_match_bundle_v1.zip"
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in names:
        z.write(out / name, arcname=name)
PY

printf 'status=COMPLETED\nbundle=%s\n' "$OUT/coordinate_anchor_family_discovery_active_match_bundle_v1.zip"
