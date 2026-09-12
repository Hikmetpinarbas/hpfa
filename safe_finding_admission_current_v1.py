from __future__ import annotations

import argparse
import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
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
