#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
VENV_PY="$HOME/hpfa/.venv/bin/python"

HPFA_EXPECT_PREFIX="$HOME/HPFA_MASTER/base/hpfa-monorepo/src/hpfa/"
HPMOTOR_EXPECT_PREFIX="$HOME/HP_PROJELERI/HP-Motor-main/src/hp_motor/"

STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
  shift || true
fi

if [ ! -x "$VENV_PY" ]; then
  echo "[FAIL] missing venv python: $VENV_PY"
  exit 10
fi

"$VENV_PY" - <<PY
import sys, json
def fail(msg, code=20):
    print("[FAIL]", msg)
    raise SystemExit(code)

print("[OK] PY=", sys.executable)

try:
    import hpfa
except Exception as e:
    fail(f"cannot import hpfa: {e}", 21)

try:
    import hp_motor
except Exception as e:
    fail(f"cannot import hp_motor: {e}", 22)

hpfa_file = getattr(hpfa, "__file__", "")
hpm_file  = getattr(hp_motor, "__file__", "")

print("[OK] hpfa=", hpfa_file)
print("[OK] hp_motor=", hpm_file)

expect_hpfa = "${HPFA_EXPECT_PREFIX}"
expect_hpm  = "${HPMOTOR_EXPECT_PREFIX}"

hpfa_ok = hpfa_file.startswith(expect_hpfa)
hpm_ok  = hpm_file.startswith(expect_hpm)

print("[OK] hpfa_expected_prefix=", expect_hpfa)
print("[OK] hpmotor_expected_prefix=", expect_hpm)

print("[OK] sys.path(head)=", sys.path[:12])

if not hpfa_ok:
    print("[WARN] hpfa import path outside expected prefix")
if not hpm_ok:
    print("[WARN] hp_motor import path outside expected prefix")

strict = int("${STRICT}")
if strict and (not hpfa_ok or not hpm_ok):
    fail("import root mismatch under --strict", 30)

print("[OK] ENV_AUDIT_PASS")
PY
