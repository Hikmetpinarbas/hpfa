#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
BRANCH="agent/outcome-support-bridge-lite-v1"
RUNTIME_ROOT="${HPFA_RUNTIME_ROOT:-$HOME/hpfa_claim_integrity/hpfa}"
DEFAULT_REPO="$HOME/hp/repos/hpfa"
FALLBACK_REPO="$HOME/hp/repos/hpfa_outcome_support_bridge_checkout"
REPO_SOURCE="environment"
if [[ -n "${HPFA_REPO:-}" ]]; then
  REPO="$HPFA_REPO"
else
  REPO="$DEFAULT_REPO"
  REPO_SOURCE="default_product_checkout"
fi
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$RUNTIME_ROOT/runtime/active_single_match/current}"
EXPECTED_ACTIVE_MATCH="${HPFA_EXPECTED_ACTIVE_MATCH:-$RUNTIME_ROOT/runtime/active_single_match/current}"
OUT="${HPFA_PHONE_OUTPUT:-/sdcard/Download/HPFA}"

case "$OUT" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *)
    echo "FAIL_CLOSED:nested_phone_output_directory_rejected" >&2
    echo "canonical_event_count=UNKNOWN" >&2
    echo "production_release=false" >&2
    exit 2
    ;;
esac

STATE="$OUT/outcome_support_bridge_bootstrap_state_v1.txt"
CONSOLE="$OUT/outcome_support_bridge_bootstrap_console_v1.log"
RUNNER_STATE="$OUT/outcome_support_bridge_operator_state_v1.txt"
OUTPUT="$OUT/outcome_support_bridge_lite_v1.json"

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
    echo "product_repo_source=$REPO_SOURCE"
    echo "runtime_root=$RUNTIME_ROOT"
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

is_git_checkout() {
  local path="$1"
  git -C "$path" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

select_product_repo() {
  if [[ "$REPO" == "$RUNTIME_ROOT" || "$REPO" == "$RUNTIME_ROOT/"* ]]; then
    if [[ -n "${HPFA_REPO:-}" ]]; then
      fail "product_repo_must_be_outside_runtime_tree:$REPO"
    fi
    REPO="$FALLBACK_REPO"
    REPO_SOURCE="fallback_runtime_tree_separation"
  fi
  if [[ -e "$REPO" ]] && ! is_git_checkout "$REPO"; then
    if [[ -n "${HPFA_REPO:-}" ]]; then
      fail "explicit_product_repo_path_exists_but_is_not_git:$REPO"
    fi
    REPO="$FALLBACK_REPO"
    REPO_SOURCE="fallback_non_git_default"
  fi
  if [[ -e "$REPO" ]] && ! is_git_checkout "$REPO"; then
    fail "fallback_product_repo_path_exists_but_is_not_git:$REPO"
  fi
  [[ "$REPO" != "$RUNTIME_ROOT" && "$REPO" != "$RUNTIME_ROOT/"* ]] \
    || fail "product_repo_runtime_tree_overlap:$REPO"
}

mkdir -p "$OUT"
rm -f "$STATE" "$CONSOLE"
exec > >(tee "$CONSOLE") 2>&1

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
[[ -d "$EXPECTED_ACTIVE_MATCH" ]] || fail "expected_active_match_runtime_missing:$EXPECTED_ACTIVE_MATCH"
select_product_repo

if ! is_git_checkout "$REPO"; then
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
  echo "product_repo_source=$REPO_SOURCE"
  echo "runtime_root=$RUNTIME_ROOT"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "phone_output=$OUT"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$STATE"

set +e
bash "$REPO/tools/run_active_match_event_label_structural_progression_evidence_v1.sh"
UPSTREAM_RC=$?
set -e
[[ "$UPSTREAM_RC" -eq 0 ]] || fail "upstream_spine_returned_nonzero:$UPSTREAM_RC"

for required in \
  "$OUT/selected_action_consequence_surface_lite_v1.json" \
  "$OUT/selected_event_consequence_surface_lite_v1.json" \
  "$OUT/eventonly_sequence_consequence_result_v1.json"; do
  [[ -f "$required" ]] || fail "upstream_output_missing:$required"
done

set +e
bash "$REPO/tools/run_active_match_outcome_support_bridge_v1.sh"
RUN_RC=$?
set -e
if [[ "$RUN_RC" -ne 0 ]]; then
  {
    echo "status=RUNTIME_FAILED"
    echo "reason=runtime_runner_returned_nonzero"
    echo "upstream_rc=$UPSTREAM_RC"
    echo "runner_rc=$RUN_RC"
    echo "runner_state=$RUNNER_STATE"
    echo "console_log=$CONSOLE"
    echo "branch=$ACTUAL_BRANCH"
    echo "head_sha=$ACTUAL_HEAD"
    echo "runtime_authority=$ACTIVE_MATCH"
    echo "canonical_event_count=UNKNOWN"
    echo "production_release=false"
  } | tee "$STATE" >&2
  trap - ERR
  exit "$RUN_RC"
fi

[[ -f "$OUTPUT" ]] || fail "runtime_completed_without_output:$OUTPUT"
{
  echo "status=COMPLETED"
  echo "upstream_rc=0"
  echo "runner_rc=0"
  echo "output=$OUTPUT"
  echo "runner_state=$RUNNER_STATE"
  echo "console_log=$CONSOLE"
  echo "product_repo=$REPO"
  echo "product_repo_source=$REPO_SOURCE"
  echo "runtime_root=$RUNTIME_ROOT"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "canonical_event_count=UNKNOWN"
  echo "production_release=false"
} | tee "$STATE"
trap - ERR
exit 0
