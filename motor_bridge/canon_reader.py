from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import importlib

from motor_bridge.policy import evaluate_epistemic_policy, Decision


@dataclass(frozen=True)
class CanonReadResult:
    payload: Dict[str, Any]
    epistemic_status: str
    lossy_mapping: bool
    assumption_id: Optional[str]
    human_override: bool
    decision: str
    decision_reason: str


def _load_contract_validator() -> Callable[[Dict[str, Any]], Any]:
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
        "No callable contract validator found in canon.definitions.contract_validator"
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
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Canon root must be an object")

    # 1) Contract validation (fail-closed)
    validator = _load_contract_validator()
    validator(data)

    # 2) Epistemic meta extraction (fail-closed)
    meta = _extract_epistemic_meta(data)

    epistemic_status = str(meta["epistemic_status"]).strip()
    lossy_mapping = bool(meta.get("lossy_mapping", False))
    human_override = bool(meta.get("human_override", False))
    assumption_id = (
        str(meta["assumption_id"]) if meta.get("assumption_id") is not None else None
    )

    # 3) Decision surface
    pd = evaluate_epistemic_policy(
        epistemic_status=epistemic_status,
        lossy_mapping=lossy_mapping,
        human_override=human_override,
        assumption_id=assumption_id,
    )

    if pd.decision == Decision.HARD_FAIL:
        raise ValueError(pd.reason)

    return CanonReadResult(
        payload=data,
        epistemic_status=epistemic_status,
        lossy_mapping=lossy_mapping,
        assumption_id=assumption_id,
        human_override=human_override,
        decision=pd.decision.value,
        decision_reason=pd.reason,
    )
