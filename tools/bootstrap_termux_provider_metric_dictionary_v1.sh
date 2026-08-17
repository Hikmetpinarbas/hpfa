#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-183-research-hardened-v1"
DEFAULT_ORIGIN_URL="https://github.com/Hikmetpinarbas/hpfa.git"
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
ssh://git@github.com/hikmetpinarbas/hpfa|ssh://git@github.com:hikmetpinarbas/hpfa.git)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

# Existing product checkouts may contain untrusted local Git configuration. They are
# intentionally not used for fetch, object import, checkout, or execution here.
# Historical discovery locations retained only as operator documentation:
#   $HOME/hp/repos/hpfa
#   $HOME/hpfa_claim_integrity/hpfa
# No merge --ff-only is performed against either checkout.
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"

ORIGIN_URL="${HPFA_TRUSTED_ORIGIN:-$DEFAULT_ORIGIN_URL}"
origin_is_trusted "$ORIGIN_URL" || fail "product_repo_origin_transport_or_identity_rejected:$ORIGIN_URL"

# Network/bootstrap Git commands run from a deliberately empty environment. This
# removes inherited GIT_CONFIG_COUNT/GIT_CONFIG_KEY_*/GIT_CONFIG_VALUE_*,
# GIT_CONFIG_PARAMETERS, GIT_CONFIG and other command-scope Git overrides before any
# trusted-origin fetch. Only the minimum deterministic environment is reintroduced.
clean_fetch_git(){
  env -i \
    HOME="${HOME:-}" \
    PATH="${PATH:-/data/data/com.termux/files/usr/bin:/system/bin}" \
    TMPDIR="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}" \
    LC_ALL=C \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_CONFIG_SYSTEM=/dev/null \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_SSH_COMMAND="ssh" \
    git \
      -c core.fsmonitor=false \
      -c core.hooksPath=/dev/null \
      -c core.untrackedCache=false \
      -c core.sshCommand=ssh \
      -c http.sslVerify=true \
      -c protocol.ext.allow=never \
      "$@"
}

# Fetch and execute only inside a freshly created repository whose configuration is
# controlled by this bootstrap. No product-checkout config participates in either step.
FETCH_TMP="$(mktemp -d "${TMPDIR:-/tmp}/hpfa-provider-dictionary-fetch.XXXXXX")" || fail "trusted_fetch_tempdir_create_failed"
cleanup_fetch_tmp(){ rm -rf "$FETCH_TMP"; }
trap cleanup_fetch_tmp EXIT
FETCH_REPO="$FETCH_TMP/fetch.git"
WORK_REPO="$FETCH_TMP/work"

clean_fetch_git init --bare "$FETCH_REPO" >/dev/null
clean_fetch_git --git-dir="$FETCH_REPO" remote add origin "$ORIGIN_URL"
clean_fetch_git --git-dir="$FETCH_REPO" fetch --no-tags --no-recurse-submodules "$ORIGIN_URL" "$BRANCH:refs/heads/remote"
REMOTE_HEAD="$(clean_fetch_git --git-dir="$FETCH_REPO" rev-parse refs/heads/remote 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi

# Local object materialization uses git-worktree from the clean bare object database.
# There is no second fetch and therefore no checkout-local URL rewrite / ext transport path.
clean_fetch_git --git-dir="$FETCH_REPO" worktree add -B "$BRANCH" "$WORK_REPO" "$REMOTE_HEAD" >/dev/null
ACTUAL_HEAD="$(clean_fetch_git -C "$WORK_REPO" rev-parse HEAD)"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "trusted_worktree_head_mismatch:$ACTUAL_HEAD remote:$REMOTE_HEAD"
EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"
[[ -z "$(clean_fetch_git -C "$WORK_REPO" status --porcelain --untracked-files=all)" ]] || fail "trusted_worktree_not_clean:$WORK_REPO"

RUNNER="$WORK_REPO/tools/run_active_match_provider_metric_dictionary_v1.sh"
[[ -x "$RUNNER" ]] || fail "provider_metric_dictionary_runner_not_executable:$RUNNER"

HPFA_REPO="$WORK_REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
"$RUNNER"
