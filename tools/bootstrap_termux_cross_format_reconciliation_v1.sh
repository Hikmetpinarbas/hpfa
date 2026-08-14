#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="integration/foundation-tranche-a-v1"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

git -C "$REPO" fetch origin "$BRANCH"
git -C "$REPO" switch "$BRANCH"
git -C "$REPO" merge --ff-only "origin/$BRANCH"

ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"

HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_cross_format_reconciliation_v1.sh"
