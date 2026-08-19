#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="work/reconstruct-181-research-hardened-v1"
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
ssh://git@github.com/hikmetpinarbas/hpfa|ssh://git@github.com/hikmetpinarbas/hpfa.git)
      return 0 ;;
    *) return 1 ;;
  esac
}

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
ORIGIN_URL="${HPFA_TRUSTED_ORIGIN:-$DEFAULT_ORIGIN_URL}"
origin_is_trusted "$ORIGIN_URL" || fail "product_repo_origin_transport_or_identity_rejected:$ORIGIN_URL"

# Bootstrap must not trust an existing product checkout. Network Git runs from an
# empty environment with hooks/fsmonitor/ext transport disabled and verified TLS.
clean_git(){
  env -i \
    -u GIT_SSL_NO_VERIFY \
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

TMP_BASE="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}"
FETCH_TMP="$(mktemp -d "$TMP_BASE/hpfa-181-fetch.XXXXXX")" || fail "trusted_fetch_tempdir_create_failed"
cleanup(){ rm -rf "$FETCH_TMP"; }
trap cleanup EXIT
WORK_REPO="$FETCH_TMP/work"

clean_git clone --no-tags --no-recurse-submodules --single-branch --branch "$BRANCH" "$ORIGIN_URL" "$WORK_REPO" >/dev/null
REMOTE_HEAD="$(clean_git -C "$WORK_REPO" rev-parse HEAD 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi
EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"

[[ -z "$(clean_git -C "$WORK_REPO" status --porcelain --untracked-files=all --ignored=matching)" ]] || fail "trusted_worktree_not_clean:$WORK_REPO"
RUNNER="$WORK_REPO/tools/run_active_match_aggregate_definition_alignment_v1.sh"
[[ -x "$RUNNER" ]] || fail "aggregate_definition_alignment_runner_not_executable:$RUNNER"

# Evidence execution also starts with a clean process environment so inherited
# PYTHONPATH/PYTHONHOME/Git variables cannot inject code or repository state.
env -i \
  HOME="${HOME:-}" \
  PATH="/data/data/com.termux/files/usr/bin:/system/bin" \
  TMPDIR="$TMP_BASE" \
  PYTHONNOUSERSITE=1 \
  HPFA_REPO="$WORK_REPO" \
  HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
  HPFA_PHONE_OUTPUT="$OUT" \
  HPFA_EXPECTED_BRANCH="$BRANCH" \
  HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
  "$RUNNER"
