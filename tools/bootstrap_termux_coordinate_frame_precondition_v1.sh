#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PRODUCT_REPO="${HPFA_PRODUCT_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="agent/coordinate-frame-precondition-lite-v1"

[ -d "$PRODUCT_REPO/.git" ] || {
  printf 'status=FAIL_CLOSED\nreason=product_repo_missing_or_not_git\n' >&2
  exit 2
}
cd "$PRODUCT_REPO"
[ -z "$(git status --porcelain --untracked-files=no)" ] || {
  printf 'status=FAIL_CLOSED\nreason=tracked_worktree_dirty\n' >&2
  exit 2
}

git fetch origin "$BRANCH"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH" --track "origin/$BRANCH"
fi
git merge --ff-only "origin/$BRANCH"

export HPFA_EXPECTED_BRANCH="$BRANCH"
export HPFA_EXPECTED_HEAD="$(git rev-parse HEAD)"
exec bash tools/run_active_match_coordinate_frame_precondition_v1.sh
