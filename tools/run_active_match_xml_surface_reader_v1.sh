#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 2
}

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

identity_matches() {
  local actual_branch="$1"
  local actual_head="$2"
  local expected_branch="$3"
  local expected_head="$4"
  [[ -n "$expected_branch" && -n "$expected_head" ]] || return 1
  [[ "$actual_branch" == "$expected_branch" ]] || return 1
  [[ "$actual_head" == "$expected_head" ]] || return 1
}

if [[ "${1:-}" == "--self-test-execution-identity-guard" ]]; then
  identity_matches \
    "integration/foundation-tranche-a-v1" \
    "abc123" \
    "integration/foundation-tranche-a-v1" \
    "abc123" \
    || fail "self_test_exact_identity_rejected"

  if identity_matches \
    "wrong-branch" \
    "abc123" \
    "integration/foundation-tranche-a-v1" \
    "abc123"; then
    fail "self_test_wrong_branch_accepted"
  fi

  if identity_matches \
    "integration/foundation-tranche-a-v1" \
    "wrong-head" \
    "integration/foundation-tranche-a-v1" \
    "abc123"; then
    fail "self_test_wrong_head_accepted"
  fi

  echo "xml_execution_identity_guard_self_test=PASS"
  exit 0
fi

[[ -n "$EXPECTED_BRANCH" ]] || \
  fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || \
  fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"

[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || \
  fail "product_repo_origin_mismatch:$ORIGIN_URL"

identity_matches \
  "$ACTUAL_BRANCH" \
  "$ACTUAL_HEAD" \
  "$EXPECTED_BRANCH" \
  "$EXPECTED_HEAD" \
  || fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"

[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || \
  fail "tracked_worktree_not_clean:$REPO"

case "$(cd "$ACTIVE_MATCH" && pwd -P)" in
  */runtime/active_single_match/current) ;;
  *) fail "active_match_runtime_authority_mismatch:$ACTIVE_MATCH" ;;
esac

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

mkdir -p "$OUT"
cd "$REPO"

rm -f \
  "$OUT/xml_surface_audit_lite_v1.json" \
  "$OUT/xml_surface_audit_lite_v1.txt" \
  "$OUT/xml_surface_analyst_audit_lite_v1.txt"

python -m py_compile \
  hpfa/modules/core/xml_surface_reader_lite/src/xml_common.py \
  hpfa/modules/core/xml_surface_reader_lite/src/xml_structure.py \
  hpfa/modules/core/xml_surface_reader_lite/src/xml_rows.py \
  hpfa/modules/core/xml_surface_reader_lite/src/xml_surface_reader.py \
  hpfa/modules/core/xml_surface_reader_lite/tests/test_xml_surface_reader.py \
  xml_surface_reader_lite.py

python -m pytest -q hpfa/modules/core/xml_surface_reader_lite/tests \
  | tee "$OUT/xml_surface_reader_pytest_v1.txt"

# Fresh upstream inventory on this exact integration head.
HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_multiformat_inventory_v1.sh" \
  | tee "$OUT/xml_surface_reader_inventory_refresh_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
[[ -f "$INVENTORY" ]] || fail "fresh_inventory_output_missing:$INVENTORY"

set +e
python xml_surface_reader_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --inventory "$INVENTORY" \
  --out "$OUT" \
  | tee "$OUT/xml_surface_reader_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

if [[ -f "$OUT/xml_surface_audit_lite_v1.json" ]]; then
  python - "$OUT/xml_surface_audit_lite_v1.json" <<'PY' \
    | tee "$OUT/xml_surface_reader_analyst_audit_v1.txt"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print("HPFA XML SURFACE READER ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "xml_file_count",
    "hard_block_hits",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")

for file_row in payload.get("files", []):
    structure = file_row.get("xml_structure") or {}
    print(
        f"file={file_row.get('relative_path')} "
        f"status={file_row.get('status')} "
        f"root={structure.get('root_tag')} "
        f"row_tag={file_row.get('selected_row_tag_candidate')} "
        f"row_candidates={file_row.get('row_candidate_count')} "
        f"field_paths={file_row.get('field_path_count')} "
        f"row_shapes={file_row.get('row_shape_count')} "
        f"duplicate_rows={file_row.get('exact_duplicate_row_candidate_count')} "
        f"hard_blocks={file_row.get('hard_block_hits')} "
        f"warnings={file_row.get('parse_warnings')}"
    )
PY
else
  printf 'xml_surface_audit_output_missing\n' \
    | tee "$OUT/xml_surface_reader_analyst_audit_v1.txt"
fi

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_branch=$EXPECTED_BRANCH"
  echo "expected_head=$EXPECTED_HEAD"
  echo "upstream_inventory_refresh=PASS"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/xml_surface_audit_lite_v1.json"
  echo "summary_output=$OUT/xml_surface_audit_lite_v1.txt"
  echo "analyst_output=$OUT/xml_surface_analyst_audit_lite_v1.txt"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/xml_surface_reader_result_v1.txt"

exit "$RUN_RC"
