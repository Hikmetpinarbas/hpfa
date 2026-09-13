from __future__ import annotations

import argparse
import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.comparable_outcome_counterevidence_projection import (
    build_comparable_outcome_counterevidence,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
    apply_process_context_to_comparison,
    apply_process_participation_context,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_admission_projection import (
    build_safe_finding_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)

OUTPUT_NAME = "safe_finding_admission_projection_v1.json"
FEATURE_DELTA_NAME = "grammar_stable_variant_feature_delta_projection_v1.json"
PROCESS_VARIANT_NAME = "observable_process_variant_binding_projection_v1.json"
PROCESS_PARTICIPATION_NAME = "analyst_episode_process_participation_projection_v1.json"
OCCURRENCE_CONSEQUENCE_NAME = "occurrence_consequence_projection_v1.json"
CHALLENGE_NAME = "variant_feature_challenge_projection_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _bind_counterevidence_projection(source_payload: dict, projection: dict) -> dict:
    source_payload["comparable_outcome_counterevidence_status"] = projection.get("status")
    source_payload["comparable_outcome_counterevidence_records"] = list(
        projection.get("comparable_outcome_counterevidence_records") or []
    )
    source_payload["comparable_outcome_counterevidence_record_count"] = int(
        projection.get("comparable_outcome_counterevidence_record_count") or 0
    )
    source_payload["comparable_outcome_contrast_state_counts"] = dict(
        projection.get("comparable_outcome_contrast_state_counts") or {}
    )
    source_payload["comparison_eligible_outcome_record_count"] = int(
        projection.get("comparison_eligible_record_count") or 0
    )
    source_payload["comparable_counterevidence_candidate_count"] = int(
        projection.get("comparable_counterevidence_candidate_count") or 0
    )
    source_payload["counterevidence_independent_support_count"] = 0
    source_payload["counterevidence_is_independent_support"] = False
    source_payload["comparable_outcome_counterevidence_claim_ceiling"] = projection.get("claim_ceiling")
    source_payload["outcome_difference_is_failure_cause_truth"] = False
    source_payload["outcome_difference_is_tactical_pattern_truth"] = False
    source_payload["absence_is_counterevidence"] = False
    source_payload["safe_finding_handoff_candidates"] = list(
        projection.get("safe_finding_handoff_candidates") or []
    )
    source_payload["safe_finding_handoff_candidate_count"] = int(
        projection.get("safe_finding_handoff_candidate_count") or 0
    )
    source_payload["safe_finding_handoff_finding_status_counts"] = dict(
        projection.get("safe_finding_handoff_finding_status_counts") or {}
    )
    source_payload["professional_finding_emitted_count"] = int(
        projection.get("professional_finding_emitted_count") or 0
    )
    source_payload["safe_finding_handoff_professional_emit_allowed"] = False
    source_payload["safe_finding_handoff_claim_ceiling"] = projection.get(
        "safe_finding_handoff_claim_ceiling"
    )
    source_payload["counterexample_pair_count_is_independent_evidence_count"] = False
    source_payload["canonical_event_count"] = "UNKNOWN"
    source_payload["true_action_count"] = "UNKNOWN"
    source_payload["production_release"] = False
    return source_payload


def runtime_write_outputs(sequence_json: str | Path, out_dir: str | Path) -> dict:
    source_path = Path(sequence_json).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    source_payload = _load(source_path)
    feature_delta_path = output / FEATURE_DELTA_NAME
    process_variant_path = output / PROCESS_VARIANT_NAME
    process_participation_path = output / PROCESS_PARTICIPATION_NAME
    occurrence_consequence_path = output / OCCURRENCE_CONSEQUENCE_NAME
    challenge_path = output / CHALLENGE_NAME

    feature_delta_payload = _load(feature_delta_path)
    process_variant_payload = _load(process_variant_path)
    process_participation_payload = _load(process_participation_path)
    occurrence_consequence_payload = _load(occurrence_consequence_path)
    challenge_payload: dict | None = None
    process_context_counterevidence_recomputed = False
    process_context_counterevidence_fail_closed = False

    if source_payload and process_participation_payload and occurrence_consequence_payload:
        source_payload = apply_process_context_to_comparison(
            source_payload,
            process_participation_payload,
            occurrence_consequence_payload,
        )
        if source_payload.get("process_comparison_context_consumed") is True:
            counterevidence_projection = build_comparable_outcome_counterevidence(source_payload)
            if counterevidence_projection.get("status") == "FAIL_CLOSED":
                process_context_counterevidence_fail_closed = True
            else:
                source_payload = _bind_counterevidence_projection(
                    source_payload,
                    counterevidence_projection,
                )
                process_context_counterevidence_recomputed = True
                _write(source_path, source_payload)

    if source_payload and feature_delta_payload:
        feature_delta_payload = apply_process_participation_context(
            source_payload,
            feature_delta_payload,
            process_participation_payload or None,
            occurrence_consequence_payload or None,
        )
        _write(feature_delta_path, feature_delta_payload)

    if feature_delta_payload and process_variant_payload:
        challenge_payload = build_variant_feature_challenge_projection(
            feature_delta_payload,
            process_variant_payload,
        )
        _write(challenge_path, challenge_payload)

    if not source_payload:
        result = {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": ["sequence_payload_missing_or_invalid"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    elif process_context_counterevidence_fail_closed:
        result = {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": ["process_context_counterevidence_recompute_fail_closed"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        base_admission = build_safe_finding_admission(source_payload)
        result = apply_variant_feature_challenge_to_admission(
            source_payload,
            base_admission,
            challenge_payload,
            process_variant_payload or None,
        )

    target = output / OUTPUT_NAME
    _write(target, result)
    result["output"] = str(target)
    result["source_sequence_json"] = str(source_path)
    result["source_feature_delta_json"] = (
        str(feature_delta_path) if feature_delta_path.is_file() else None
    )
    result["source_process_variant_json"] = (
        str(process_variant_path) if process_variant_path.is_file() else None
    )
    result["source_process_participation_json"] = (
        str(process_participation_path) if process_participation_path.is_file() else None
    )
    result["source_occurrence_consequence_json"] = (
        str(occurrence_consequence_path) if occurrence_consequence_path.is_file() else None
    )
    result["source_variant_feature_challenge_json"] = (
        str(challenge_path) if challenge_path.is_file() else None
    )
    result["variant_feature_challenge_materialized"] = challenge_path.is_file()
    result["process_participation_context_enrichment_consumed"] = bool(
        feature_delta_payload.get("process_participation_context_enrichment_consumed")
    ) if feature_delta_payload else False
    result["process_participation_context_binding_state"] = (
        feature_delta_payload.get("process_participation_context_binding_state")
        if feature_delta_payload
        else "NOT_AVAILABLE"
    )
    result["process_context_feature_difference_appended_count"] = int(
        feature_delta_payload.get("process_context_feature_difference_appended_count") or 0
    ) if feature_delta_payload else 0
    result["process_comparison_context_consumed"] = source_payload.get(
        "process_comparison_context_consumed"
    ) is True if source_payload else False
    result["process_comparison_context_binding_state"] = (
        source_payload.get("process_comparison_context_binding_state")
        if source_payload
        else "NOT_AVAILABLE"
    )
    result["process_comparison_context_lowered_pair_count"] = int(
        source_payload.get("process_comparison_context_lowered_pair_count") or 0
    ) if source_payload else 0
    result["process_context_counterevidence_recomputed"] = process_context_counterevidence_recomputed
    result["process_context_can_create_new_pair"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA compact Safe Finding admission micro-gear")
    parser.add_argument("--sequence-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = runtime_write_outputs(args.sequence_json, args.out_dir)
    print(json.dumps({
        "status": result.get("status"),
        "safe_finding_admission_decision_count": result.get("safe_finding_admission_decision_count"),
        "finding_status_counts": result.get("finding_status_counts") or {},
        "professional_finding_emitted_count": result.get("professional_finding_emitted_count"),
        "claim_output_allowed_count": result.get("claim_output_allowed_count"),
        "variant_feature_challenge_consumed": result.get("variant_feature_challenge_consumed"),
        "variant_feature_challenge_materialized": result.get("variant_feature_challenge_materialized"),
        "process_participation_context_enrichment_consumed": result.get(
            "process_participation_context_enrichment_consumed"
        ),
        "process_participation_context_binding_state": result.get(
            "process_participation_context_binding_state"
        ),
        "process_context_feature_difference_appended_count": result.get(
            "process_context_feature_difference_appended_count", 0
        ),
        "process_comparison_context_consumed": result.get("process_comparison_context_consumed"),
        "process_comparison_context_binding_state": result.get(
            "process_comparison_context_binding_state"
        ),
        "process_comparison_context_lowered_pair_count": result.get(
            "process_comparison_context_lowered_pair_count", 0
        ),
        "process_context_counterevidence_recomputed": result.get(
            "process_context_counterevidence_recomputed"
        ),
        "hard_block_hits": result.get("hard_block_hits") or [],
        "review_hits": result.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "output": result.get("output"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
