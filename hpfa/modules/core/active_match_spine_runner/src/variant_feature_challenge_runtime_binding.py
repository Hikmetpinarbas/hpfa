from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)

FEATURE_DELTA_JSON = "grammar_stable_variant_feature_delta_projection_v1.json"
PROCESS_VARIANT_JSON = "observable_process_variant_binding_projection_v1.json"
OUTPUT_JSON = "variant_feature_challenge_projection_v1.json"


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def materialize_variant_feature_challenge(out_dir: str | Path) -> dict[str, Any]:
    """Materialize the existing challenge projection from current full-spine artifacts.

    This is a binding step only. It does not discover observations, reconstruct sequences,
    recompute feature deltas, create independent evidence, or authorize a professional
    finding.
    """
    output = Path(out_dir).expanduser().resolve(strict=False)
    feature_path = output / FEATURE_DELTA_JSON
    process_path = output / PROCESS_VARIANT_JSON
    target = output / OUTPUT_JSON

    feature_payload = _load(feature_path)
    process_payload = _load(process_path)
    missing = [
        path.name
        for path, payload in (
            (feature_path, feature_payload),
            (process_path, process_payload),
        )
        if not payload
    ]

    if missing:
        if target.is_file():
            target.unlink()
        return {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "required_current_invocation_input_missing",
            "missing_inputs": sorted(missing),
            "artifact_materialized": False,
            "projection_creates_new_evidence": False,
            "professional_finding_emit_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = build_variant_feature_challenge_projection(
        feature_payload,
        process_payload,
    )
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": report.get("status"),
        "artifact_materialized": True,
        "output": str(target),
        "variant_feature_challenge_record_count": int(
            report.get("variant_feature_challenge_record_count") or 0
        ),
        "projection_creates_new_evidence": False,
        "difference_rows_are_independent_evidence_votes": False,
        "professional_finding_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
