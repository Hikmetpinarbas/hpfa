#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_URL="https://github.com/Hikmetpinarbas/hpfa.git"
EXPECTED_REPO_SLUG="hikmetpinarbas/hpfa"
BRANCH="${HPFA_EXPECTED_BRANCH:-}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"
REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
OUT="/sdcard/Download/HPFA"

fail(){ mkdir -p "$OUT" 2>/dev/null || true; printf 'FAIL: %s\n' "$1" | tee "$OUT/provider_alias_field_semantics_bootstrap_v1.txt" >&2; exit 2; }
normalize_origin(){
  local o="${1:-}"; o="${o%/}"; o="${o%.git}"
  o="${o#https://github.com/}"; o="${o#http://github.com/}"
  o="${o#git@github.com:}"; o="${o#ssh://git@github.com/}"
  printf '%s\n' "${o,,}"
}

[[ -n "$BRANCH" ]] || fail "expected_branch_required:set_HPFA_EXPECTED_BRANCH"
[[ -n "$EXPECTED_HEAD" ]] || fail "expected_head_required:set_HPFA_EXPECTED_HEAD"
[[ -d "$ACTIVE_MATCH" ]] || fail "active_match_runtime_missing:$ACTIVE_MATCH"
if [[ -e "$REPO" && ! -d "$REPO/.git" ]]; then fail "product_repo_path_exists_but_is_not_git:$REPO"; fi
if [[ ! -d "$REPO/.git" ]]; then
  mkdir -p "$(dirname "$REPO")"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO"
fi

ORIGIN_URL="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(normalize_origin "$ORIGIN_URL")"
[[ "$ORIGIN_SLUG" == "$EXPECTED_REPO_SLUG" ]] || fail "product_repo_origin_mismatch:$ORIGIN_URL"
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || fail "product_repo_worktree_not_clean:$REPO"

git -C "$REPO" fetch origin "$BRANCH"
REMOTE_HEAD="$(git -C "$REPO" rev-parse "origin/$BRANCH")"
[[ "$REMOTE_HEAD" == "$EXPECTED_HEAD" ]] || fail "remote_head_mismatch:$REMOTE_HEAD expected:$EXPECTED_HEAD"

if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" switch "$BRANCH"
else
  git -C "$REPO" switch --track "origin/$BRANCH"
fi
git -C "$REPO" merge --ff-only "origin/$BRANCH"

ACTUAL_BRANCH="$(git -C "$REPO" branch --show-current)"
ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$BRANCH"
[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]] || fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"

if ! python - <<'PY'
import openpyxl, pytest
print(f"openpyxl_version={openpyxl.__version__}")
print(f"pytest_version={pytest.__version__}")
PY
then
  python -m pip install --upgrade openpyxl pytest
fi

mkdir -p "$OUT"
{
  echo "product_repo=$REPO"
  echo "origin_url=$ORIGIN_URL"
  echo "origin_slug=$ORIGIN_SLUG"
  echo "branch=$ACTUAL_BRANCH"
  echo "head_sha=$ACTUAL_HEAD"
  echo "runtime_authority=$ACTIVE_MATCH"
  echo "bootstrap_status=READY"
} | tee "$OUT/provider_alias_field_semantics_bootstrap_v1.txt"

HPFA_EXPECTED_BRANCH="$BRANCH" \
HPFA_EXPECTED_HEAD="$EXPECTED_HEAD" \
HPFA_REPO="$REPO" \
HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" \
HPFA_PHONE_OUTPUT="$OUT" \
bash "$REPO/tools/run_active_match_provider_alias_field_semantics_v1.sh"
