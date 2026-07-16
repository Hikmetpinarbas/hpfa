#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

OUT="/sdcard/Download/HPFA"
EXPECTED_BRANCH="multiformat-file-inventory-lite-v1"
DEFAULT_ACTIVE="$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"

mkdir -p "$OUT"

fail() {
  printf 'FAIL: %s\n' "$1" | tee "$OUT/multiformat_file_inventory_active_match_v1.txt" >&2
  exit 1
}

repo_matches_hpfa() {
  local candidate="$1"
  [[ -d "$candidate/.git" ]] || return 1
  local remote
  remote="$(git -C "$candidate" remote get-url origin 2>/dev/null || true)"
  [[ "$remote" == *"Hikmetpinarbas/hpfa"* || "$remote" == *"/hpfa.git"* ]]
}

resolve_repo() {
  local candidate

  if [[ -n "${HPFA_REPO:-}" ]]; then
    repo_matches_hpfa "$HPFA_REPO" || fail "hpfa_repo_not_found_or_wrong_remote:$HPFA_REPO"
    printf '%s\n' "$HPFA_REPO"
    return 0
  fi

  for candidate in \
    "$PWD" \
    "$HOME/hp/repos/hpfa" \
    "$HOME/hpfa" \
    "$HOME/hpfa_claim_integrity/hpfa"
  do
    if repo_matches_hpfa "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  while IFS= read -r git_dir; do
    candidate="${git_dir%/.git}"
    if repo_matches_hpfa "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(find "$HOME" -maxdepth 6 -type d -name .git 2>/dev/null | sort)

  fail "hpfa_product_repo_not_found:set_HPFA_REPO_to_the_git_checkout"
}

REPO="$(resolve_repo)"
ACTIVE="${HPFA_ACTIVE_MATCH:-$DEFAULT_ACTIVE}"

[[ -d "$ACTIVE" ]] || fail "active_match_runtime_not_found:$ACTIVE"

ACTUAL_ROOT="$(git -C "$REPO" rev-parse --show-toplevel)"
ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"

[[ "$ACTUAL_ROOT" == "$REPO" ]] || REPO="$ACTUAL_ROOT"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH repo:$REPO"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

cd "$REPO"

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
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
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
