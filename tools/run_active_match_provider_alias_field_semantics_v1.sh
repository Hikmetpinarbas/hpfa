#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="provider-alias-field-semantics-v1"
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
  "$OUT/provider_alias_field_semantics_lite_v1.json" \
  "$OUT/provider_alias_field_semantics_lite_v1.txt" \
  "$OUT/provider_alias_field_semantics_analyst_audit_v1.txt"

python -m py_compile \
  hpfa/modules/core/provider_alias_field_semantics_lite/src/provider_alias_field_semantics.py \
  hpfa/modules/core/provider_alias_field_semantics_lite/tests/test_provider_alias_field_semantics.py \
  provider_alias_field_semantics_lite.py
python -m pytest -q hpfa/modules/core/provider_alias_field_semantics_lite/tests \
  | tee "$OUT/provider_alias_field_semantics_pytest_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
python multiformat_file_inventory.py \
  --input-root "$ACTIVE_MATCH" \
  --runtime-authority "$ACTIVE_MATCH" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/provider_alias_field_semantics_inventory_refresh_v1.txt"

python csv_surface_reader_lite.py \
  --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_alias_field_semantics_csv_refresh_v1.txt"
python xlsx_surface_reader_lite.py \
  --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_alias_field_semantics_xlsx_refresh_v1.txt"
python xml_surface_reader_lite.py \
  --input-root "$ACTIVE_MATCH" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/provider_alias_field_semantics_xml_refresh_v1.txt"

set +e
python provider_alias_field_semantics_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --out "$OUT" \
  | tee "$OUT/provider_alias_field_semantics_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

if [[ -f "$OUT/provider_alias_field_semantics_lite_v1.json" ]]; then
  python - "$OUT/provider_alias_field_semantics_lite_v1.json" <<'PY' \
    | tee "$OUT/provider_alias_field_semantics_runtime_audit_v1.txt"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
print("HPFA PROVIDER ALIAS & FIELD SEMANTICS ACTIVE_MATCH AUDIT")
for key in ("status", "field_record_count", "hard_block_hits", "parse_warnings", "active_match_evidence_pass", "canonical_event_count", "production_release"):
    print(f"{key}={payload.get(key)}")
for fmt, row in (payload.get("mapping_coverage") or {}).items():
    print(f"format={fmt} fields={row.get('field_count')} mapped={row.get('candidate_mapped_count')} exact={row.get('exact_rule_count')} unknown={row.get('unknown_preserved_count')} coverage={row.get('coverage_ratio')}")
for fmt, row in (payload.get("required_anchor_audit") or {}).items():
    print(f"anchor_format={fmt} ready={row.get('ready_for_candidate_reconciliation')} missing={row.get('missing')}")
print("cross_format_candidate_groups=" + str(sum(1 for row in payload.get("candidate_equivalence_groups", []) if row.get("cross_format_candidate"))))
PY
else
  printf 'provider_alias_field_semantics_output_missing\n' | tee "$OUT/provider_alias_field_semantics_runtime_audit_v1.txt"
fi

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/provider_alias_field_semantics_lite_v1.json"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/provider_alias_field_semantics_result_v1.txt"
exit "$RUN_RC"
