import sys
from pathlib import Path
import importlib

HOME = Path("/data/data/com.termux/files/home").resolve()

SSOT_HPFA_SRC  = (HOME / "HPFA_MASTER/base/hpfa-monorepo/src").resolve()
SSOT_MOTOR_SRC = (HOME / "HP_PROJELERI/HP-Motor-main/src").resolve()

def fail(msg: str, code: int = 2):
    print("[FAIL]", msg)
    raise SystemExit(code)

def ok(msg: str):
    print("[OK]", msg)

def find_dups_on_syspath(pkg_dir_name: str):
    hits = []
    for p in map(Path, sys.path):
        try:
            if not p:
                continue
            pp = p.resolve()
        except Exception:
            continue
        cand = pp / pkg_dir_name
        if cand.is_dir():
            hits.append(str(cand))
    return sorted(set(hits))

def main():
    ok(f"python={sys.executable}")

    # --- imports ---
    for name in ("hpfa", "hp_motor"):
        try:
            m = importlib.import_module(name)
        except Exception as e:
            fail(f"cannot import {name}: {e}")
        ok(f"{name}.__file__={getattr(m,'__file__',None)}")
        ok(f"{name}.__path__={list(getattr(m,'__path__',[])) if hasattr(m,'__path__') else None}")

    # --- SSOT source check via sys.path visibility ---
    hpfa_hits = find_dups_on_syspath("hpfa")
    motor_hits = find_dups_on_syspath("hp_motor")

    ok("sys.path hpfa dirs:")
    for h in hpfa_hits: print(" -", h)
    ok("sys.path hp_motor dirs:")
    for h in motor_hits: print(" -", h)

    # strict: must include SSOT and must be unique
    if not any(str(SSOT_HPFA_SRC) in h for h in hpfa_hits):
        fail(f"hpfa SSOT not visible on sys.path: expected under {SSOT_HPFA_SRC}")
    if not any(str(SSOT_MOTOR_SRC) in h for h in motor_hits):
        fail(f"hp_motor SSOT not visible on sys.path: expected under {SSOT_MOTOR_SRC}")

    # if multiple distinct package dirs visible, drift risk
    if len(hpfa_hits) > 1:
        fail(f"hpfa appears from multiple dirs on sys.path (drift risk): {hpfa_hits}")
    if len(motor_hits) > 1:
        fail(f"hp_motor appears from multiple dirs on sys.path (drift risk): {motor_hits}")

    ok("SSOT_GUARD_STRICT_PASS")

if __name__ == "__main__":
    main()
