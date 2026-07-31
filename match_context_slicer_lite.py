from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPL = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "match_context_slicer_lite"
    / "src"
    / "match_context_slicer.py"
)

spec = importlib.util.spec_from_file_location("hpfa_match_context_slicer_impl", IMPL)
if spec is None or spec.loader is None:
    raise RuntimeError("match_context_slicer_implementation_unloadable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

build_match_context_slicer = module.build_match_context_slicer
write_outputs = module.write_outputs
main = module.main

if __name__ == "__main__":
    raise SystemExit(main())
