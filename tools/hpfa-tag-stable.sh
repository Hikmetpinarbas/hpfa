#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

TAG="${1:-}"
if [ -z "$TAG" ]; then
  echo "[FAIL] usage: hpfa-tag-stable.sh hpfa-stable-YYYYMMDD"
  exit 2
fi

cd "$HOME/hpfa"
git diff --quiet && git diff --cached --quiet || { echo "[FAIL] dirty tree"; exit 11; }

git tag -f -a "$TAG" -m "stable: retag to HEAD" HEAD
git push -f origin "refs/tags/$TAG"
git show -s --decorate --oneline HEAD
