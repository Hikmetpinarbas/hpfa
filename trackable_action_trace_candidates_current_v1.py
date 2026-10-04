from __future__ import annotations

import argparse
import json
from pathlib import Path

import action_occurrence_admission_current_v1 as current_occurrence
from hpfa.modules.core.trackable_action_trace_candidates_lite.src import (
    trackable_action_trace_candidates as trackable,
)
from hpfa.modules.core.trackable_action_trace_candidates_lite.src.observed_actor_acquisition_release_interval_projection import (
    CLAIM_CEILING as INTERVAL_CLAIM_CEILING,
    build_observed_actor_acquisition_release_interval_projection,
)
from hpfa.modules.core.trackable_action_trace_candidates_lite.src.occurrence_topology_adapter import (
    apply_occurrence_topology_binding,
)
from hpfa.modules.core.trackable_action_trace_candidates_lite.src.occurrence_trace_binding import (
    build_occurrence_aware_trace_payload,
)
from hpfa.modules.core.trackable_action_trace_candidates_lite.src.provider_time_runtime_context_adapter import (
    build_provider_time_runtime_context,
)
from hpfa.modules.core.trackable_action_trace_candidates_lite.src.temporal_relation_admission_adapter import (
    bind_temporal_relation_admission,
)

INTERVAL_OUTPUT_JSON = "observed_actor_acquisition_release_interval_projection_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_interval_projection(payload: dict, output: Path) -> dict:
    if payload.get("status") == "FAIL_CLOSED":
        projection = {
            "status": "FAIL_CLOSED",
            "observed_actor_acquisition_release_interval_candidates": [],
            "observed_actor_acquisition_release_interval_candidate_count": 0,
            "eligible_acquisition_trace_count": 0,
            "hard_block_hits": ["upstream_trace_runtime_fail_closed"],
            "review_hits": [],
            "projection_creates_new_evidence": False,
            "projection_reconstructs_sequences": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": INTERVAL_CLAIM_CEILING,
        }
    else:
        projection = build_observed_actor_acquisition_release_interval_projection(payload)

    path = output / INTERVAL_OUTPUT_JSON
    path.write_text(
        json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload["current_actor_acquisition_release_interval_projection_bound"] = True
    payload["current_actor_acquisition_release_interval_status"] = projection.get("status")
    payload["current_actor_acquisition_release_interval_candidate_count"] = projection.get(
        "observed_actor_acquisition_release_interval_candidate_count", 0
    )
    payload["current_actor_acquisition_release_interval_claim_ceiling"] = projection.get(
        "claim_ceiling"
    )
    payload["current_actor_acquisition_release_interval_output"] = str(path)
    payload["current_actor_acquisition_release_interval_projection_creates_new_evidence"] = (
        projection.get("projection_creates_new_evidence") is True
    )
    payload["current_actor_acquisition_release_interval_projection_reconstructs_sequences"] = (
        projection.get("projection_reconstructs_sequences") is True
    )
    if projection.get("status") == "FAIL_CLOSED":
        review_hits = list(payload.get("review_hits") or [])
        review_hits.append("actor_acquisition_release_interval_projection_fail_closed")
        payload["review_hits"] = sorted(set(review_hits))
        if payload.get("status") == "PASS":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
    return projection


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = trackable.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    occurrence_payload = current_occurrence.runtime_write_outputs(input_dir, output)
    relation_path = output / "cross_role_relation_candidate_resolver_lite_v1.json"
    action_path = output / "semantic_role_action_bundle_candidates_lite_v1.json"
    taxonomy_path = output / "action_bundle_multi_family_review_taxonomy_lite_v1.json"
    evidence_path = output / "evidence_atom_inventory_lite_v1.json"

    if (
        occurrence_payload.get("status") == "FAIL_CLOSED"
        or not relation_path.is_file()
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
            "occurrence_trace_binding_records": [],
            "occurrence_trace_binding_record_count": 0,
            "occurrence_bound_trace_candidate_count": 0,
            "occurrence_both_participants_trace_visible_count": 0,
            "occurrence_single_actor_trace_visible_count": 0,
            "occurrence_partial_participant_trace_visible_count": 0,
            "occurrence_no_participant_trace_visible_count": 0,
            "occurrence_unresolved_topology_count": 0,
            "occurrence_topology_aware_binding": True,
            "temporal_relation_admission_records": [],
            "temporal_relation_admission_record_count": 0,
            "temporal_relation_state_counts": {},
            "provider_time_contract_admission_status": "NOT_EVALUATED",
            "current_actor_acquisition_release_interval_projection_bound": False,
            "current_actor_acquisition_release_interval_status": "NOT_EVALUATED",
            "current_actor_acquisition_release_interval_candidate_count": 0,
            "hard_block_hits": ["current_occurrence_or_required_upstream_output_missing"],
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
            "occurrence_binding_is_event_truth": False,
            "occurrence_binding_changes_upstream_taxonomy_truth": False,
            "event_instance_count": 0,
            "claim_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_occurrence_status": occurrence_payload.get("status"),
            "current_content_source_role_bridge_status": occurrence_payload.get(
                "current_content_source_role_bridge_status"
            ),
        }

    relation_payload = _load(relation_path)
    action_payload = _load(action_path)
    taxonomy_payload = _load(taxonomy_path)
    evidence_payload = _load(evidence_path)
    payload = build_occurrence_aware_trace_payload(
        action_payload,
        taxonomy_payload,
        relation_payload,
        evidence_payload,
        occurrence_payload,
        trackable.build_trackable_action_trace_candidates,
    )
    payload = apply_occurrence_topology_binding(payload, occurrence_payload)
    context_payload = build_provider_time_runtime_context(input_dir)
    payload = bind_temporal_relation_admission(payload, context_payload)
    payload["provider_time_runtime_context_source"] = context_payload.get("runtime_context_source")
    payload["current_occurrence_status"] = occurrence_payload.get("status")
    payload["current_occurrence_candidate_count"] = occurrence_payload.get(
        "action_occurrence_candidate_count", 0
    )
    payload["current_relation_status"] = occurrence_payload.get("current_relation_status")
    payload["current_taxonomy_status"] = occurrence_payload.get("current_taxonomy_status")
    payload["current_semantic_status"] = occurrence_payload.get("current_semantic_status")
    payload["current_content_source_role_bridge_status"] = occurrence_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["current_provider_semantics_binding_status"] = occurrence_payload.get(
        "provider_semantics_binding_status"
    )
    if payload["current_content_source_role_bridge_status"] != "PASS":
        hard_blocks = list(payload.get("hard_block_hits") or [])
        hard_blocks.append("current_content_source_role_bridge_not_pass")
        payload["hard_block_hits"] = sorted(set(hard_blocks))
        payload["status"] = "FAIL_CLOSED"
        payload["module_status"] = "FAIL_CLOSED"
        payload["runtime_evidence_status"] = "NOT_EVALUATED"
    if payload["current_provider_semantics_binding_status"] != "PASS":
        hard_blocks = list(payload.get("hard_block_hits") or [])
        hard_blocks.append("current_provider_semantics_binding_not_pass")
        payload["hard_block_hits"] = sorted(set(hard_blocks))
        payload["status"] = "FAIL_CLOSED"
        payload["module_status"] = "FAIL_CLOSED"
        payload["runtime_evidence_status"] = "NOT_EVALUATED"

    _write_interval_projection(payload, output)
    payload["active_match_evidence_pass"] = False
    paths = trackable.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    payload["outputs"]["observed_actor_acquisition_release_interval_projection"] = str(
        output / INTERVAL_OUTPUT_JSON
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current occurrence-aware relation+taxonomy+action+evidence to Trackable Action trace candidates"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "current_occurrence_status": payload.get("current_occurrence_status"),
                "current_occurrence_candidate_count": payload.get("current_occurrence_candidate_count", 0),
                "current_relation_status": payload.get("current_relation_status"),
                "current_content_source_role_bridge_status": payload.get(
                    "current_content_source_role_bridge_status"
                ),
                "current_provider_semantics_binding_status": payload.get(
                    "current_provider_semantics_binding_status"
                ),
                "source_action_bundle_candidate_count": payload.get("source_action_bundle_candidate_count"),
                "selected_primary_surface_candidate_count": payload.get("selected_primary_surface_candidate_count"),
                "reflection_context_surface_candidate_count": payload.get("reflection_context_surface_candidate_count"),
                "quarantined_surface_candidate_count": payload.get("quarantined_surface_candidate_count"),
                "trackable_action_trace_candidate_count": payload.get("trackable_action_trace_candidate_count"),
                "occurrence_bound_trace_candidate_count": payload.get("occurrence_bound_trace_candidate_count", 0),
                "occurrence_both_participants_trace_visible_count": payload.get("occurrence_both_participants_trace_visible_count", 0),
                "occurrence_single_actor_trace_visible_count": payload.get("occurrence_single_actor_trace_visible_count", 0),
                "occurrence_partial_participant_trace_visible_count": payload.get("occurrence_partial_participant_trace_visible_count", 0),
                "occurrence_no_participant_trace_visible_count": payload.get("occurrence_no_participant_trace_visible_count", 0),
                "occurrence_unresolved_topology_count": payload.get("occurrence_unresolved_topology_count", 0),
                "provider_time_contract_admission_status": payload.get("provider_time_contract_admission_status"),
                "provider_time_runtime_context_source": payload.get("provider_time_runtime_context_source"),
                "temporal_relation_admission_record_count": payload.get("temporal_relation_admission_record_count", 0),
                "temporal_relation_state_counts": payload.get("temporal_relation_state_counts") or {},
                "current_actor_acquisition_release_interval_status": payload.get(
                    "current_actor_acquisition_release_interval_status"
                ),
                "current_actor_acquisition_release_interval_candidate_count": payload.get(
                    "current_actor_acquisition_release_interval_candidate_count", 0
                ),
                "current_actor_acquisition_release_interval_projection_bound": payload.get(
                    "current_actor_acquisition_release_interval_projection_bound", False
                ),
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
