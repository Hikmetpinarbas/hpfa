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

  echo "xlsx_execution_identity_guard_self_test=PASS"
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

[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
identity_matches \
  "$ACTUAL_BRANCH" \
  "$ACTUAL_HEAD" \
  "$EXPECTED_BRANCH" \
  "$EXPECTED_HEAD" \
  || fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

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
  "$OUT/xlsx_surface_audit_lite_v1.json" \
  "$OUT/xlsx_surface_audit_lite_v1.txt" \
  "$OUT/xlsx_surface_analyst_audit_lite_v1.txt"

python -m py_compile \
  hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader.py \
  hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_runtime_guard.py \
  hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_header_semantics.py \
  hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_surface_reader.py \
  hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_runtime_guard.py \
  hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_header_semantics.py \
  xlsx_surface_reader_lite.py

python -m pytest -q \
  hpfa/modules/core/xlsx_surface_reader_lite/tests \
  | tee "$OUT/xlsx_surface_reader_pytest_v1.txt"

# Refresh upstream inventory on this exact integration head.
HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_multiformat_inventory_v1.sh" \
  | tee "$OUT/xlsx_surface_reader_inventory_refresh_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
[[ -f "$INVENTORY" ]] || fail "fresh_inventory_output_missing:$INVENTORY"

set +e
python xlsx_surface_reader_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --inventory "$INVENTORY" \
  --out "$OUT" \
  | tee "$OUT/xlsx_surface_reader_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

if [[ -f "$OUT/xlsx_surface_audit_lite_v1.json" ]]; then
  python - "$OUT/xlsx_surface_audit_lite_v1.json" <<'PY' \
    | tee "$OUT/xlsx_surface_reader_analyst_audit_v1.txt"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print("HPFA XLSX SURFACE READER ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "xlsx_file_count",
    "hard_block_hits",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
for file_row in payload.get("files", []):
    print(
        f"file={file_row.get('relative_path')} "
        f"status={file_row.get('status')} "
        f"sheet_count={file_row.get('sheet_count')} "
        f"hard_blocks={file_row.get('hard_block_hits')}"
    )
    for sheet in file_row.get("sheets", []):
        print(
            f"sheet={sheet.get('sheet_name')} "
            f"state={sheet.get('sheet_state')} "
            f"status={sheet.get('status')} "
            f"rows={sheet.get('surface_row_count')} "
            f"columns={sheet.get('visible_column_count')} "
            f"metric_labels={len(sheet.get('metric_inventory', []))} "
            f"duplicate_columns={len(sheet.get('duplicate_column_names', []))} "
            f"hard_blocks={sheet.get('hard_block_hits')}"
        )
PY
else
  printf 'xlsx_surface_audit_output_missing\n' \
    | tee "$OUT/xlsx_surface_reader_analyst_audit_v1.txt"
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
  echo "main_output=$OUT/xlsx_surface_audit_lite_v1.json"
  echo "summary_output=$OUT/xlsx_surface_audit_lite_v1.txt"
  echo "analyst_output=$OUT/xlsx_surface_analyst_audit_lite_v1.txt"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/xlsx_surface_reader_result_v1.txt"

exit "$RUN_RC"
