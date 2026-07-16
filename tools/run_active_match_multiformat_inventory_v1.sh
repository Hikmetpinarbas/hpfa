#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

OUT="/sdcard/Download/HPFA"
EXPECTED_BRANCH="multiformat-file-inventory-lite-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
DEFAULT_ACTIVE="$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"

mkdir -p "$OUT"

fail() {
  printf 'FAIL: %s\n' "$1" | tee "$OUT/multiformat_file_inventory_active_match_v1.txt" >&2
  exit 1
}

normalize_remote_slug() {
  local remote="${1:-}"
  remote="${remote%/}"
  remote="${remote%.git}"
  remote="${remote#https://github.com/}"
  remote="${remote#http://github.com/}"
  remote="${remote#git@github.com:}"
  remote="${remote#ssh://git@github.com/}"
  printf '%s\n' "${remote,,}"
}

repo_matches_hpfa() {
  local candidate="$1"
  [[ -d "$candidate/.git" ]] || return 1
  local remote slug
  remote="$(git -C "$candidate" remote get-url origin 2>/dev/null || true)"
  slug="$(normalize_remote_slug "$remote")"
  [[ "$slug" == "$EXPECTED_REPO_SLUG" ]]
}

self_test_repo_guard() {
  local tmp repo
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  repo="$tmp/repo"
  git init -q "$repo"
  git -C "$repo" remote add origin "https://github.com/Hikmetpinarbas/hpfa.git"
  repo_matches_hpfa "$repo" || fail "self_test_exact_origin_rejected"
  git -C "$repo" remote set-url origin "https://github.com/Hikmetpinarbas/hpfa-main.git"
  if repo_matches_hpfa "$repo"; then
    fail "self_test_prefix_collision_accepted"
  fi
  git -C "$repo" remote set-url origin "git@github.com:Hikmetpinarbas/hpfa.git"
  repo_matches_hpfa "$repo" || fail "self_test_ssh_origin_rejected"
  echo "repo_origin_guard_self_test=PASS"
}

if [[ "${1:-}" == "--self-test-repo-guard" ]]; then
  self_test_repo_guard
  exit 0
fi

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
    "$HOME/hpfa"
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

  fail "hpfa_product_repo_not_found:set_HPFA_REPO_to_exact_Hikmetpinarbas_hpfa_checkout"
}

REPO="$(resolve_repo)"
ACTIVE="${HPFA_ACTIVE_MATCH:-$DEFAULT_ACTIVE}"

[[ -d "$ACTIVE" ]] || fail "active_match_runtime_not_found:$ACTIVE"

ACTUAL_ROOT="$(git -C "$REPO" rev-parse --show-toplevel)"
[[ "$ACTUAL_ROOT" == "$REPO" ]] || REPO="$ACTUAL_ROOT"
repo_matches_hpfa "$REPO" || fail "wrong_product_repo_origin:$REPO"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_remote_slug "$ORIGIN_URL")"

[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "unexpected_origin:$ORIGIN_URL expected:$EXPECTED_REPO_SLUG"
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
  echo "origin_slug=$ORIGIN_SLUG"
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
