#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hp/repos/hpfa}"
BRANCH="csv-surface-reader-lite-v1"
ACTIVE_MATCH="${HPFA_ACTIVE_MATCH:-$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current}"
EXPECTED="hikmetpinarbas/hpfa"

normalize_origin() {
  local origin="$1"
  origin="${origin%.git}"
  origin="${origin%/}"
  origin="${origin#https://github.com/}"
  origin="${origin#http://github.com/}"
  origin="${origin#git@github.com:}"
  printf '%s' "${origin,,}"
}

[[ -d "$ACTIVE_MATCH" ]] || { echo "active_match_runtime_missing"; exit 2; }
mkdir -p "$(dirname "$REPO")"
if [[ ! -d "$REPO/.git" ]]; then
  git clone https://github.com/Hikmetpinarbas/hpfa.git "$REPO"
fi
ORIGIN="$(git -C "$REPO" remote get-url origin)"
[[ "$(normalize_origin "$ORIGIN")" == "$EXPECTED" ]] || { echo "product_repo_origin_mismatch:$ORIGIN"; exit 2; }
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || { echo "product_repo_worktree_not_clean"; exit 2; }
git -C "$REPO" fetch origin "$BRANCH"
git -C "$REPO" switch "$BRANCH" 2>/dev/null || git -C "$REPO" switch --track "origin/$BRANCH"
git -C "$REPO" pull --ff-only origin "$BRANCH"

echo "product_repo=$REPO"
echo "origin_url=$ORIGIN"
echo "branch=$BRANCH"
echo "head_sha=$(git -C "$REPO" rev-parse HEAD)"
echo "runtime_authority=$ACTIVE_MATCH"
echo "bootstrap_status=READY"

HPFA_REPO="$REPO" HPFA_ACTIVE_MATCH="$ACTIVE_MATCH" bash "$REPO/tools/run_active_match_csv_surface_reader_v1.sh"
