from __future__ import annotations

import argparse
import json
from pathlib import Path

import trackable_action_consequence_candidates_current_v1 as current_consequence
from hpfa.modules.core.visible_action_sequence_candidates_lite.src import (
    visible_action_sequence_candidates as sequence,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.occurrence_temporal_sequence_projection import (
    build_occurrence_temporal_sequence_projection,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.partial_order_occurrence_variant_projection import (
    build_partial_order_occurrence_variants,
)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _bind_occurrence_projection(payload: dict, trace_payload: dict, consequence_payload: dict) -> dict:
    projection = build_occurrence_temporal_sequence_projection(trace_payload, consequence_payload)
    payload["occurrence_temporal_projection_status"] = projection.get("status")
    payload["occurrence_temporal_time_layer_candidates"] = list(
        projection.get("occurrence_temporal_time_layer_candidates") or []
    )
    payload["occurrence_temporal_time_layer_candidate_count"] = int(
        projection.get("occurrence_temporal_time_layer_candidate_count") or 0
    )
    payload["occurrence_temporal_sequence_candidates"] = list(
        projection.get("occurrence_temporal_sequence_candidates") or []
    )
    payload["occurrence_temporal_sequence_candidate_count"] = int(
        projection.get("occurrence_temporal_sequence_candidate_count") or 0
    )
    payload["eligible_occurrence_after_confirmed_edge_count"] = int(
        projection.get("eligible_occurrence_after_confirmed_edge_count") or 0
    )
    payload["occurrence_temporal_rejected_edge_reason_counts"] = dict(
        projection.get("rejected_edge_reason_counts") or {}
    )
    payload["occurrence_temporal_projection_claim_ceiling"] = "VISIBLE_SEQUENCE_CANDIDATE_ONLY"
    payload["occurrence_temporal_projection_is_sequence_truth"] = False
    payload["occurrence_temporal_projection_is_possession_truth"] = False
    payload["occurrence_temporal_projection_is_causal_truth"] = False
    payload["occurrence_temporal_projection_is_tactical_truth"] = False
    payload["occurrence_temporal_projection_is_primary_consumer_candidate"] = bool(
        payload["occurrence_temporal_sequence_candidate_count"] > 0
    )
    if projection.get("status") == "FAIL_CLOSED":
        reviews = list(payload.get("review_hits") or [])
        reviews.append("occurrence_temporal_projection_fail_closed_preserved_as_review")
        payload["review_hits"] = sorted(set(str(value) for value in reviews if str(value)))
        if payload.get("status") != "FAIL_CLOSED":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
    payload["canonical_event_count"] = "UNKNOWN"
    payload["true_action_count"] = "UNKNOWN"
    payload["production_release"] = False
    return payload


def _promote_occurrence_temporal_primary(payload: dict) -> dict:
    projection_status = str(payload.get("occurrence_temporal_projection_status") or "").strip().upper()
    occurrence_layers = payload.get("occurrence_temporal_time_layer_candidates")
    occurrence_sequences = payload.get("occurrence_temporal_sequence_candidates")
    if projection_status != "PASS" or not isinstance(occurrence_layers, list) or not isinstance(occurrence_sequences, list):
        payload["primary_sequence_projection_mode"] = "LEGACY_TRACE_COMPATIBILITY"
        payload["occurrence_temporal_primary_inventory_admitted"] = False
        return payload

    if not occurrence_sequences:
        payload["primary_sequence_projection_mode"] = "LEGACY_TRACE_COMPATIBILITY_EMPTY_OCCURRENCE_PROJECTION"
        payload["occurrence_temporal_primary_inventory_admitted"] = False
        payload["occurrence_temporal_empty_projection_requires_review"] = True
        reviews = list(payload.get("review_hits") or [])
        reviews.append("occurrence_temporal_primary_inventory_empty")
        payload["review_hits"] = sorted(set(str(value) for value in reviews if str(value)))
        if payload.get("status") != "FAIL_CLOSED":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
        return payload

    legacy_layers = list(payload.get("visible_action_time_layer_candidates") or [])
    legacy_sequences = list(payload.get("visible_action_sequence_candidates") or [])
    payload["legacy_visible_action_time_layer_candidates"] = legacy_layers
    payload["legacy_visible_action_sequence_candidates"] = legacy_sequences
    payload["legacy_visible_action_time_layer_candidate_count"] = len(legacy_layers)
    payload["legacy_visible_action_sequence_candidate_count"] = len(legacy_sequences)
    payload["legacy_trace_sequence_surface_is_primary_action_member_surface"] = False
    payload["legacy_trace_sequence_surface_retained_as_support_context"] = True

    payload["visible_action_time_layer_candidates"] = occurrence_layers
    payload["visible_action_time_layer_candidate_count"] = len(occurrence_layers)
    payload["visible_action_sequence_candidates"] = occurrence_sequences
    payload["visible_action_sequence_candidate_count"] = len(occurrence_sequences)
    payload["primary_sequence_projection_mode"] = "OCCURRENCE_TEMPORAL_PRIMARY"
    payload["occurrence_temporal_primary_inventory_admitted"] = True
    payload["occurrence_temporal_primary_inventory_is_sequence_truth"] = False
    payload["occurrence_temporal_primary_inventory_is_possession_truth"] = False
    payload["occurrence_temporal_primary_inventory_is_tactical_truth"] = False
    payload["occurrence_temporal_primary_inventory_is_causal_truth"] = False

    payload["pass_multi_layer_visible_sequence_candidate_count"] = sum(
        str(row.get("sequence_record_status") or "") == "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"
        for row in occurrence_sequences
        if isinstance(row, dict)
    )
    payload["pass_single_layer_visible_trace_candidate_count"] = sum(
        str(row.get("sequence_record_status") or "") == "PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE"
        for row in occurrence_sequences
        if isinstance(row, dict)
    )
    payload["review_required_sequence_context_count"] = sum(
        str(row.get("sequence_record_status") or "") == "REVIEW_REQUIRED_CONTEXT"
        for row in occurrence_sequences
        if isinstance(row, dict)
    )
    payload["primary_sequence_member_trace_count"] = len(
        {
            str(trace_id)
            for row in occurrence_sequences
            if isinstance(row, dict)
            for trace_id in (row.get("trackable_action_trace_candidate_ids") or [])
            if str(trace_id)
        }
    )
    payload["review_layer_member_trace_count"] = 0
    payload["trace_assignment_complete"] = False
    payload["trace_assignment_count"] = int(payload.get("source_trackable_action_trace_candidate_count") or 0)
    payload["canonical_event_count"] = "UNKNOWN"
    payload["true_action_count"] = "UNKNOWN"
    payload["production_release"] = False
    return payload


def _bind_partial_order_variants(payload: dict, trace_payload: dict, consequence_payload: dict) -> dict:
    projection = build_partial_order_occurrence_variants(payload, trace_payload, consequence_payload)
    payload["partial_order_occurrence_variant_status"] = projection.get("status")
    payload["partial_order_occurrence_variants"] = list(
        projection.get("partial_order_occurrence_variants") or []
    )
    payload["partial_order_occurrence_variant_count"] = int(
        projection.get("partial_order_occurrence_variant_count") or 0
    )
    payload["partial_order_occurrence_variant_claim_ceiling"] = projection.get("claim_ceiling")
    payload["partial_order_occurrence_variant_is_sequence_truth"] = False
    payload["partial_order_occurrence_variant_is_possession_truth"] = False
    payload["partial_order_occurrence_variant_is_tactical_pattern_truth"] = False
    payload["partial_order_occurrence_variant_is_coach_intention_truth"] = False
    if projection.get("status") == "FAIL_CLOSED":
        reviews = list(payload.get("review_hits") or [])
        reviews.append("partial_order_occurrence_variant_projection_fail_closed_preserved_as_review")
        payload["review_hits"] = sorted(set(str(value) for value in reviews if str(value)))
        if payload.get("status") != "FAIL_CLOSED":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
    payload["canonical_event_count"] = "UNKNOWN"
    payload["true_action_count"] = "UNKNOWN"
    payload["production_release"] = False
    return payload


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = sequence.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    consequence_payload = current_consequence.runtime_write_outputs(input_dir, output)
    trace_path = output / "trackable_action_trace_candidates_lite_v1.json"

    if consequence_payload.get("status") == "FAIL_CLOSED" or not trace_path.is_file():
        return {
            "module_id": sequence.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "visible_action_time_layer_candidates": [],
            "visible_action_sequence_candidates": [],
            "visible_sequence_boundary_candidates": [],
            "trace_assignments": [],
            "review_time_layer_candidates": [],
            "source_trackable_action_trace_candidate_count": 0,
            "source_trackable_action_consequence_candidate_count": 0,
            "visible_action_time_layer_candidate_count": 0,
            "single_team_primary_layer_count": 0,
            "mixed_team_primary_layer_review_required_count": 0,
            "visible_action_sequence_candidate_count": 0,
            "primary_sequence_member_trace_count": 0,
            "review_layer_member_trace_count": 0,
            "trace_assignment_count": 0,
            "trace_assignment_complete": False,
            "occurrence_temporal_time_layer_candidates": [],
            "occurrence_temporal_time_layer_candidate_count": 0,
            "occurrence_temporal_sequence_candidates": [],
            "occurrence_temporal_sequence_candidate_count": 0,
            "eligible_occurrence_after_confirmed_edge_count": 0,
            "partial_order_occurrence_variants": [],
            "partial_order_occurrence_variant_count": 0,
            "hard_block_hits": ["current_consequence_fail_closed_or_trace_output_missing"],
            "review_hits": [],
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "visible_sequence_candidate_is_sequence_truth": False,
            "visible_sequence_candidate_is_possession_truth": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "event_instance_count": 0,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "current_consequence_status": consequence_payload.get("status"),
        }

    trace_payload = _load(trace_path)
    payload = sequence.build_visible_action_sequence_candidates(trace_payload, consequence_payload)
    payload = _bind_occurrence_projection(payload, trace_payload, consequence_payload)
    payload = _promote_occurrence_temporal_primary(payload)
    payload = _bind_partial_order_variants(payload, trace_payload, consequence_payload)
    payload["current_consequence_status"] = consequence_payload.get("status")
    payload["current_trace_status"] = consequence_payload.get("current_trace_status")
    payload["current_content_source_role_bridge_status"] = consequence_payload.get(
        "current_content_source_role_bridge_status"
    )
    payload["active_match_evidence_pass"] = False
    paths = sequence.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA current Trackable Action consequence to visible sequence candidates")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": payload.get("status"),
        "current_consequence_status": payload.get("current_consequence_status"),
        "primary_sequence_projection_mode": payload.get("primary_sequence_projection_mode"),
        "occurrence_temporal_primary_inventory_admitted": payload.get("occurrence_temporal_primary_inventory_admitted"),
        "source_trackable_action_trace_candidate_count": payload.get("source_trackable_action_trace_candidate_count"),
        "legacy_visible_action_sequence_candidate_count": payload.get("legacy_visible_action_sequence_candidate_count"),
        "visible_action_time_layer_candidate_count": payload.get("visible_action_time_layer_candidate_count"),
        "single_team_primary_layer_count": payload.get("single_team_primary_layer_count"),
        "mixed_team_primary_layer_review_required_count": payload.get("mixed_team_primary_layer_review_required_count"),
        "visible_action_sequence_candidate_count": payload.get("visible_action_sequence_candidate_count"),
        "pass_multi_layer_visible_sequence_candidate_count": payload.get("pass_multi_layer_visible_sequence_candidate_count"),
        "pass_single_layer_visible_trace_candidate_count": payload.get("pass_single_layer_visible_trace_candidate_count"),
        "review_required_sequence_context_count": payload.get("review_required_sequence_context_count"),
        "occurrence_temporal_sequence_candidate_count": payload.get("occurrence_temporal_sequence_candidate_count"),
        "eligible_occurrence_after_confirmed_edge_count": payload.get("eligible_occurrence_after_confirmed_edge_count"),
        "partial_order_occurrence_variant_status": payload.get("partial_order_occurrence_variant_status"),
        "partial_order_occurrence_variant_count": payload.get("partial_order_occurrence_variant_count"),
        "primary_sequence_member_trace_count": payload.get("primary_sequence_member_trace_count"),
        "review_layer_member_trace_count": payload.get("review_layer_member_trace_count"),
        "trace_assignment_complete": payload.get("trace_assignment_complete"),
        "boundary_reason_counts": payload.get("boundary_reason_counts") or {},
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "review_hits": payload.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
