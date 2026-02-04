from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

_SPEC_CACHE: Dict[str, Any] | None = None

def read_spec() -> Dict[str, Any]:
    global _SPEC_CACHE
    if _SPEC_CACHE is not None:
        return _SPEC_CACHE
    p = Path(__file__).resolve().parent / "config" / "spec.json"
    if not p.exists():
        _SPEC_CACHE = {"hp_motor": {"version": "missing", "ontology_version": "missing"}}
        return _SPEC_CACHE
    with p.open("r", encoding="utf-8") as f:
        _SPEC_CACHE = json.load(f)
        return _SPEC_CACHE
