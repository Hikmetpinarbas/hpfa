#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="work/reconstruct-178-research-hardened-v1"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }

[[ -d "$REPO/.git" ]] || fail "product_repo_not_git_checkout:$REPO"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

git -C "$REPO" fetch origin "$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"
REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi

git -C "$REPO" switch "$BRANCH"
git -C "$REPO" merge --ff-only "origin/$BRANCH"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "product_repo_head_not_remote_head:$ACTUAL_HEAD remote:$REMOTE_HEAD"
HPFA_EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
[[ "$ACTUAL_HEAD" == "$HPFA_EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$HPFA_EXPECTED_HEAD"

HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$HPFA_EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_metric_definition_policy_v1.sh"
