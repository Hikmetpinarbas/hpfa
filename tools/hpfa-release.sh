#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="$HOME/hpfa"
TAG_PREFIX="hpfa-stable"
DATE_TAG="$(date +%Y%m%d)"
TAG="${TAG_PREFIX}-${DATE_TAG}"

cd "$REPO"

echo "[INFO] repo=$(pwd)"
echo "[INFO] tag=$TAG"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[FAIL] working tree dirty. Commit/stash first."
  git status -sb
  exit 11
fi

if [ -x tools/hpfa-doctor ]; then
  tools/hpfa-doctor
else
  echo "[FAIL] missing tools/hpfa-doctor"
  exit 12
fi

if [ -x tools/hpfa-tests.sh ]; then
  tools/hpfa-tests.sh
else
  echo "[WARN] tools/hpfa-tests.sh missing; skipping tests"
fi

git fetch --all --prune >/dev/null 2>&1 || true
AHEAD_BEHIND="$(git rev-list --left-right --count @{upstream}...HEAD 2>/dev/null || echo "0 0")"
echo "[INFO] upstream divergence: $AHEAD_BEHIND"

git tag -f -a "$TAG" -m "stable: doctor pass + release ($TAG)" HEAD

git push origin HEAD
git push -f origin "refs/tags/$TAG"

echo "[OK] release complete"
git show -s --decorate --oneline HEAD
git ls-remote --tags origin | grep -E "refs/tags/${TAG}(\^\{\})?$" || true
