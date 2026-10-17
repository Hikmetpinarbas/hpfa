"""'If played today' counterfactual layer — kept apart from observation.

This layer never edits, extends or re-labels observed rows. It consumes
observed-layer summaries by reference (event ids) and records every assumption
explicitly. Numeric projections are refused unless a registered, validated
model id is supplied; without one the output is a structured hypothesis frame.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hvi_contract import COUNTERFACTUAL_LAYER, OBSERVED_LAYER, VERIFIED_STATES

OUTPUT_NAME = "counterfactual_today_scenario_v1.json"


def build_counterfactual(
    observed_events: list[dict[str, Any]],
    assumptions: list[dict[str, str]],
    question: str,
    model_registry: dict[str, dict[str, Any]] | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    if any(e.get("layer") != OBSERVED_LAYER for e in observed_events):
        raise ValueError("counterfactual_input_must_be_observed_layer_rows")
    if not assumptions or any(not a.get("id") or not a.get("statement") for a in assumptions):
        raise ValueError("counterfactual_requires_explicit_assumptions")
    verified = [e for e in observed_events if e.get("verification_status") in VERIFIED_STATES]
    registry = model_registry or {}
    model = registry.get(model_id) if model_id else None
    numeric_allowed = bool(model and model.get("validation_status") == "VALIDATED")
    by_type: dict[str, int] = {}
    for e in verified:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    return {
        "layer": COUNTERFACTUAL_LAYER,
        "evidence_kind": "MODEL_OUTPUT" if numeric_allowed else "HYPOTHESIS",
        "question": question,
        "observed_basis": {
            "observed_layer": OBSERVED_LAYER,
            "verified_event_ids": [e["event_id"] for e in verified],
            "verified_event_counts_by_type": by_type,
            "candidate_rows_excluded": len(observed_events) - len(verified),
        },
        "assumptions": assumptions,
        "model_id": model_id if numeric_allowed else None,
        "numeric_projection_allowed": numeric_allowed,
        "numeric_projection": None,
        "refusal_reason": None if numeric_allowed else "no_registered_validated_counterfactual_model",
        "falsifiers_required": True,
        "mixed_with_observation": False,
        "claim_ceiling": "COUNTERFACTUAL_HYPOTHESIS_NOT_OBSERVATION",
    }


def write_counterfactual(out_dir: str | Path, payload: dict[str, Any]) -> Path:
    root = Path(out_dir)
    if "hpfa_surface" in root.parts:
        raise ValueError("counterfactual_must_not_be_written_into_observed_surface")
    if payload.get("layer") != COUNTERFACTUAL_LAYER:
        raise ValueError("not_a_counterfactual_payload")
    root.mkdir(parents=True, exist_ok=True)
    path = root / OUTPUT_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path
