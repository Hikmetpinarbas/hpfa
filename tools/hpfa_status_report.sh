#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
HPFA="$HOME/hpfa"
DIAG="$HPFA/_diag"
OUT="$HPFA/_out"
ARCH="$HOME/HP_ARCHIVES"

VENV_PY="$HPFA/.venv/bin/python"

echo "===== HPFA STATUS REPORT ====="
date
echo

echo "== RUNTIME =="
if [ -x "$VENV_PY" ]; then
  echo "[OK] venv python=$VENV_PY"
else
  echo "[FAIL] missing venv python=$VENV_PY"
fi
echo

echo "== IMPORT RESOLUTION =="
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" - <<'PY'
import sys
def show(mod):
  m=__import__(mod)
  p=getattr(m,"__file__",None)
  print(f"[OK] {mod}={p}")
show("hpfa")
show("hp_motor")
print("[OK] sys.path(head)=", sys.path[:10])
PY
else
  echo "[SKIP] venv missing; cannot import check"
fi
echo

echo "== BASELINES (locks + fingerprint) =="
for f in \
  "$DIAG/engine_artifacts.CORE.BASELINE.json" \
  "$DIAG/hp_projeleri_inventory.BASELINE.tsv" \
  "$DIAG/hp_projeleri_inventory.BASELINE.sig" \
; do
  if [ -f "$f" ]; then
    ls -l "$f"
  else
    echo "[FAIL] missing: $f"
  fi
done
if [ -f "$DIAG/engine_artifacts.CORE.BASELINE.json" ]; then
  echo
  echo "[INFO] core baseline fingerprint:"
  sed -n 's/.*"fingerprint_sha256":[[:space:]]*"\([^"]*\)".*/\1/p' "$DIAG/engine_artifacts.CORE.BASELINE.json" | head -n 1
fi
echo

echo "== OUT DIR HEALTH =="
if [ -d "$OUT" ]; then
  TOTAL="$(find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' | wc -l | tr -d ' ')"
  echo "[OK] OUT=$OUT"
  echo "[OK] engine_run_* count=$TOTAL"
  echo
  echo "[INFO] newest 8:"
  find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@\t%TY-%Tm-%Td %TH:%TM:%TS\t%f\n' \
    | sort -nr | head -n 8 | awk -F'\t' '{print "  " $2 "  " $3}'
  echo
  echo "[INFO] oldest 8:"
  find "$OUT" -maxdepth 1 -type d -name 'engine_run_*' -printf '%T@\t%TY-%Tm-%Td %TH:%TM:%TS\t%f\n' \
    | sort -n | head -n 8 | awk -F'\t' '{print "  " $2 "  " $3}'
else
  echo "[FAIL] missing OUT dir: $OUT"
fi
echo

echo "== ARCHIVE/QUARANTINE FOOTPRINT (top-level) =="
if [ -d "$ARCH" ]; then
  echo "[OK] ARCH=$ARCH"
  # en büyük 12 klasörü göster
  du -s "$ARCH"/* 2>/dev/null | sort -nr | head -n 12 | awk '{printf "  %8.1f MB  %s\n", $1/1024, $2}'
else
  echo "[WARN] missing ARCH: $ARCH"
fi
echo

echo "== DUPLICATE MODULE DIRS (hpfa / hp_motor) =="
echo "[INFO] hpfa dirs (first 30):"
find "$HOME" -type d -name hpfa 2>/dev/null | head -n 30 | sed 's/^/  /'
echo
echo "[INFO] hp_motor dirs (first 30):"
find "$HOME" -type d -name hp_motor 2>/dev/null | head -n 30 | sed 's/^/  /'
echo

echo "== QUICK HEALTH: GUARDED RUN (dry) =="
echo "[INFO] This will only validate guards + require PRIMARY_DIR; it will NOT guess paths."
if [ -z "${PRIMARY_DIR:-}" ]; then
  echo "[WARN] PRIMARY_DIR is empty; set it then run: hpfa-run"
else
  echo "[OK] PRIMARY_DIR=$PRIMARY_DIR"
  echo "[INFO] run: hpfa-run | tail -n 30"
fi

echo
echo "===== END REPORT ====="
