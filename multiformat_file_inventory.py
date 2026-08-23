from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent
IMPLEMENTATION_PATH = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "multiformat_file_inventory_lite"
    / "src"
    / "multiformat_file_inventory.py"
)
IMPLEMENTATION_MODULE_NAME = "_hpfa_multiformat_file_inventory_impl"


def _load_implementation() -> ModuleType:
    existing = sys.modules.get(IMPLEMENTATION_MODULE_NAME)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        IMPLEMENTATION_MODULE_NAME,
        IMPLEMENTATION_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"unable_to_load_multiformat_file_inventory:{IMPLEMENTATION_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[IMPLEMENTATION_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(IMPLEMENTATION_MODULE_NAME, None)
        raise
    return module


main = _load_implementation().main


if __name__ == "__main__":
    raise SystemExit(main())
