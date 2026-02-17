#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "${HPFA_REPO:-$HOME/hpfa}" || exit 2

TAG="${1:-hpfa-stable-$(date +%Y%m%d)}"
MSG="${2:-stable: doctor-gated release}"

# refuse dirty tree
git diff --quiet && git diff --cached --quiet || { echo "[FAIL] dirty tree"; exit 11; }

git tag -f -a "$TAG" -m "$MSG" HEAD
git push -f origin "refs/tags/$TAG"

echo "[OK] tagged+pushed $TAG -> $(git rev-parse --short HEAD)"
