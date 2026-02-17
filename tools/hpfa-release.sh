#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hpfa}"
cd "$REPO" || { echo "[FAIL] repo not found: $REPO"; exit 2; }

TAG="${1:-hpfa-stable-$(date +%Y%m%d)}"
MSG="${2:-stable: doctor-gated release}"

echo "[INFO] repo=$REPO"
echo "[INFO] tag=$TAG"
echo "--------------------------------"
echo "HPFA DOCTOR v2"
ts="$(date --iso-8601=seconds 2>/dev/null || date)"
echo "$ts"
echo "--------------------------------"

fail=0

# helpers
note_fail(){ echo "[FAIL] $*"; fail=$((fail+1)); }
note_ok(){ echo "[OK] $*"; }
note_warn(){ echo "[WARN] $*"; }

# 0) git sanity
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && note_ok "git repo" || note_fail "git repo"

# 1) sync check (best-effort fetch)
git fetch --all --prune >/dev/null 2>&1 || true
if git rev-list --left-right --count @{upstream}...HEAD >/dev/null 2>&1; then
  c="$(git rev-list --left-right --count @{upstream}...HEAD | tr -s " " | tr "\t" " ")"
  [ "$c" = "0 0" ] && note_ok "HEAD sync remote" || note_fail "HEAD not sync remote: $c"
else
  note_warn "upstream not set; skipping sync check"
fi

# 2) refuse dirty tree
if git diff --quiet && git diff --cached --quiet; then
  note_ok "clean tree"
else
  note_fail "dirty tree"
fi

# 3) commands exist
command -v hpfa-run >/dev/null 2>&1 && note_ok "hpfa-run found" || note_fail "hpfa-run missing"
command -v hpfa-set-primary >/dev/null 2>&1 && note_ok "hpfa-set-primary found" || note_fail "hpfa-set-primary missing"

# 4) PRIMARY_DIR info (non-fatal)
if [ -f "$HOME/.config/hpfa/primary.env" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.config/hpfa/primary.env"
fi
note_ok "PRIMARY_DIR=${PRIMARY_DIR:-EMPTY}"

# 5) python import check (counts on fail if python exists)
PY="$HOME/hpfa/.venv/bin/python"
if [ -x "$PY" ]; then
  if "$PY" - <<'PY'
import hpfa, hp_motor
print(hpfa.__file__)
print(hp_motor.__file__)
PY
  then
    note_ok "python import"
  else
    note_fail "python import"
  fi
else
  note_warn "venv python not found at $PY (skipping import check)"
fi

# 6) guarded engine run (counts on fail)
if command -v hpfa-run >/dev/null 2>&1; then
  if out="$(hpfa-run 2>&1)"; then
    echo "$out" | sed -n "1,220p"
    note_ok "engine run ok"
  else
    echo "$out" | sed -n "1,220p"
    note_fail "engine run fail"
  fi
fi

# 7) OUT run count (non-fatal)
OUT="$HOME/hpfa/_out"
if [ -d "$OUT" ]; then
  n="$(find "$OUT" -maxdepth 1 -type d -name "engine_run_*" 2>/dev/null | wc -l | tr -d " ")"
  note_ok "runs=$n"
else
  note_warn "OUT missing: $OUT"
fi

# 8) PACK verify (SSOT) - counts on fail
if [ -x "$REPO/tools/hp_pack_verify.sh" ]; then
  if "$REPO/tools/hp_pack_verify.sh" >/dev/null; then
    note_ok "PACK checksum ok"
  else
    note_fail "PACK checksum fail"
  fi
else
  note_warn "hp_pack_verify.sh missing; skipping PACK verify"
fi

# 9) github reachability (non-fatal)
if command -v ping >/dev/null 2>&1; then
  ping -c 1 github.com >/dev/null 2>&1 && note_ok "github reachable" || note_warn "github not reachable"
else
  note_warn "ping missing"
fi

echo "--------------------------------"
if [ "$fail" -eq 0 ]; then
  note_ok "RESULT=PASS"
else
  note_fail "RESULT=FAIL count=$fail"
  # log history (fail too)
fi

# 10) doctor history (always append)
mkdir -p "$REPO/_diag"
H="$REPO/_diag/doctor_history.tsv"
head_sha="$(git rev-parse --short HEAD 2>/dev/null || echo NA)"
up_sha="$(git rev-parse --short @{upstream} 2>/dev/null || echo NA)"
printf "%s\t%s\t%s\t%s\t%s\t%d\t%s\n" "$ts" "$TAG" "$head_sha" "$up_sha" "$([ "$fail" -eq 0 ] && echo PASS || echo FAIL)" "$fail" "${PRIMARY_DIR:-EMPTY}" >> "$H"

# 11) If FAIL -> stop here
if [ "$fail" -ne 0 ]; then
  exit 11
fi

# 12) tag idempotency: only move tag if needed
cur_target="$(git rev-parse --short "$TAG^{}" 2>/dev/null || echo NONE)"
if [ "$cur_target" = "$head_sha" ]; then
  note_ok "tag already points to HEAD ($TAG -> $head_sha) (no-op)"
else
  git tag -f -a "$TAG" -m "$MSG" HEAD
  git push -f origin "refs/tags/$TAG"
  note_ok "tagged+pushed $TAG -> $head_sha"
fi

# 12b) immutable build tag (never force-move)
# format: hpfa-build-YYYYMMDD-HHMMSS (local time)
# Idempotent rule: if there is already ANY hpfa-build-* tag pointing at HEAD, do not create another.
if git tag --points-at "$head_sha" 2>/dev/null | grep -qE "^hpfa-build-"; then
  note_ok "build tag already exists for HEAD ($head_sha) (no-op)"
else
  BUILD_TAG="hpfa-build-$(date +%Y%m%d-%H%M%S)"
  if git rev-parse -q --verify "refs/tags/$BUILD_TAG" >/dev/null 2>&1; then
    note_fail "BUILD_TAG already exists: $BUILD_TAG (abort)"
    exit 12
  fi
  git tag -a "$BUILD_TAG" -m "build: immutable snapshot ($head_sha) @ $ts" "$head_sha"
  git push origin "refs/tags/$BUILD_TAG"
  note_ok "build tag pushed $BUILD_TAG -> $head_sha"
fi

# 13) PASS -> prune OUT (KEEP default 5)
KEEP="${KEEP:-5}"
if [ -x "$REPO/tools/hpfa_out_prune_apply.sh" ]; then
  KEEP="$KEEP" "$REPO/tools/hpfa_out_prune_apply.sh" apply || note_warn "out prune failed"
else
  note_warn "hpfa_out_prune_apply.sh missing; skipping prune"
fi
