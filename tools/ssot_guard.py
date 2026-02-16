import os, sys
from pathlib import Path

def fail(msg: str, code: int = 2):
    print("[FAIL]", msg); raise SystemExit(code)

def ok(msg: str):
    print("[OK]", msg)

HOME = Path.home()
SSOT_MOTOR = Path(os.environ.get("HPFA_MOTOR", HOME/"HP_PROJELERI/HP-Motor-main")).resolve()
SSOT_HPFA  = Path(os.environ.get("HPFA_WORK", HOME/"hpfa")).resolve()

try:
    import hp_motor
except Exception as e:
    fail(f"cannot import hp_motor: {e}")

motor_paths = list(getattr(hp_motor, "__path__", [])) if hasattr(hp_motor, "__path__") else []
motor_paths_res = [Path(x).resolve() for x in motor_paths]

ok(f"python={sys.executable}")
ok(f"SSOT_MOTOR={SSOT_MOTOR}")
ok(f"SSOT_HPFA={SSOT_HPFA}")
ok(f"hp_motor.__path__={motor_paths}")

if not motor_paths_res:
    fail("hp_motor has no __path__ (unexpected namespace state)")

if not any(str(x).startswith(str(SSOT_MOTOR)) for x in motor_paths_res):
    fail("hp_motor is NOT loaded from SSOT_MOTOR (drift detected)")

cwd = Path.cwd().resolve()
if str(SSOT_HPFA) not in str(cwd):
    print("[WARN] CWD is not under SSOT_HPFA. CWD=", cwd)

ok("SSOT_GUARD_PASS")
