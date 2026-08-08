#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/xlsx-entity-metric-row-projection-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

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

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"

[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_not_set"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "invalid_expected_head:$EXPECTED_HEAD"
[[ "${ACTUAL_HEAD,,}" == "${EXPECTED_HEAD,,}" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
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
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.json" \
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_analyst_audit_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_pytest_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_active_match_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_result_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_manifest_v1.sha256" \
  "$OUT/xlsx_entity_metric_row_projection_active_match_bundle_v1.zip"

python -m py_compile \
  hpfa/modules/core/xlsx_entity_metric_row_projection_lite/src/xlsx_entity_metric_row_projection.py \
  hpfa/modules/core/xlsx_entity_metric_row_projection_lite/tests/test_xlsx_entity_metric_row_projection.py \
  xlsx_entity_metric_row_projection_lite.py

python -m pytest -q \
  hpfa/modules/core/xlsx_entity_metric_row_projection_lite/tests \
  | tee "$OUT/xlsx_entity_metric_row_projection_pytest_v1.txt"

python -m json.tool \
  hpfa/modules/core/xlsx_entity_metric_row_projection_lite/contract/xlsx_entity_metric_row_projection_lite_v1.json \
  >/dev/null

# Refresh current inventory from the single runtime authority.
python multiformat_file_inventory.py \
  --input-root "$ACTIVE_MATCH" \
  --runtime-authority "$ACTIVE_MATCH" \
  --active-match-execution \
  --out "$TMP" \
  >/dev/null

INVENTORY="$TMP/multiformat_file_inventory_lite_v1.json"
[[ -f "$INVENTORY" ]] || fail "current_inventory_refresh_missing"

# Re-run the current product XLSX producer with its semantic header normalizer.
# Importing the root wrapper applies the same normalization patch without invoking
# its historical branch guard; no reader logic is copied into this runner.
python - "$ACTIVE_MATCH" "$INVENTORY" "$TMP" <<'PY'
import sys
from pathlib import Path
import xlsx_surface_reader_lite as wrapper

active, inventory, out = map(Path, sys.argv[1:4])
payload = wrapper.xlsx_surface_reader.write_outputs(active, inventory, out)
if payload.get("status") == "FAIL_CLOSED":
    raise SystemExit(2)
PY

XLSX_AUDIT="$TMP/xlsx_surface_audit_lite_v1.json"
[[ -f "$XLSX_AUDIT" ]] || fail "current_xlsx_surface_audit_missing"

# Preserve the freshly regenerated prerequisite evidence as flat phone outputs.
cp "$INVENTORY" "$OUT/multiformat_file_inventory_lite_v1.json"
cp "$XLSX_AUDIT" "$OUT/xlsx_surface_audit_lite_v1.json"

set +e
python xlsx_entity_metric_row_projection_lite.py \
  --input-root "$ACTIVE_MATCH" \
  --inventory "$INVENTORY" \
  --xlsx-audit "$XLSX_AUDIT" \
  --runtime-authority "$ACTIVE_MATCH" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/xlsx_entity_metric_row_projection_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

MAIN="$OUT/xlsx_entity_metric_row_projection_lite_v1.json"
[[ -f "$MAIN" ]] || fail "xlsx_entity_metric_row_projection_main_output_missing"

# Exact-code provenance is written into the product JSON itself.
python - "$MAIN" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_HEAD" "$ACTIVE_MATCH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
branch, head, expected_head, authority = sys.argv[2:6]
payload = json.loads(path.read_text(encoding="utf-8"))
payload["runtime_branch"] = branch
payload["runtime_code_head_sha"] = head
payload["runtime_expected_head_sha"] = expected_head
payload["runtime_execution"] = {
    "branch": branch,
    "head_sha": head,
    "expected_head_sha": expected_head,
    "runtime_authority": authority,
    "execution_completed": True,
    "exact_head_match": head.casefold() == expected_head.casefold(),
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

python - "$MAIN" <<'PY' \
  | tee "$OUT/xlsx_entity_metric_row_projection_result_v1.txt"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

for key in (
    "module_id",
    "status",
    "runtime_evidence_status",
    "runtime_branch",
    "runtime_code_head_sha",
    "runtime_expected_head_sha",
    "runtime_authority",
    "xlsx_file_count",
    "row_projection_count",
    "match_surface_binding_id",
    "hard_block_hits",
    "review_hits",
    "canonical_event_count",
    "production_release",
):
    print(f"{key}={payload.get(key)}")
PY

MANIFEST="$OUT/xlsx_entity_metric_row_projection_manifest_v1.sha256"
: > "$MANIFEST"
for file in \
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.json" \
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_analyst_audit_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_pytest_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_active_match_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_result_v1.txt" \
  "$OUT/multiformat_file_inventory_lite_v1.json" \
  "$OUT/xlsx_surface_audit_lite_v1.json"; do
  [[ -f "$file" ]] || fail "manifest_input_missing:$file"
  sha256sum "$file" >> "$MANIFEST"
done

BUNDLE="$OUT/xlsx_entity_metric_row_projection_active_match_bundle_v1.zip"
rm -f "$BUNDLE"
zip -j -q "$BUNDLE" \
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.json" \
  "$OUT/xlsx_entity_metric_row_projection_lite_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_analyst_audit_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_pytest_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_active_match_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_result_v1.txt" \
  "$OUT/xlsx_entity_metric_row_projection_manifest_v1.sha256" \
  "$OUT/multiformat_file_inventory_lite_v1.json" \
  "$OUT/xlsx_surface_audit_lite_v1.json"

printf 'bundle=%s\n' "$BUNDLE"
printf 'run_rc=%s\n' "$RUN_RC"
printf 'canonical_event_count=UNKNOWN\n'
printf 'production_release=false\n'

exit "$RUN_RC"
