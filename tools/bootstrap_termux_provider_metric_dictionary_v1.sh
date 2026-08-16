#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-183-research-hardened-v1"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 2; }

origin_is_trusted(){
  local o="${1:-}"
  o="${o%/}"
  local lower="${o,,}"
  case "$lower" in
    https://github.com/hikmetpinarbas/hpfa|https://github.com/hikmetpinarbas/hpfa.git|\
git@github.com:hikmetpinarbas/hpfa|git@github.com:hikmetpinarbas/hpfa.git|\
ssh://git@github.com/hikmetpinarbas/hpfa|ssh://git@github.com/hikmetpinarbas/hpfa.git)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

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

safe_git(){
  GIT_CONFIG_GLOBAL=/dev/null \
  GIT_CONFIG_SYSTEM=/dev/null \
  GIT_CONFIG_NOSYSTEM=1 \
  GIT_SSH_COMMAND="ssh" \
  git \
    -c core.fsmonitor=false \
    -c core.hooksPath=/dev/null \
    -c core.untrackedCache=false \
    -c core.sshCommand=ssh \
    -C "$REPO" "$@"
}

clean_fetch_git(){
  env \
    -u GIT_SSL_NO_VERIFY \
    -u GIT_ASKPASS \
    -u SSH_ASKPASS \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_CONFIG_SYSTEM=/dev/null \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_SSH_COMMAND="ssh" \
    git \
      -c core.hooksPath=/dev/null \
      -c core.sshCommand=ssh \
      -c http.sslVerify=true \
      -c protocol.ext.allow=never \
      "$@"
}

# Trust boundary: inspect the checkout only with unsafe hook/fsmonitor paths neutralized.
# The network fetch itself is performed from a new bare repository with repository,
# global and system Git configuration isolated from the checkout.
ORIGIN_URL="$(safe_git remote get-url origin 2>/dev/null || true)"
origin_is_trusted "$ORIGIN_URL" || fail "product_repo_origin_transport_or_identity_rejected:$ORIGIN_URL"
[[ -z "$(safe_git status --porcelain --untracked-files=all)" ]] || fail "product_repo_worktree_not_clean:$REPO"

FETCH_TMP="$(mktemp -d "${TMPDIR:-/tmp}/hpfa-provider-dictionary-fetch.XXXXXX")" || fail "trusted_fetch_tempdir_create_failed"
cleanup_fetch_tmp(){ rm -rf "$FETCH_TMP"; }
trap cleanup_fetch_tmp EXIT
FETCH_REPO="$FETCH_TMP/fetch.git"
clean_fetch_git init --bare "$FETCH_REPO" >/dev/null
clean_fetch_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules "$ORIGIN_URL" "$BRANCH:refs/heads/remote"
REMOTE_HEAD="$(clean_fetch_git --git-dir="$FETCH_REPO" rev-parse refs/heads/remote 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi

# Import only the already-fetched commit graph into the product checkout; no checkout-local
# configuration participates in the network transfer above.
safe_git fetch --no-tags --no-recurse-submodules "$FETCH_REPO" "refs/heads/remote:refs/remotes/origin/$BRANCH"

if safe_git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  safe_git switch "$BRANCH"
  safe_git merge --ff-only "origin/$BRANCH"
else
  safe_git switch -c "$BRANCH" --track "origin/$BRANCH"
fi

ACTUAL_HEAD="$(safe_git rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "product_repo_head_not_remote_head:$ACTUAL_HEAD remote:$REMOTE_HEAD"
EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(safe_git status --porcelain --untracked-files=all)" ]] || fail "product_repo_worktree_not_clean_after_sync:$REPO"

RUNNER="$REPO/tools/run_active_match_provider_metric_dictionary_v1.sh"
[[ -x "$RUNNER" ]] || fail "provider_metric_dictionary_runner_not_executable:$RUNNER"

HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
"$RUNNER"
