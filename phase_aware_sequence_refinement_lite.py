from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPL = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "phase_aware_sequence_refinement_lite"
    / "src"
    / "phase_aware_sequence_refinement.py"
)

spec = importlib.util.spec_from_file_location("hpfa_phase_aware_refinement_impl", IMPL)
if spec is None or spec.loader is None:
    raise RuntimeError("phase_aware_sequence_refinement_implementation_unloadable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

build_phase_aware_sequence_refinement = module.build_phase_aware_sequence_refinement
write_outputs = module.write_outputs
main = module.main

if __name__ == "__main__":
    raise SystemExit(main())
