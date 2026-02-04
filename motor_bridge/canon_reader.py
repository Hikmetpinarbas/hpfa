from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class CanonReadResult:
    payload: Dict[str, Any]


def read_canon_json(path: Path) -> CanonReadResult:
    """
    Canon read entrypoint.
    For now: minimal JSON read with fail-closed semantics.
    Next: enforce HP-CDL schema and epistemic_meta gates.
    """
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Canon root must be an object")
    return CanonReadResult(payload=data)
