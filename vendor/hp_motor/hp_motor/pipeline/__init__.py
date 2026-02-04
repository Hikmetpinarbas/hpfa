"""
hp_motor.pipeline public API

Two entrypoints:
1) Legacy pipeline (expected by pytest): hp_motor/pipeline.py or hp_motor/pipeline_single.py -> run_pipeline(...)
2) HP_PLATFORM runner (spec/base-dir):   hp_motor/pipeline/run_pipeline.py -> run(...)

IMPORTANT:
- Do NOT import the submodule "hp_motor.pipeline.run_pipeline" here, because Python will
  attach it to the package attribute "run_pipeline" and shadow the legacy callable.
"""

from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List


def _pick_callable(obj):
    # Accept callable OR module that contains callable.
    if callable(obj):
        return obj
    if isinstance(obj, ModuleType):
        for name in ("run_pipeline", "run"):
            fn = getattr(obj, name, None)
            if callable(fn):
                return fn
    return None


def _load_legacy_run_pipeline():
    hp_root = Path(__file__).resolve().parent.parent  # hp_motor/
    candidates = [
        hp_root / "pipeline.py",
        hp_root / "pipeline_single.py",
    ]
    legacy_path = next((p for p in candidates if p.exists()), None)
    if legacy_path is None:
        raise ImportError(f"Legacy pipeline not found. Tried: {', '.join(map(str, candidates))}")

    loader = SourceFileLoader("hp_motor._legacy_pipeline", str(legacy_path))
    spec = spec_from_loader(loader.name, loader)
    if spec is None:
        raise ImportError("Could not create import spec for legacy pipeline")

    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]

    raw = getattr(mod, "run_pipeline", None)
    fn = _pick_callable(raw)
    if fn is None:
        fn = _pick_callable(getattr(mod, "run", None))

    if fn is None:
        raise ImportError(f"Legacy pipeline has no callable run_pipeline/run(): {legacy_path}")

    return fn


# Tests expect: from hp_motor.pipeline import run_pipeline
run_pipeline = _load_legacy_run_pipeline()


def run_hp_platform(spec_path: str, base_dir: str, out_path: str, team_names: List[str]) -> Dict[str, Any]:
    """
    Lazy-import HP_PLATFORM runner to avoid shadowing the legacy 'run_pipeline' symbol.
    """
    from importlib import import_module
    m = import_module("hp_motor.pipeline.run_pipeline")  # this will set package.run_pipeline attribute,
    # BUT only when you explicitly call this function (tests won't).
    fn = getattr(m, "run", None)
    if not callable(fn):
        raise ImportError("hp_motor.pipeline.run_pipeline has no callable 'run'")
    return fn(spec_path, base_dir, out_path, team_names)


__all__ = ["run_pipeline", "run_hp_platform"]
