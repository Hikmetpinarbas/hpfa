from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import importlib


@dataclass(frozen=True)
class CanonReadResult:
    payload: Dict[str, Any]
    epistemic_status: str
    lossy_mapping: bool
    assumption_id: Optional[str]
    human_override: bool


def _load_contract_validator() -> Callable[[Dict[str, Any]], Any]:
    """
    Fail-closed: if we can't find a validator callable, we raise.
    We intentionally avoid hard-coding the function name; we probe common names.
    """
    mod = importlib.import_module("canon.definitions.contract_validator")

    candidates = [
        "validate_contract",
        "validate",
        "validate_instance",
        "validate_payload",
        "validate_canon",
    ]
    for name in candidates:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn

    raise RuntimeError(
        "No callable contract validator found in canon.definitions.contract_validator. "
        "Expected one of: " + ", ".join(candidates)
    )


def _extract_epistemic_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    meta = payload.get("epistemic_meta")
    if not isinstance(meta, dict):
        raise ValueError("Canon missing required object: epistemic_meta")

    status = meta.get("epistemic_status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("Canon epistemic_meta.epistemic_status is required")

    return meta


def read_canon_json(path: Path) -> CanonReadResult:
    """
    Canon read entrypoint.
    A5.1: contract-enforced + epistemic gate (fail-closed).
    """
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Canon root must be an object")

    # 1) Contract validation (fail-closed)
    validator = _load_contract_validator()
    validator(data)  # must raise on invalid

    # 2) Epistemic gate (fail-closed)
    meta = _extract_epistemic_meta(data)

    return CanonReadResult(
        payload=data,
        epistemic_status=str(meta["epistemic_status"]).strip(),
        lossy_mapping=bool(meta.get("lossy_mapping", False)),
        assumption_id=(str(meta["assumption_id"]) if meta.get("assumption_id") is not None else None),
        human_override=bool(meta.get("human_override", False)),
    )
