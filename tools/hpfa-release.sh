#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hpfa}"
cd "$REPO" || { echo "[FAIL] repo not found: $REPO"; exit 2; }

TAG="${1:-hpfa-stable-$(date +%Y%m%d)}"
echo "[INFO] repo=$REPO"
echo "[INFO] tag=$TAG"

echo "--------------------------------"
echo "HPFA DOCTOR v2"
date --iso-8601=seconds 2>/dev/null || date
echo "--------------------------------"

fail=0

# 0) git sanity
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && echo "[OK] git repo" || { echo "[FAIL] git repo"; fail=$((fail+1)); }

# 1) sync check (best-effort fetch)
git fetch --all --prune >/dev/null 2>&1 || true
if git rev-list --left-right --count @{upstream}...HEAD >/dev/null 2>&1; then
  c="$(git rev-list --left-right --count @{upstream}...HEAD | tr -s " " | tr "\t" " ")"
  if [ "$c" = "0 0" ]; then
    echo "[OK] HEAD sync remote"
  else
    echo "[FAIL] HEAD not sync remote: $c"
    fail=$((fail+1))
  fi
else
  # if upstream missing, don't block release but warn
  echo "[WARN] upstream not set; skipping sync check"
fi

# 2) refuse dirty tree
if git diff --quiet && git diff --cached --quiet; then
  echo "[OK] clean tree"
else
  echo "[FAIL] dirty tree"
  fail=$((fail+1))
fi

# 3) commands exist
command -v hpfa-run >/dev/null 2>&1 && echo "[OK] hpfa-run found" || { echo "[FAIL] hpfa-run missing"; fail=$((fail+1)); }
command -v hpfa-set-primary >/dev/null 2>&1 && echo "[OK] hpfa-set-primary found" || { echo "[FAIL] hpfa-set-primary missing"; fail=$((fail+1)); }

# 4) PRIMARY_DIR info (non-fatal)
if [ -f "$HOME/.config/hpfa/primary.env" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.config/hpfa/primary.env"
fi
echo "[OK] PRIMARY_DIR=${PRIMARY_DIR:-EMPTY}"

# 5) python import check (non-fatal but counts on fail)
PY="$HOME/hpfa/.venv/bin/python"
if [ -x "$PY" ]; then
  if "$PY" - <<'PY'
import hpfa, hp_motor
print(hpfa.__file__)
print(hp_motor.__file__)
PY
  then
    echo "[OK] python import"
  else
    echo "[FAIL] python import"
    fail=$((fail+1))
  fi
else
  echo "[WARN] venv python not found at $PY (skipping import check)"
fi

# 6) guarded engine run (counts on fail)
if command -v hpfa-run >/dev/null 2>&1; then
  if out="$(hpfa-run 2>&1)"; then
    echo "$out" | sed -n '1,220p'
    echo "[OK] engine run ok"
  else
    echo "$out" | sed -n '1,220p'
    echo "[FAIL] engine run fail"
    fail=$((fail+1))
  fi
fi

# 7) OUT run count (non-fatal)
OUT="$HOME/hpfa/_out"
if [ -d "$OUT" ]; then
  n="$(find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' 2>/dev/null | wc -l | tr -d ' ')"
  echo "[OK] runs=$n"
else
  echo "[WARN] OUT missing: $OUT"
fi

# 8) PACK verify (SSOT) - counts on fail
if [ -x "$REPO/tools/hp_pack_verify.sh" ]; then
  if "$REPO/tools/hp_pack_verify.sh" >/dev/null; then
    echo "[OK] PACK checksum ok"
  else
    echo "[FAIL] PACK checksum fail"
    fail=$((fail+1))
  fi
else
  echo "[WARN] hp_pack_verify.sh missing; skipping PACK verify"
fi

# 9) github reachability (non-fatal)
if command -v ping >/dev/null 2>&1; then
  ping -c 1 github.com >/dev/null 2>&1 && echo "[OK] github reachable" || echo "[WARN] github not reachable"
else
  echo "[WARN] ping missing"
fi

echo "--------------------------------"
if [ "$fail" -eq 0 ]; then
  echo "[OK] RESULT=PASS"
else
  echo "[FAIL] RESULT=FAIL count=$fail"
  exit 11
fi

# Tag + push (only if PASS)
if [ -n "${TAG:-}" ]; then
  git tag -f -a "$TAG" -m "stable: doctor-gated release" HEAD
  git push -f origin "refs/tags/$TAG"
  echo "[OK] tagged+pushed $TAG -> $(git rev-parse --short HEAD)"
fi
