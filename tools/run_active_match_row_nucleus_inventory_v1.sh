#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="agent/row-nucleus-inventory-lite-v1"
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
  "$OUT/row_nucleus_inventory_lite_v1.json" \
  "$OUT/row_nucleus_inventory_lite_v1.txt" \
  "$OUT/row_nucleus_inventory_analyst_audit_v1.txt" \
  "$OUT/g01_g18_data_quality_rollup_v1.json" \
  "$OUT/g01_g18_data_quality_rollup_v1.txt"

python -m py_compile \
  row_nucleus_inventory_lite.py \
  hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py \
  hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory_hardened.py
python -m pytest -q \
  hpfa/modules/core/provider_metric_dictionary_lite/tests \
  hpfa/modules/core/row_nucleus_inventory_lite/tests \
  | tee "$OUT/row_nucleus_inventory_pytest_v1.txt"

INVENTORY="$OUT/multiformat_file_inventory_lite_v1.json"
python multiformat_file_inventory.py \
  --input-root "$ACTIVE_RESOLVED" \
  --runtime-authority "$EXPECTED_RESOLVED" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_inventory_refresh_v1.txt"
python csv_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_csv_refresh_v1.txt"
python xlsx_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_xlsx_refresh_v1.txt"
python xml_surface_reader_lite.py \
  --input-root "$ACTIVE_RESOLVED" --inventory "$INVENTORY" --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_xml_refresh_v1.txt"
python provider_alias_field_semantics_lite.py \
  --input-root "$ACTIVE_RESOLVED" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_field_semantics_refresh_v1.txt"
python provider_label_value_semantics_lite.py \
  --runtime-authority "$ACTIVE_RESOLVED" \
  --expected-runtime-authority "$EXPECTED_RESOLVED" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --field-semantics "$OUT/provider_alias_field_semantics_lite_v1.json" \
  --registry "$REPO/hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json" \
  --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_label_semantics_refresh_v1.txt"
python cross_format_reconciliation_lite.py \
  --input-root "$ACTIVE_RESOLVED" \
  --expected-runtime-authority "$EXPECTED_RESOLVED" \
  --inventory "$INVENTORY" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --field-semantics "$OUT/provider_alias_field_semantics_lite_v1.json" \
  --label-semantics "$OUT/provider_label_value_semantics_lite_v1.json" \
  --xml-group-registry "$REPO/hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json" \
  --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_reconciliation_refresh_v1.txt"
python aggregate_definition_alignment_lite.py \
  --xlsx-audit "$OUT/xlsx_surface_audit_lite_v1.json" \
  --label-semantics "$OUT/provider_label_value_semantics_lite_v1.json" \
  --metric-config-dir "$REPO/configs/metrics" \
  --registry "$REPO/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json" \
  --output "$OUT/aggregate_definition_alignment_lite_v1.json" \
  | tee "$OUT/row_nucleus_inventory_aggregate_alignment_refresh_v1.txt"
python - "$REPO/configs/metrics" "$OUT/provider_metric_dictionary_lite_v1.json" <<'PY' \
  | tee "$OUT/row_nucleus_inventory_metric_dictionary_refresh_v1.txt"
import json
import sys
from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import write_dictionary_report
report = write_dictionary_report(sys.argv[1], sys.argv[2])
print(json.dumps({
    "status": report.get("status"),
    "metric_record_count": report.get("metric_record_count"),
    "runtime_contract_ready_count": report.get("runtime_contract_ready_count"),
    "canonical_event_count": report.get("canonical_event_count"),
    "production_release": report.get("production_release"),
}, ensure_ascii=False, indent=2))
PY

set +e
python row_nucleus_inventory_lite.py \
  --input-root "$ACTIVE_RESOLVED" \
  --inventory "$INVENTORY" \
  --csv-audit "$OUT/csv_surface_audit_lite_v1.json" \
  --xml-audit "$OUT/xml_surface_audit_lite_v1.json" \
  --field-semantics "$OUT/provider_alias_field_semantics_lite_v1.json" \
  --label-semantics "$OUT/provider_label_value_semantics_lite_v1.json" \
  --reconciliation "$OUT/cross_format_reconciliation_lite_v1.json" \
  --aggregate-alignment "$OUT/aggregate_definition_alignment_lite_v1.json" \
  --metric-dictionary "$OUT/provider_metric_dictionary_lite_v1.json" \
  --xml-group-registry "$REPO/hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json" \
  --out "$OUT" \
  | tee "$OUT/row_nucleus_inventory_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

OUTPUT="$OUT/row_nucleus_inventory_lite_v1.json"
[[ -f "$OUTPUT" ]] || fail "row_nucleus_inventory_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC" <<'PY' \
  | tee "$OUT/row_nucleus_inventory_runtime_audit_v1.txt"
import json
import sys

path, actual_authority, expected_authority, run_rc_text = sys.argv[1:]
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
payload["runtime_code_head_sha"] = None
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
print("HPFA ROW NUCLEUS INVENTORY ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "module_status",
    "runtime_evidence_status",
    "release_status",
    "row_nucleus_candidate_count",
    "row_nucleus_pass_count",
    "row_nucleus_review_required_count",
    "source_role_count",
    "duplicate_reflection_count",
    "cross_id_collision_nucleus_count",
    "semantic_review_nucleus_count",
    "surface_review_nucleus_count",
    "hard_block_hits",
    "review_hits",
    "active_match_execution_completed",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
rollup = payload.get("g01_g18_rollup") or {}
print(f"g01_g18_status={rollup.get('status')}")
PY

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_RESOLVED"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUTPUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/row_nucleus_inventory_result_v1.txt"

exit "$RUN_RC"
