#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
BRANCH="agent/provider-semantic-provenance-reconciliation-hardening-v1"
REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="/sdcard/Download/HPFA"

fail() {
  mkdir -p "$OUT" 2>/dev/null || true
  printf 'FAIL: %s\n' "$1" | tee "$OUT/cross_format_reconciliation_bootstrap_v1.txt" >&2
  exit 2
}

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

verify_python_dependencies() {
  python - <<'PY'
import openpyxl, pytest
print(f"openpyxl_version={openpyxl.__version__}")
print(f"pytest_version={pytest.__version__}")
PY
}

ensure_python_dependencies() {
  if verify_python_dependencies; then
    return
  fi

  if ! python -m pip --version >/dev/null 2>&1; then
    command -v pkg >/dev/null 2>&1 || fail "python_pip_missing_and_pkg_unavailable"
    pkg install -y python-pip || fail "python_pip_install_failed"
  fi

  python -m pip install --upgrade openpyxl pytest \
    || fail "python_dependencies_install_failed"
  verify_python_dependencies \
    || fail "python_dependencies_import_failed_after_install"
}

[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
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
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "product_repo_worktree_not_clean:$REPO"

git -C "$REPO" fetch origin "$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
[[ "$REMOTE_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "remote_head_missing_or_invalid:$REMOTE_HEAD"

REQUESTED_EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
if [[ -n "$REQUESTED_EXPECTED_HEAD" ]]; then
  [[ "$REQUESTED_EXPECTED_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] \
    || fail "requested_expected_head_invalid:$REQUESTED_EXPECTED_HEAD"
  [[ "$REQUESTED_EXPECTED_HEAD" == "$REMOTE_HEAD" ]] \
    || fail "remote_head_mismatch:$REMOTE_HEAD expected:$REQUESTED_EXPECTED_HEAD"
fi

if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch --track "origin/$BRANCH"
fi
git -C "$REPO" merge --ff-only "origin/$BRANCH" \
  || fail "product_repo_non_fast_forward:$REPO"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$BRANCH"
[[ "$ACTUAL_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "fetched_head_missing_or_invalid:$ACTUAL_HEAD"
[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]] \
  || fail "product_repo_head_not_remote_head:$ACTUAL_HEAD remote:$REMOTE_HEAD"

HPFA_REPO="$REPO"
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH"
HPFA_PHONE_OUTPUT="$OUT"
HPFA_EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"
export HPFA_REPO HPFA_ACTIVE_MATCH HPFA_PHONE_OUTPUT HPFA_EXPECTED_HEAD

[[ "$HPFA_EXPECTED_HEAD" == "$ACTUAL_HEAD" ]] || fail "bootstrap_expected_head_export_mismatch"
ensure_python_dependencies
mkdir -p "$OUT"
{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "expected_head_sha=$HPFA_EXPECTED_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "bootstrap_status=READY"
} | tee "$OUT/cross_format_reconciliation_bootstrap_v1.txt"

bash "$REPO/tools/run_active_match_cross_format_reconciliation_v1.sh"
