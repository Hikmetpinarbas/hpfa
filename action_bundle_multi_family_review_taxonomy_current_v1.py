from __future__ import annotations

import argparse
import json
from pathlib import Path

import semantic_role_action_bundle_candidates_lite as current_semantic
from hpfa.modules.core.action_bundle_multi_family_review_taxonomy_lite.src import (
    action_bundle_multi_family_review_taxonomy as taxonomy,
)


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = taxonomy.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    semantic_payload = current_semantic.runtime_write_outputs(input_dir, output)
    if semantic_payload.get("status") == "FAIL_CLOSED":
        return {
            "module_id": taxonomy.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": semantic_payload.get("match_surface_binding_id"),
            "multi_family_review_records": [],
            "source_action_bundle_candidate_count": semantic_payload.get("action_bundle_candidate_count", 0),
            "source_review_bundle_record_count": semantic_payload.get("action_bundle_review_required_count", 0),
            "source_pass_bundle_record_count": semantic_payload.get("action_bundle_pass_count", 0),
            "multi_family_review_core_count": 0,
            "classified_candidate_core_count": 0,
            "review_required_core_count": 0,
            "coordinate_missing_core_count": 0,
            "classification_counts": {},
            "source_role_counts": {},
            "family_set_counts": {},
            "hard_block_hits": ["current_semantic_action_bundle_fail_closed"],
            "review_hits": [],
            "classification_is_event_truth": False,
            "family_parent_is_validated_action": False,
            "subtype_is_validated_action": False,
            "restart_coupling_is_event_fusion": False,
            "same_time_order_truth_admitted": False,
            "source_row_order_is_temporal_truth": False,
            "cross_role_fusion_allowed": False,
            "independent_source_vote_allowed": False,
            "event_instance_count": 0,
            "claim_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_semantic_status": semantic_payload.get("status"),
        }

    payload = taxonomy.build_action_bundle_multi_family_review_taxonomy(semantic_payload)
    payload["current_semantic_status"] = semantic_payload.get("status")
    payload["current_semantic_route_record_count"] = semantic_payload.get("semantic_route_record_count")
    payload["current_action_bundle_candidate_count"] = semantic_payload.get("action_bundle_candidate_count")
    payload["current_action_bundle_review_required_count"] = semantic_payload.get("action_bundle_review_required_count")
    payload["current_cross_role_relation_candidate_count"] = semantic_payload.get("cross_role_relation_candidate_count")
    payload["current_content_source_role_bridge_status"] = semantic_payload.get("current_content_source_role_bridge_status")
    payload["active_match_evidence_pass"] = False
    paths = taxonomy.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current Action Bundle to Multi-Family Review Taxonomy migration")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_semantic_status": payload.get("current_semantic_status"),
        "source_review_bundle_record_count": payload.get("source_review_bundle_record_count"),
        "multi_family_review_core_count": payload.get("multi_family_review_core_count"),
        "classified_candidate_core_count": payload.get("classified_candidate_core_count"),
        "review_required_core_count": payload.get("review_required_core_count"),
        "coordinate_missing_core_count": payload.get("coordinate_missing_core_count"),
        "classification_counts": payload.get("classification_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
