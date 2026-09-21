from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import post_sequence_admission_finalizer_current_v1 as post_sequence_finalizer
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
    """Materialize the existing challenge projection and finalize current post-sequence admission.

    This binding/orchestration step links current challenge surfaces and carries their existing observation authority;
    reconstruct sequences, recompute feature deltas, create independent evidence, or
    authorize a professional finding. The post-sequence finalizer is deliberately run
    only after the current challenge artifact is materialized so Safe Finding admission
    and Analyst Output claim contracts consume the same invocation's challenge state.
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
            "post_sequence_admission_finalized": False,
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

    finalization = post_sequence_finalizer.finalize_post_sequence_admission(output)
    finalization_status = str(finalization.get("status") or "").upper()
    status = "FAIL_CLOSED" if finalization_status == "FAIL_CLOSED" else report.get("status")

    final_report = _load(target) if target.is_file() else {}
    final_challenge_count = int(final_report.get("variant_feature_challenge_record_count") if final_report else report.get("variant_feature_challenge_record_count") or 0)

    return {
        "status": status,
        "artifact_materialized": True,
        "output": str(target),
        "variant_feature_challenge_record_count": final_challenge_count,
        "pre_finalization_variant_feature_challenge_record_count": int(report.get("variant_feature_challenge_record_count") or 0),
        "final_artifact_accounting_bound": bool(final_report),
        "post_sequence_admission_finalized": finalization_status in {"PASS", "REVIEW_REQUIRED"},
        "post_sequence_admission_status": finalization.get("status"),
        "post_sequence_admission_reason": finalization.get("reason"),
        "post_sequence_expected_handoff_count": int(finalization.get("expected_handoff_count") or 0),
        "post_sequence_admission_count": int(finalization.get("admission_count") or 0),
        "post_sequence_claim_count": int(finalization.get("claim_count") or 0),
        "post_sequence_safe_finding_admission_consumed": (
            finalization.get("safe_finding_admission_consumed") is True
        ),
        "post_sequence_current_invocation_artifacts": [
            str(value)
            for value in (finalization.get("current_invocation_artifacts") or [])
            if str(value or "").strip()
        ],
        "projection_creates_new_evidence": False,
        "difference_rows_are_independent_evidence_votes": False,
        "post_sequence_finalization_creates_new_evidence": False,
        "post_sequence_finalization_can_authorize_emit": False,
        "professional_finding_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
