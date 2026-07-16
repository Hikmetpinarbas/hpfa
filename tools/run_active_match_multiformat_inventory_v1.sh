#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hpfa_claim_integrity/hpfa}"
ACTIVE="${HPFA_ACTIVE_MATCH:-$REPO/runtime/active_single_match/current}"
OUT="/sdcard/Download/HPFA"
EXPECTED_BRANCH="multiformat-file-inventory-lite-v1"

fail() {
  printf 'FAIL: %s\n' "$1" | tee "$OUT/multiformat_file_inventory_active_match_v1.txt" >&2
  exit 1
}

mkdir -p "$OUT"
[[ -d "$REPO/.git" ]] || fail "hpfa_repo_not_found:$REPO"
[[ -d "$ACTIVE" ]] || fail "active_match_runtime_not_found:$ACTIVE"

cd "$REPO"
ACTUAL_BRANCH="$(git branch --show-current)"
ACTUAL_HEAD="$(git rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean"

python -m py_compile \
  hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory.py \
  hpfa/modules/core/multiformat_file_inventory_lite/tests/test_multiformat_file_inventory.py \
  multiformat_file_inventory.py

python -m pytest -q \
  hpfa/modules/core/multiformat_file_inventory_lite/tests/test_multiformat_file_inventory.py \
  | tee "$OUT/multiformat_file_inventory_pytest_v1.txt"

set +e
python multiformat_file_inventory.py \
  --input-root "$ACTIVE" \
  --out "$OUT" \
  | tee "$OUT/multiformat_file_inventory_active_match_v1.txt"
RUN_RC="${PIPESTATUS[0]}"
set -e

{
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE"
  echo "run_rc=$RUN_RC"
  echo "main_output=$OUT/multiformat_file_inventory_lite_v1.json"
  echo "inventory_json=$OUT/input_file_inventory.json"
  echo "inventory_tsv=$OUT/input_file_inventory.tsv"
  echo "unsupported_report=$OUT/unsupported_file_report.json"
  echo "duplicate_report=$OUT/duplicate_file_fingerprint_report.json"
  echo "decision_txt=$OUT/multiformat_ingest_decision_v1.txt"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$OUT/multiformat_file_inventory_result_v1.txt"

exit "$RUN_RC"
