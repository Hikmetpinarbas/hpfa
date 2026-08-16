#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-183-research-hardened-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }
normalize_origin(){ local o="${1:-}"; o="${o%/}"; o="${o%.git}"; o="${o#https://github.com/}"; o="${o#http://github.com/}"; o="${o#git@github.com:}"; o="${o#ssh://git@github.com/}"; printf '%s\n' "${o,,}"; }

REPO="${HPFA_REPO:-}"
if [[ -z "$REPO" ]]; then
  for candidate in "$HOME/hp/repos/hpfa" "$HOME/hpfa_claim_integrity/hpfa"; do
    if [[ -d "$candidate/.git" ]]; then
      REPO="$candidate"
      break
    fi
  done
fi
[[ -n "$REPO" && -d "$REPO/.git" ]] || fail "hpfa_repo_not_found"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch_before_fetch:$ORIGIN_URL"

git -C "$REPO" fetch origin "$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi

if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
  git -C "$REPO" merge --ff-only "origin/$BRANCH"
else
  git -C "$REPO" switch -c "$BRANCH" --track "origin/$BRANCH"
fi

ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "product_repo_head_not_remote_head:$ACTUAL_HEAD remote:$REMOTE_HEAD"
EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"

HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
bash "$REPO/tools/run_active_match_provider_metric_dictionary_v1.sh"
