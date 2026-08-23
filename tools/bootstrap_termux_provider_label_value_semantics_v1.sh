#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -n "$BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ "$EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] \
  || fail "expected_head_required_or_invalid:set_HPFA_EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
ACTIVE_RESOLVED="$(cd "$ACTIVE_MATCH" && pwd -P)"
case "$ACTIVE_RESOLVED" in
  */runtime/active_single_match/current) ;;
  *) fail "active_match_runtime_authority_mismatch:$ACTIVE_RESOLVED" ;;
esac

# Fetch and fast-forward only the operator-selected current product branch.
# The bootstrap contains no historical integration-branch authority.
git -C "$REPO" fetch origin "$BRANCH"
git -C "$REPO" switch "$BRANCH"
git -C "$REPO" merge --ff-only "origin/$BRANCH"

ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"

HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_RESOLVED" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_provider_label_value_semantics_v1.sh"
