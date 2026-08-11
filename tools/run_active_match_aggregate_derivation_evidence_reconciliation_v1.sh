#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-agent/aggregate-derivation-evidence-reconciliation-lite-v1}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
REPO="${HPFA_REPO:-$PWD}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
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

ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in
  */runtime/active_single_match/current) ;;
  *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;;
esac
case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac
mkdir -p "$OUT"

XLSX_ROW="$OUT/xlsx_entity_metric_row_projection_lite_v1.json"
EVIDENCE="$OUT/evidence_atom_inventory_lite_v1.json"
IDENTITY="$OUT/match_local_identity_candidates_lite_v1.json"
SEMANTICS="$OUT/provider_label_value_semantics_lite_v1.json"
ALIGNMENT="$OUT/aggregate_definition_alignment_lite_v1.json"
REGISTRY="$REPO/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json"
MAIN="$OUT/aggregate_derivation_evidence_reconciliation_lite_v1.json"

for required in "$XLSX_ROW" "$EVIDENCE" "$IDENTITY" "$SEMANTICS" "$ALIGNMENT" "$REGISTRY"; do
  [[ -f "$required" ]] || fail "required_input_missing:$required"
done

# Prerequisites must describe the same ACTIVE_MATCH authority where they expose runtime authority.
python - "$ACTIVE_RESOLVED" "$XLSX_ROW" "$EVIDENCE" "$IDENTITY" "$SEMANTICS" "$ALIGNMENT" <<'PY'
import json
import sys
from pathlib import Path

authority = str(Path(sys.argv[1]).resolve())
for raw in sys.argv[2:]:
    path = Path(raw)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("production_release") is True:
        raise SystemExit(f"unexpected_production_claim:{path.name}")
    if payload.get("canonical_event_count") not in (None, "UNKNOWN"):
        raise SystemExit(f"canonical_event_count_claimed:{path.name}")
    runtime = payload.get("runtime_authority")
    if runtime and str(Path(runtime).resolve()) != authority:
        raise SystemExit(f"prerequisite_runtime_authority_mismatch:{path.name}")
    if payload.get("status") == "FAIL_CLOSED" or payload.get("module_status") == "FAIL_CLOSED":
        raise SystemExit(f"prerequisite_fail_closed:{path.name}")
PY

cd "$REPO"
rm -f \
  "$MAIN" \
  "$OUT/aggregate_derivation_evidence_reconciliation_lite_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_analyst_audit_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_pytest_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_active_match_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_result_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_manifest_v1.sha256" \
  "$OUT/aggregate_derivation_evidence_reconciliation_active_match_bundle_v1.zip"

python -m py_compile \
  hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/src/aggregate_derivation_evidence_reconciliation.py \
  hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/tests/test_aggregate_derivation_evidence_reconciliation.py \
  aggregate_derivation_evidence_reconciliation_lite.py
python -m pytest -q \
  hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/tests \
  | tee "$OUT/aggregate_derivation_evidence_reconciliation_pytest_v1.txt"
python -m json.tool \
  hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/contract/aggregate_derivation_evidence_reconciliation_lite_v1.json \
  >/dev/null

set +e
python aggregate_derivation_evidence_reconciliation_lite.py \
  --xlsx-row-projection "$XLSX_ROW" \
  --evidence-atoms "$EVIDENCE" \
  --identity-candidates "$IDENTITY" \
  --label-semantics "$SEMANTICS" \
  --aggregate-alignment "$ALIGNMENT" \
  --definition-registry "$REGISTRY" \
  --runtime-authority "$ACTIVE_RESOLVED" \
  --active-match-execution \
  --out "$OUT" \
  | tee "$OUT/aggregate_derivation_evidence_reconciliation_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e
[[ -f "$MAIN" ]] || fail "aggregate_derivation_reconciliation_output_missing"

python - "$MAIN" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$EXPECTED_HEAD" "$ACTIVE_RESOLVED" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["runtime_branch"] = sys.argv[2]
payload["runtime_code_head_sha"] = sys.argv[3]
payload["runtime_expected_head_sha"] = sys.argv[4]
payload["runtime_authority"] = sys.argv[5]
payload["runtime_execution"] = {
    "branch": sys.argv[2],
    "head_sha": sys.argv[3],
    "expected_head_sha": sys.argv[4],
    "runtime_authority": sys.argv[5],
    "execution_completed": True,
    "exact_head_match": sys.argv[3].casefold() == sys.argv[4].casefold(),
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

python - "$MAIN" <<'PY' | tee "$OUT/aggregate_derivation_evidence_reconciliation_result_v1.txt"
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
for key in (
    "module_id", "status", "runtime_evidence_status", "runtime_branch",
    "runtime_code_head_sha", "match_surface_binding_id",
    "reconciliation_record_count", "g16_recheck_admitted_count",
    "g16_recheck_blocked_count", "observed_arithmetic_status_counts",
    "provider_definition_evidence_status_counts", "hard_block_hits", "review_hits",
    "canonical_event_count", "production_release",
):
    print(f"{key}={payload.get(key)}")
PY

MANIFEST="$OUT/aggregate_derivation_evidence_reconciliation_manifest_v1.sha256"
: > "$MANIFEST"
for file in \
  "$MAIN" \
  "$OUT/aggregate_derivation_evidence_reconciliation_lite_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_analyst_audit_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_pytest_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_active_match_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_result_v1.txt"; do
  [[ -f "$file" ]] || fail "manifest_input_missing:$file"
  sha256sum "$file" >> "$MANIFEST"
done

BUNDLE="$OUT/aggregate_derivation_evidence_reconciliation_active_match_bundle_v1.zip"
zip -j -q "$BUNDLE" \
  "$MAIN" \
  "$OUT/aggregate_derivation_evidence_reconciliation_lite_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_analyst_audit_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_pytest_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_active_match_v1.txt" \
  "$OUT/aggregate_derivation_evidence_reconciliation_result_v1.txt" \
  "$MANIFEST"

printf 'bundle=%s\n' "$BUNDLE"
printf 'run_rc=%s\n' "$RUN_RC"
printf 'canonical_event_count=UNKNOWN\n'
printf 'production_release=false\n'
exit "$RUN_RC"
