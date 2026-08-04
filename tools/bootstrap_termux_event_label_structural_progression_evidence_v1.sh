#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
BRANCH="agent/event-label-structural-progression-evidence-lite-v1"
REPO="${HPFA_REPO:-$HOME/hpfa_claim_integrity/hpfa}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"
STATE="$OUT/event_label_structural_progression_bootstrap_state_v1.txt"
CONSOLE="$OUT/event_label_structural_progression_bootstrap_console_v1.log"
RUNNER_STATE="$OUT/event_label_structural_progression_evidence_operator_state_v1.txt"
BUNDLE="$OUT/event_label_structural_progression_evidence_bundle_v1.zip"

write_state() {
  local status="$1"
  local reason="$2"
  local rc="$3"
  local line="${4:-}"
  local command="${5:-}"
  {
    echo "status=$status"
    echo "reason=$reason"
    echo "exit_code=$rc"
    [[ -n "$line" ]] && echo "failed_line=$line"
    [[ -n "$command" ]] && echo "failed_command=$command"
    echo "product_repo=$REPO"
    echo "branch=$BRANCH"
    echo "runtime_authority=$ACTIVE_MATCH"
    echo "phone_output=$OUT"
    echo "canonical_event_count=UNKNOWN"
    echo "production_release=false"
  } > "$STATE"
}

fail() {
  local reason="$1"
  trap - ERR
  mkdir -p "$OUT" 2>/dev/null || true
  write_state "FAILED" "$reason" 2
  cat "$STATE" >&2
  exit 2
}

on_error() {
  local rc=$?
  local line="${BASH_LINENO[0]:-${LINENO}}"
  local command="${BASH_COMMAND:-unknown}"
  trap - ERR
  mkdir -p "$OUT" 2>/dev/null || true
  write_state "FAILED" "bootstrap_command_failed" "$rc" "$line" "$command"
  cat "$STATE" >&2
  exit "$rc"
}
trap on_error ERR

normalize_origin() {
  local origin="${1:-}"
  origin="${origin%/}"
  origin="${origin%.git}"
  origin="${origin#https://github.com/}"
  origin="${origin#http://github.com/}"
  origin="${origin#git@github.com:}"
  origin="${origin#ssh://git@github.com/}"
  printf '%s\n' "${origin,,}"
}

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  */HPFA/*) fail "nested_phone_output_directory_rejected" ;;
  *) fail "phone_output_directory_not_allowed:$OUT" ;;
esac
mkdir -p "$OUT"
rm -f "$STATE" "$CONSOLE"
exec > >(tee "$CONSOLE") 2>&1

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"
if [[ -e "$REPO" && ! -d "$REPO/.git" ]]; then
  fail "product_repo_path_exists_but_is_not_git:$REPO"
fi
if [[ ! -d "$REPO/.git" ]]; then
  mkdir -p "$(dirname "$REPO")"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO"
fi

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean:$REPO"

git -C "$REPO" fetch --prune origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH")"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch --track -c "$BRANCH" "origin/$BRANCH"
fi
git -C "$REPO" reset --hard "$REMOTE_HEAD"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$BRANCH"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$REMOTE_HEAD"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean_after_reset:$REPO"

if ! python - <<'PY'
import openpyxl
import pytest
print(f"openpyxl_version={openpyxl.__version__}")
print(f"pytest_version={pytest.__version__}")
PY
then
  python -m pip install --upgrade openpyxl pytest
fi

export HPFA_REPO="$REPO"
export HPFA_ACTIVE_MATCH="$ACTIVE_MATCH"
export HPFA_EXPECTED_ACTIVE_MATCH="$EXPECTED_ACTIVE_MATCH"
export HPFA_PHONE_OUTPUT="$OUT"
export HPFA_EXPECTED_BRANCH="$BRANCH"
export HPFA_EXPECTED_HEAD="$ACTUAL_HEAD"

{
  echo "status=READY"
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$HPFA_EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "phone_output=$OUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$STATE"

set +e
bash "$REPO/tools/run_active_match_event_label_structural_progression_evidence_v1.sh"
RUN_RC=$?
set -e

if [[ "$RUN_RC" -ne 0 ]]; then
  {
    echo "status=RUNTIME_FAILED"
    echo "reason=runtime_runner_returned_nonzero"
    echo "runner_rc=$RUN_RC"
    echo "runner_state=$RUNNER_STATE"
    echo "console_log=$CONSOLE"
    echo "product_repo=$REPO"
    echo "branch=$ACTUAL_BRANCH"
    echo "head_sha=$ACTUAL_HEAD"
    echo "runtime_authority=$ACTIVE_MATCH"
    echo "canonical_event_count=UNKNOWN"
    echo "production_release=false"
  } | tee "$STATE" >&2
  trap - ERR
  exit "$RUN_RC"
fi

[[ -f "$BUNDLE" ]] || fail "runtime_completed_without_bundle:$BUNDLE"
{
  echo "status=COMPLETED"
  echo "runner_rc=0"
  echo "bundle=$BUNDLE"
  echo "console_log=$CONSOLE"
  echo "product_repo=$REPO"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$STATE"
trap - ERR
exit 0
