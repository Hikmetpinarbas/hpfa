from __future__ import annotations

import argparse
import json
from pathlib import Path

import action_bundle_multi_family_review_taxonomy_current_v1 as current_taxonomy
from hpfa.modules.core.cross_role_relation_candidate_resolver_lite.src import (
    cross_role_relation_candidate_resolver as resolver,
)


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = resolver.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    taxonomy_payload = current_taxonomy.runtime_write_outputs(input_dir, output)
    semantic_path = output / "semantic_role_action_bundle_candidates_lite_v1.json"

    if taxonomy_payload.get("status") == "FAIL_CLOSED" or not semantic_path.is_file():
        return {
            "module_id": resolver.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": taxonomy_payload.get("match_surface_binding_id"),
            "resolved_relation_candidates": [],
            "source_action_bundle_candidate_count": taxonomy_payload.get("source_action_bundle_candidate_count", 0),
            "source_cross_role_relation_candidate_count": taxonomy_payload.get("current_cross_role_relation_candidate_count", 0),
            "resolved_relation_candidate_count": 0,
            "candidate_clear_relation_count": 0,
            "review_required_relation_count": 0,
            "double_count_suppression_candidate_count": 0,
            "relation_classification_counts": {},
            "relation_role_pair_counts": {},
            "relation_family_counts": {},
            "hard_block_hits": ["current_multi_family_taxonomy_fail_closed_or_semantic_output_missing"],
            "review_hits": [],
            "same_time_only_link_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "relation_candidate_is_event_truth": False,
            "reflection_equivalence_truth": False,
            "double_count_suppression_is_final": False,
            "count_value_output_allowed": False,
            "cross_role_fusion_allowed": False,
            "event_instance_count": 0,
            "claim_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_taxonomy_status": taxonomy_payload.get("status"),
        }

    try:
        semantic_payload = json.loads(semantic_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        semantic_payload = {}

    payload = resolver.build_cross_role_relation_candidate_resolver(
        semantic_payload,
        taxonomy_payload,
    )
    payload["current_taxonomy_status"] = taxonomy_payload.get("status")
    payload["current_semantic_status"] = taxonomy_payload.get("current_semantic_status")
    payload["current_content_source_role_bridge_status"] = taxonomy_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["current_multi_family_review_core_count"] = taxonomy_payload.get(
        "multi_family_review_core_count"
    )
    payload["active_match_evidence_pass"] = False
    paths = resolver.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current Action Bundle + Taxonomy to Cross-Role Relation migration"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_taxonomy_status": payload.get("current_taxonomy_status"),
        "source_cross_role_relation_candidate_count": payload.get("source_cross_role_relation_candidate_count"),
        "resolved_relation_candidate_count": payload.get("resolved_relation_candidate_count"),
        "candidate_clear_relation_count": payload.get("candidate_clear_relation_count"),
        "review_required_relation_count": payload.get("review_required_relation_count"),
        "double_count_suppression_candidate_count": payload.get("double_count_suppression_candidate_count"),
        "relation_classification_counts": payload.get("relation_classification_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
