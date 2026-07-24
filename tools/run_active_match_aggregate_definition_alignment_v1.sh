#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="agent/aggregate-definition-alignment-lite-v1"
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

XLSX_AUDIT="$OUT/xlsx_surface_audit_lite_v1.json"
LABEL_SEMANTICS="$OUT/provider_label_value_semantics_lite_v1.json"
REGISTRY="$REPO/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json"
OUTPUT="$OUT/aggregate_definition_alignment_lite_v1.json"

[[ -f "$XLSX_AUDIT" ]] || fail "xlsx_surface_audit_missing:$XLSX_AUDIT"
[[ -f "$LABEL_SEMANTICS" ]] || fail "provider_label_semantics_missing:$LABEL_SEMANTICS"
[[ -f "$REGISTRY" ]] || fail "aggregate_definition_registry_missing:$REGISTRY"
[[ -d "$REPO/configs/metrics" ]] || fail "metric_config_directory_missing"

mkdir -p "$OUT"
rm -f "$OUTPUT" "$OUT/aggregate_definition_alignment_active_match_v1.txt" "$OUT/aggregate_definition_alignment_result_v1.txt"
cd "$REPO"

python -m py_compile \
  aggregate_definition_alignment_lite.py \
  hpfa/modules/core/aggregate_definition_alignment_lite/src/aggregate_definition_alignment.py
python -m pytest -q \
  hpfa/modules/core/metric_definition_policy_lite/tests \
  hpfa/modules/core/aggregate_definition_alignment_lite/tests \
  | tee "$OUT/aggregate_definition_alignment_pytest_v1.txt"

set +e
python aggregate_definition_alignment_lite.py \
  --xlsx-audit "$XLSX_AUDIT" \
  --label-semantics "$LABEL_SEMANTICS" \
  --metric-config-dir "$REPO/configs/metrics" \
  --registry "$REGISTRY" \
  --output "$OUTPUT" \
  | tee "$OUT/aggregate_definition_alignment_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

[[ -f "$OUTPUT" ]] || fail "aggregate_definition_alignment_output_missing"
python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" <<'PY' \
  | tee "$OUT/aggregate_definition_alignment_runtime_audit_v1.txt"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
authority_equal = sys.argv[2] == sys.argv[3]
payload["runtime_authority"] = sys.argv[2]
payload["runtime_authority_equal"] = authority_equal
payload["active_match_evidence_pass"] = (
    payload.get("status") == "SMOKE_PASS"
    and not payload.get("hard_block_hits")
    and not payload.get("review_hits")
    and authority_equal
)
payload["runtime_evidence_status"] = (
    "ACTIVE_MATCH_EVIDENCE_PASS"
    if payload["active_match_evidence_pass"]
    else "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"
)
payload["release_status"] = "NOT_PRODUCTION"
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
print("HPFA AGGREGATE DEFINITION ALIGNMENT ACTIVE_MATCH AUDIT")
for key in (
    "status",
    "runtime_evidence_status",
    "release_status",
    "definition_candidate_count",
    "alignment_decision_counts",
    "hard_block_hits",
    "review_hits",
    "active_match_evidence_pass",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
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
} | tee "$OUT/aggregate_definition_alignment_result_v1.txt"

exit "$RUN_RC"
