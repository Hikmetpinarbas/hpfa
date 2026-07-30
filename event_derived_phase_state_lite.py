from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPL = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "event_derived_phase_state_lite"
    / "src"
    / "event_derived_phase_state.py"
)

spec = importlib.util.spec_from_file_location("hpfa_event_derived_phase_state_impl", IMPL)
if spec is None or spec.loader is None:
    raise RuntimeError("event_derived_phase_state_implementation_unloadable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

main = module.main

if __name__ == "__main__":
    raise SystemExit(main())
