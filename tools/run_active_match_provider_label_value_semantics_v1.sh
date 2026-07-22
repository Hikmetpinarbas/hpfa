#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="provider-label-value-semantics-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 2; }

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

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "expected_head_missing_or_invalid:${EXPECTED_HEAD:-EMPTY}"
EXPECTED_HEAD="${EXPECTED_HEAD,,}"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
EXPECTED_RESOLVED="$(cd "$EXPECTED_ACTIVE_MATCH" && pwd -P)"
[[ "$ACTIVE_RESOLVED" == "$EXPECTED_RESOLVED" ]] || fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED expected:$EXPECTED_RESOLVED"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

mkdir -p "$OUT"
cd "$REPO"
rm -f \
  "$OUT/provider_label_value_inventory_v1.json" \
  "$OUT/provider_label_value_semantics_lite_v1.json" \
  "$OUT/provider_label_unknown_report_v1.json" \
  "$OUT/provider_label_conflict_report_v1.json" \
  "$OUT/provider_label_value_semantics_analyst_audit_v1.txt"

python -m py_compile \
  hpfa/modules/core/provider_label_value_semantics_lite/src/provider_label_value_semantics.py \
  hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics.py \
  provider_label_value_semantics_lite.py
python -m pytest -q hpfa/modules/core/provider_label_value_semantics_lite/tests \
  | tee "$OUT/provider_label_value_semantics_pytest_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
python multiformat_file_inventory.py \
  --input-root "$ACTIVE_RESOLVED" \
  --runtime-authority "$EXPECTED_RESOLVED" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_inventory_refresh_v1.txt"

python csv_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_csv_refresh_v1.txt"
python xlsx_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_xlsx_refresh_v1.txt"
python xml_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_xml_refresh_v1.txt"
python provider_alias_field_semantics_lite.py \
  --input-root "$ACTIVE_RESOLVED" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_field_refresh_v1.txt"

set +e
python provider_label_value_semantics_lite.py \
  --runtime-authority "$ACTIVE_RESOLVED" \
  --expected-runtime-authority "$EXPECTED_RESOLVED" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --field-semantics "$OUT/provider_alias_field_semantics_lite_v1.json" \
  --registry "$REPO/hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json" \
  --out "$OUT" \
  | tee "$OUT/provider_label_value_semantics_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

if [[ -f "$OUT/provider_label_value_semantics_lite_v1.json" ]]; then
  python - "$OUT/provider_label_value_semantics_lite_v1.json" <<'PY' \
    | tee "$OUT/provider_label_value_semantics_runtime_audit_v1.txt"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
coverage = payload.get("coverage") or {}
print("HPFA PROVIDER LABEL VALUE SEMANTICS ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "decision",
    "provider_label_record_count",
    "hard_block_hits",
    "review_hits",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
for key in (
    "csv_surface_row_volume",
    "mapped_surface_row_volume",
    "unknown_surface_row_volume",
    "mapped_surface_row_volume_ratio",
    "xml_example_support_label_count",
    "xlsx_aggregate_label_count",
):
    print(f"{key}={coverage.get(key)}")
print("cross_format_conflict_count=" + str((payload.get("cross_format_consistency") or {}).get("conflict_count")))
PY
else
  printf 'provider_label_value_semantics_output_missing\n' \
    | tee "$OUT/provider_label_value_semantics_runtime_audit_v1.txt"
fi

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_RESOLVED"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/provider_label_value_semantics_lite_v1.json"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/provider_label_value_semantics_result_v1.txt"

exit "$RUN_RC"
