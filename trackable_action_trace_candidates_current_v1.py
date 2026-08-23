from __future__ import annotations

import argparse
import json
from pathlib import Path

import cross_role_relation_candidate_resolver_current_v1 as current_relation
from hpfa.modules.core.trackable_action_trace_candidates_lite.src import (
    trackable_action_trace_candidates as trackable,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = trackable.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    relation_payload = current_relation.runtime_write_outputs(input_dir, output)
    action_path = output / "semantic_role_action_bundle_candidates_lite_v1.json"
    taxonomy_path = output / "action_bundle_multi_family_review_taxonomy_lite_v1.json"
    evidence_path = output / "evidence_atom_inventory_lite_v1.json"

    if (
        relation_payload.get("status") == "FAIL_CLOSED"
        or not action_path.is_file()
        or not taxonomy_path.is_file()
        or not evidence_path.is_file()
    ):
        return {
            "module_id": trackable.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "selection_records": {
                "selected_primary_surfaces": [],
                "reflection_context_surfaces": [],
                "quarantined_surfaces": [],
            },
            "source_action_bundle_candidate_count": 0,
            "selected_primary_surface_candidate_count": 0,
            "reflection_context_surface_candidate_count": 0,
            "quarantined_surface_candidate_count": 0,
            "selection_partition_coverage_count": 0,
            "selection_partition_complete": False,
            "trackable_action_trace_candidates": [],
            "trackable_action_trace_candidate_count": 0,
            "relation_supported_trace_candidate_count": 0,
            "standalone_primary_trace_candidate_count": 0,
            "same_surface_multi_family_trace_candidate_count": 0,
            "hard_block_hits": ["current_cross_role_or_required_upstream_output_missing"],
            "review_hits": [],
            "trackable_action_candidate_is_event_truth": False,
            "physical_action_identity_truth": False,
            "trace_count_is_physical_action_count": False,
            "reflection_context_is_event_equivalence_truth": False,
            "final_double_count_suppression_admitted": False,
            "count_value_output_allowed": False,
            "consequence_classification_allowed": False,
            "sequence_link_allowed": False,
            "same_time_order_truth_admitted": False,
            "source_row_order_is_temporal_truth": False,
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
            "current_relation_status": relation_payload.get("status"),
        }

    action_payload = _load(action_path)
    taxonomy_payload = _load(taxonomy_path)
    evidence_payload = _load(evidence_path)
    payload = trackable.build_trackable_action_trace_candidates(
        action_payload,
        taxonomy_payload,
        relation_payload,
        evidence_payload,
    )
    payload["current_relation_status"] = relation_payload.get("status")
    payload["current_taxonomy_status"] = relation_payload.get("current_taxonomy_status")
    payload["current_semantic_status"] = relation_payload.get("current_semantic_status")
    payload["current_content_source_role_bridge_status"] = relation_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["active_match_evidence_pass"] = False
    paths = trackable.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current relation+taxonomy+action+evidence to Trackable Action trace candidates"
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
                "source_action_bundle_candidate_count": payload.get("source_action_bundle_candidate_count"),
                "selected_primary_surface_candidate_count": payload.get("selected_primary_surface_candidate_count"),
                "reflection_context_surface_candidate_count": payload.get("reflection_context_surface_candidate_count"),
                "quarantined_surface_candidate_count": payload.get("quarantined_surface_candidate_count"),
                "trackable_action_trace_candidate_count": payload.get("trackable_action_trace_candidate_count"),
                "relation_supported_trace_candidate_count": payload.get("relation_supported_trace_candidate_count"),
                "standalone_primary_trace_candidate_count": payload.get("standalone_primary_trace_candidate_count"),
                "same_surface_multi_family_trace_candidate_count": payload.get("same_surface_multi_family_trace_candidate_count"),
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
