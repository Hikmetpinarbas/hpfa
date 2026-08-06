#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/coordinate-frame-precondition-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"

fail() {
  printf 'status=FAIL_CLOSED\nreason=%s\n' "$1" >&2
  exit 2
}

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *) fail "nested_phone_output_directory_rejected" ;;
esac

[ -d "$PRODUCT_REPO/.git" ] || fail "product_repo_missing_or_not_git"
[ -d "$ACTIVE" ] || fail "active_match_runtime_missing"
cd "$PRODUCT_REPO"

CURRENT_BRANCH="$(git branch --show-current)"
CURRENT_HEAD="$(git rev-parse HEAD)"
[ "$CURRENT_BRANCH" = "$EXPECTED_BRANCH" ] || fail "branch_mismatch:$CURRENT_BRANCH"
[ -n "$EXPECTED_HEAD" ] || fail "expected_head_missing"
[ "$CURRENT_HEAD" = "$EXPECTED_HEAD" ] || fail "head_mismatch:$CURRENT_HEAD"
[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "tracked_worktree_dirty"

mkdir -p "$OUT"
PROVIDER="$OUT/provider_label_value_semantics_lite_v1.json"
BUNDLES="$OUT/semantic_role_action_bundle_candidates_lite_v1.json"
SELECTED_EVENT="$OUT/selected_event_consequence_surface_lite_v1.json"

[ -s "$PROVIDER" ] || fail "provider_label_output_missing"
[ -s "$BUNDLES" ] || fail "action_bundle_output_missing"
[ -s "$SELECTED_EVENT" ] || fail "selected_event_output_missing"

PYTEST_OUT="$OUT/coordinate_frame_precondition_pytest_v1.txt"
python -m pytest -q \
  hpfa/modules/core/coordinate_frame_precondition_lite/tests/test_coordinate_frame_precondition.py \
  | tee "$PYTEST_OUT"

python coordinate_frame_precondition_lite.py \
  --provider-labels "$PROVIDER" \
  --action-bundles "$BUNDLES" \
  --selected-event "$SELECTED_EVENT" \
  --out "$OUT"

STATE="$OUT/coordinate_frame_precondition_active_match_v1.txt"
{
  printf 'runtime_authority=%s\n' "$ACTIVE"
  printf 'product_repo=%s\n' "$PRODUCT_REPO"
  printf 'branch=%s\n' "$CURRENT_BRANCH"
  printf 'runtime_code_head_sha=%s\n' "$CURRENT_HEAD"
  printf 'run_rc=0\n'
  printf 'canonical_event_count=UNKNOWN\n'
  printf 'production_release=false\n'
} > "$STATE"

MANIFEST="$OUT/coordinate_frame_precondition_manifest_v1.sha256"
sha256sum \
  "$OUT/coordinate_frame_precondition_lite_v1.json" \
  "$OUT/coordinate_frame_precondition_lite_v1.txt" \
  "$OUT/coordinate_frame_precondition_analyst_audit_v1.txt" \
  "$PYTEST_OUT" \
  "$STATE" > "$MANIFEST"

BUNDLE="$OUT/coordinate_frame_precondition_active_match_bundle_v1.zip"
rm -f "$BUNDLE"
(
  cd "$OUT"
  zip -q "$(basename "$BUNDLE")" \
    coordinate_frame_precondition_lite_v1.json \
    coordinate_frame_precondition_lite_v1.txt \
    coordinate_frame_precondition_analyst_audit_v1.txt \
    coordinate_frame_precondition_pytest_v1.txt \
    coordinate_frame_precondition_active_match_v1.txt \
    coordinate_frame_precondition_manifest_v1.sha256
)
printf 'bundle=%s\n' "$BUNDLE"
