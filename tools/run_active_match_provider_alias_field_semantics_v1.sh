#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){
  local o="${1:-}"; o="${o%/}"; o="${o%.git}"
  o="${o#https://github.com/}"; o="${o#http://github.com/}"
  o="${o#git@github.com:}"; o="${o#ssh://git@github.com/}"
  printf '%s\n' "${o,,}"
}
identity_matches(){
  [[ -n "$3" && -n "$4" && "$1" == "$3" && "$2" == "$4" ]]
}

if [[ "${1:-}" == "--self-test-execution-identity-guard" ]]; then
  identity_matches "integration/foundation-tranche-a-v1" "abc123" \
    "integration/foundation-tranche-a-v1" "abc123" || fail "self_test_exact_identity_rejected"
  if identity_matches "wrong" "abc123" "integration/foundation-tranche-a-v1" "abc123"; then
    fail "self_test_wrong_branch_accepted"
  fi
  if identity_matches "integration/foundation-tranche-a-v1" "wrong" \
    "integration/foundation-tranche-a-v1" "abc123"; then
    fail "self_test_wrong_head_accepted"
  fi
  echo "provider_alias_field_semantics_execution_identity_guard_self_test=PASS"
  exit 0
fi

[[ -n "$EXPECTED_BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
identity_matches "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_BRANCH" "$EXPECTED_HEAD" || \
  fail "execution_identity_mismatch:branch=$ACTUAL_BRANCH head=$ACTUAL_HEAD expected_branch=$EXPECTED_BRANCH expected_head=$EXPECTED_HEAD"
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
  "$OUT/provider_alias_field_semantics_analyst_audit_v1.txt" \
  "$OUT/provider_alias_field_semantics_temporal_order_guard_v1.txt"

python -m py_compile \
  hpfa/modules/core/provider_alias_field_semantics_lite/src/provider_alias_field_semantics.py \
  hpfa/modules/core/provider_alias_field_semantics_lite/tests/test_provider_alias_field_semantics.py \
  provider_alias_field_semantics_lite.py
python -m pytest -q hpfa/modules/core/provider_alias_field_semantics_lite/tests \
  | tee "$OUT/provider_alias_field_semantics_pytest_v1.txt"

for runner in \
  run_active_match_multiformat_inventory_v1.sh \
  run_active_match_csv_surface_reader_v1.sh \
  run_active_match_xlsx_surface_reader_v1.sh \
  run_active_match_xml_surface_reader_v1.sh
do
  HPFA_REPO="$REPO" \
  HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
  HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
  HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
  HPFA_PHONE_OUTPUT="$OUT" \
  bash "$REPO/tools/$runner"
done

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

python - <<'PY' | tee "$OUT/provider_alias_field_semantics_temporal_order_guard_v1.txt"
import json
from pathlib import Path
c=json.loads(Path(
 "hpfa/modules/core/provider_alias_field_semantics_lite/contract/provider_alias_field_semantics_lite_v1.json"
).read_text(encoding="utf-8"))
g=c["temporal_order_guard"]
print("HPFA R08 TEMPORAL ORDER GUARD")
for k in (
 "time_field_candidate_is_football_order_truth",
 "source_row_index_role",
 "same_time_default_without_admitted_order_evidence",
 "event_type_priority_ordering_allowed",
 "same_time_means_simultaneous_truth",
 "downstream_order_sensitive_claim_decision",
 "claim_ceiling",
):
 print(f"{k}={g[k]}")
PY

{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_branch=$EXPECTED_BRANCH"
  echo "expected_head=$EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/provider_alias_field_semantics_lite_v1.json"
  echo "temporal_order_guard_output=$OUT/provider_alias_field_semantics_temporal_order_guard_v1.txt"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/provider_alias_field_semantics_result_v1.txt"

exit "$RUN_RC"
