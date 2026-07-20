#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="cross-format-reconciliation-lite-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin() {
  local origin="${1:-}"
  origin="${origin%/}"; origin="${origin%.git}"
  origin="${origin#https://github.com/}"; origin="${origin#http://github.com/}"
  origin="${origin#git@github.com:}"; origin="${origin#ssh://git@github.com/}"
  printf '%s\n' "${origin,,}"
}

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
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
  "$OUT/cross_format_reconciliation_lite_v1.json" \
  "$OUT/cross_format_reconciliation_lite_v1.txt" \
  "$OUT/cross_format_reconciliation_analyst_audit_v1.txt"

python -m py_compile \
  hpfa/modules/core/cross_format_reconciliation_lite/src/cross_format_reconciliation.py \
  hpfa/modules/core/cross_format_reconciliation_lite/tests/test_cross_format_reconciliation.py \
  cross_format_reconciliation_lite.py
python -m pytest -q hpfa/modules/core/cross_format_reconciliation_lite/tests \
  | tee "$OUT/cross_format_reconciliation_pytest_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
python multiformat_file_inventory.py \
  --input-root "$ACTIVE_MATCH" \
  --runtime-authority "$ACTIVE_MATCH" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_inventory_refresh_v1.txt"
python csv_surface_reader_lite.py --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_csv_refresh_v1.txt"
python xlsx_surface_reader_lite.py --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_xlsx_refresh_v1.txt"
python xml_surface_reader_lite.py --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_xml_refresh_v1.txt"
python provider_alias_field_semantics_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_semantics_refresh_v1.txt"

set +e
python cross_format_reconciliation_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --inventory "$INVENTORY" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --semantics "$OUT/provider_alias_field_semantics_lite_v1.json" \
  --out "$OUT" \
  | tee "$OUT/cross_format_reconciliation_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

if [[ -f "$OUT/cross_format_reconciliation_lite_v1.json" ]]; then
  python - "$OUT/cross_format_reconciliation_lite_v1.json" <<'PY' \
    | tee "$OUT/cross_format_reconciliation_runtime_audit_v1.txt"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
print("HPFA CROSS-FORMAT RECONCILIATION ACTIVE_MATCH AUDIT")
for key in ("status", "role_pair_count", "fusion_admissibility", "hard_block_hits", "parse_warnings", "active_match_evidence_pass", "canonical_event_count", "production_release"):
    print(f"{key}={payload.get(key)}")
for row in payload.get("pair_reports", []):
    print(
        "role=" + str(row.get("source_role"))
        + " csv_rows=" + str(row.get("csv_profiled_row_count"))
        + " xml_rows=" + str(row.get("xml_row_candidate_count"))
        + " shared_ids=" + str(row.get("shared_id_candidate_count"))
        + " exact=" + str(row.get("exact_surface_alignment_candidate_count"))
        + " required_mismatch=" + str(row.get("required_field_mismatch_candidate_count"))
        + " csv_only=" + str(row.get("csv_only_id_candidate_count"))
        + " xml_only=" + str(row.get("xml_only_id_candidate_count"))
        + " decision=" + str(row.get("decision"))
    )
PY
else
  printf 'cross_format_reconciliation_output_missing\n' | tee "$OUT/cross_format_reconciliation_runtime_audit_v1.txt"
fi

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/cross_format_reconciliation_lite_v1.json"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/cross_format_reconciliation_result_v1.txt"
exit "$RUN_RC"
