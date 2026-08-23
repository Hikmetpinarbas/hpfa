#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
BRANCH="multiformat-file-inventory-lite-v1"
PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="/sdcard/Download/HPFA"

mkdir -p "$OUT"

fail() {
  printf 'FAIL: %s\n' "$1" | tee "$OUT/multiformat_inventory_bootstrap_v1.txt" >&2
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

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_not_found:$ACTIVE_MATCH"

if [[ -e "$PRODUCT_REPO" && ! -d "$PRODUCT_REPO/.git" ]]; then
  fail "product_repo_path_exists_but_is_not_git:$PRODUCT_REPO"
fi

if [[ ! -d "$PRODUCT_REPO/.git" ]]; then
  mkdir -p "$(dirname "$PRODUCT_REPO")"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$PRODUCT_REPO"
fi

ORIGIN_URL="$(git -C "$PRODUCT_REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_remote_slug "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "wrong_product_repo_origin:$ORIGIN_URL expected:$EXPECTED_REPO_SLUG"

if [[ -n "$(git -C "$PRODUCT_REPO" status --porcelain)" ]]; then
  fail "product_repo_worktree_not_clean:$PRODUCT_REPO"
fi

git -C "$PRODUCT_REPO" fetch origin "$BRANCH"

if git -C "$PRODUCT_REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$PRODUCT_REPO" switch "$BRANCH"
else
  git -C "$PRODUCT_REPO" switch --track "origin/$BRANCH"
fi

git -C "$PRODUCT_REPO" pull --ff-only origin "$BRANCH"

ACTUAL_BRANCH="$(git -C "$PRODUCT_REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$BRANCH"

{
  echo "product_repo=$PRODUCT_REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "bootstrap_status=READY"
} | tee "$OUT/multiformat_inventory_bootstrap_v1.txt"

HPFA_REPO="$PRODUCT_REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
bash "$PRODUCT_REPO/tools/run_active_match_multiformat_inventory_v1.sh"
