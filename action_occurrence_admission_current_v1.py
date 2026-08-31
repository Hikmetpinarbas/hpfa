from __future__ import annotations

import argparse
import json
from pathlib import Path

import cross_role_relation_candidate_resolver_current_v1 as current_relation
from hpfa.modules.core.action_occurrence_admission_lite.src import action_occurrence_admission as occurrence
from hpfa.modules.core.action_occurrence_admission_lite.src.conditional_review_passthrough import (
    build_action_occurrence_admission_with_conditional_review,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = occurrence.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    relation_payload = current_relation.runtime_write_outputs(input_dir, output)
    action_path = output / "semantic_role_action_bundle_candidates_lite_v1.json"
    taxonomy_path = output / "action_bundle_multi_family_review_taxonomy_lite_v1.json"

    if (
        relation_payload.get("status") == "FAIL_CLOSED"
        or not action_path.is_file()
        or not taxonomy_path.is_file()
    ):
        return {
            "module_id": occurrence.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": relation_payload.get("match_surface_binding_id"),
            "action_occurrence_candidates": [],
            "action_occurrence_candidate_count": 0,
            "admission_class_counts": {},
            "interaction_type_counts": {},
            "conditional_review_passthrough_record_count": 0,
            "conditional_review_passthrough_candidate_count": 0,
            "hard_block_hits": ["current_relation_or_required_action_outputs_missing"],
            "review_hits": [],
            "precision_first_exact_rule_policy": True,
            "near_time_or_space_admission_enabled": False,
            "probability_output_allowed": False,
            "same_time_total_order_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "coordinate_is_physical_player_position": False,
            "independent_csv_xml_vote_allowed": False,
            "action_occurrence_candidate_is_event_truth": False,
            "validated_event_identity": False,
            "event_instance_count": 0,
            "count_value_output_allowed": False,
            "claim_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_relation_status": relation_payload.get("status"),
        }

    action_payload = _load(action_path)
    taxonomy_payload = _load(taxonomy_path)
    payload = build_action_occurrence_admission_with_conditional_review(
        action_payload,
        taxonomy_payload,
        relation_payload,
    )
    payload["current_relation_status"] = relation_payload.get("status")
    payload["current_taxonomy_status"] = relation_payload.get("current_taxonomy_status")
    payload["current_semantic_status"] = relation_payload.get("current_semantic_status")
    payload["active_match_evidence_pass"] = False
    paths = occurrence.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current Action Bundle + Taxonomy + Cross-Role Relation to Action Occurrence Admission"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "current_relation_status": payload.get("current_relation_status"),
                "action_occurrence_candidate_count": payload.get("action_occurrence_candidate_count"),
                "conditional_review_passthrough_record_count": payload.get("conditional_review_passthrough_record_count", 0),
                "conditional_review_passthrough_candidate_count": payload.get("conditional_review_passthrough_candidate_count", 0),
                "candidate_rejected_missing_primary_support_count": payload.get("candidate_rejected_missing_primary_support_count", 0),
                "admission_class_counts": payload.get("admission_class_counts") or {},
                "interaction_type_counts": payload.get("interaction_type_counts") or {},
                "hard_block_hits": payload.get("hard_block_hits") or [],
                "review_hits": payload.get("review_hits") or [],
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
