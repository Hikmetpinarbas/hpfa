from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .common import (
        ACTION_MODULE_ID,
        CANONICAL_EVENT_COUNT,
        EVENT_MODULE_ID,
        MAX_GAP_SECONDS,
        MODULE_ID,
        OUTPUTS,
        clean,
        load_json,
        validate_out,
    )
    from .sequence_admission import admit_visible_sequences, build_sequence_profiles
    from .time_layers import build_visible_time_layers
except ImportError:
    from common import (
        ACTION_MODULE_ID,
        CANONICAL_EVENT_COUNT,
        EVENT_MODULE_ID,
        MAX_GAP_SECONDS,
        MODULE_ID,
        OUTPUTS,
        clean,
        load_json,
        validate_out,
    )
    from sequence_admission import admit_visible_sequences, build_sequence_profiles
    from time_layers import build_visible_time_layers


def _validate_inputs(
    action_payload: dict[str, Any],
    event_payload: dict[str, Any],
) -> tuple[list[str], str, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    blocks: list[str] = []
    if action_payload.get("module_id") != ACTION_MODULE_ID:
        blocks.append("selected_action_module_id_mismatch")
    if event_payload.get("module_id") != EVENT_MODULE_ID:
        blocks.append("selected_event_module_id_mismatch")
    for name, payload in (("action", action_payload), ("event", event_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
    action_binding = clean(action_payload.get("match_surface_binding_id"))
    event_binding = clean(event_payload.get("match_surface_binding_id"))
    if not action_binding or action_binding != event_binding:
        blocks.append("match_surface_binding_mismatch")
    nodes = action_payload.get("selected_action_nodes") or []
    action_records = action_payload.get("selected_action_consequence_candidates") or []
    event_records = event_payload.get("selected_event_consequence_candidates") or []
    if not isinstance(nodes, list):
        blocks.append("selected_action_node_inventory_invalid")
        nodes = []
    if not isinstance(action_records, list):
        blocks.append("selected_action_consequence_inventory_invalid")
        action_records = []
    if not isinstance(event_records, list):
        blocks.append("selected_event_consequence_inventory_invalid")
        event_records = []
    declared = (
        (len(nodes), action_payload.get("selected_action_node_count"), "selected_action_node"),
        (
            len(action_records),
            action_payload.get("selected_action_consequence_candidate_count"),
            "selected_action_consequence",
        ),
        (
            len(event_records),
            event_payload.get("selected_event_consequence_candidate_count"),
            "selected_event_consequence",
        ),
    )
    for actual, expected, name in declared:
        if actual != expected:
            blocks.append(f"{name}_count_mismatch")
    node_ids = [clean(node.get("selected_action_node_id")) for node in nodes if isinstance(node, dict)]
    action_anchor_ids = [
        clean(record.get("anchor_selected_action_node_id"))
        for record in action_records
        if isinstance(record, dict)
    ]
    event_anchor_ids = [
        clean(record.get("anchor_selected_action_node_id"))
        for record in event_records
        if isinstance(record, dict)
    ]
    if len(node_ids) != len(set(node_ids)) or "" in node_ids:
        blocks.append("selected_action_node_id_invalid_or_duplicate")
    if len(action_anchor_ids) != len(set(action_anchor_ids)) or set(action_anchor_ids) != set(node_ids):
        blocks.append("selected_action_consequence_anchor_coverage_mismatch")
    if len(event_anchor_ids) != len(set(event_anchor_ids)) or set(event_anchor_ids) != set(node_ids):
        blocks.append("selected_event_consequence_anchor_coverage_mismatch")
    event_by_node = {
        clean(record.get("anchor_selected_action_node_id")): record
        for record in event_records
        if isinstance(record, dict)
    }
    return sorted(set(blocks)), action_binding, nodes, event_by_node


def build_visible_action_sequence_candidate_admission(
    action_payload: dict[str, Any],
    event_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks, binding, nodes, event_by_node = _validate_inputs(action_payload, event_payload)
    layers: list[dict[str, Any]] = []
    sequences: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    review_layers: list[dict[str, Any]] = []
    if not blocks:
        layers, layer_blocks = build_visible_time_layers(nodes, event_by_node, binding)
        blocks.extend(layer_blocks)
    if not blocks:
        sequences, boundaries, assignments, review_layers, sequence_blocks = admit_visible_sequences(
            layers,
            nodes,
            event_by_node,
            binding,
            MAX_GAP_SECONDS,
        )
        blocks.extend(sequence_blocks)

    node_by_id = {
        clean(node.get("selected_action_node_id")): node
        for node in nodes
        if isinstance(node, dict)
    }
    team_profiles = build_sequence_profiles(
        sequences,
        node_by_id,
        "team_identity_candidate_id",
        "TEAM_ACTION_FAMILY_VISIBLE_SEQUENCE_PROFILE_CANDIDATE",
    )
    actor_profiles = build_sequence_profiles(
        sequences,
        node_by_id,
        "actor_identity_candidate_id",
        "ACTOR_ACTION_FAMILY_VISIBLE_SEQUENCE_PROFILE_CANDIDATE",
    )

    review_hits: list[str] = []
    for name, payload in (("selected_action", action_payload), ("selected_event", event_payload)):
        status = clean(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        elif status != "PASS":
            review_hits.append(f"{name}_upstream_status_review:{status}")
    state_counts = Counter(clean(layer.get("layer_state")) for layer in layers)
    if state_counts.get("MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED", 0):
        review_hits.append("mixed_team_primary_time_layers_preserved")
    if state_counts.get("TEAM_CONTEXT_ONLY_LAYER", 0):
        review_hits.append("team_context_only_layers_preserved")
    unresolved_sequence_count = sum(
        clean(sequence.get("sequence_context_status")) == "REVIEW_REQUIRED"
        for sequence in sequences
    )
    if unresolved_sequence_count:
        review_hits.append("sequence_consequence_context_review_required")
    cross_team_context_support_count = sum(
        int(sequence.get("cross_team_context_support_review_count") or 0)
        for sequence in sequences
    )
    if cross_team_context_support_count:
        review_hits.append("cross_team_same_time_context_support_preserved")

    blocks = sorted(set(blocks))
    review_hits = sorted(set(review_hits))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")

    assignment_counts = Counter(clean(item.get("assignment_type")) for item in assignments)
    sequence_admission_counts = Counter(
        clean(sequence.get("sequence_admission_status")) for sequence in sequences
    )
    start_reason_counts = Counter(clean(sequence.get("start_reason_candidate")) for sequence in sequences)
    end_reason_counts = Counter(clean(sequence.get("end_reason_candidate")) for sequence in sequences)
    trace_counts = Counter(
        signal
        for sequence in sequences
        for signal in (sequence.get("trace_signal_candidates") or [])
    )
    zone_span_counts = Counter(
        clean(sequence.get("sequence_zone_span_candidate")) for sequence in sequences
    )
    composition_counts = Counter(
        clean(sequence.get("sequence_consequence_composition_candidate"))
        for sequence in sequences
    )

    primary_node_count = sum(
        int(layer.get("primary_node_count") or 0) for layer in layers
    )
    team_context_node_count = sum(
        int(layer.get("team_context_node_count") or 0) for layer in layers
    )
    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_selected_action_module_id": action_payload.get("module_id"),
        "source_selected_event_module_id": event_payload.get("module_id"),
        "source_selected_action_node_count": len(nodes),
        "source_selected_action_consequence_candidate_count": action_payload.get(
            "selected_action_consequence_candidate_count"
        ),
        "source_selected_event_consequence_candidate_count": event_payload.get(
            "selected_event_consequence_candidate_count"
        ),
        "visible_action_time_layer_candidates": layers,
        "visible_action_time_layer_candidate_count": len(layers),
        "time_layer_state_counts": dict(sorted(state_counts.items())),
        "primary_sequence_eligible_node_count": primary_node_count,
        "team_context_support_node_count": team_context_node_count,
        "visible_action_sequence_candidates": sequences,
        "visible_action_sequence_candidate_count": len(sequences),
        "sequence_admission_status_counts": dict(sorted(sequence_admission_counts.items())),
        "sequence_context_review_required_count": unresolved_sequence_count,
        "visible_sequence_boundary_candidates": boundaries,
        "visible_sequence_boundary_candidate_count": len(boundaries),
        "review_or_context_only_time_layers": review_layers,
        "review_or_context_only_time_layer_count": len(review_layers),
        "node_assignment_records": assignments,
        "node_assignment_count": len(assignments),
        "node_assignment_type_counts": dict(sorted(assignment_counts.items())),
        "sequence_start_reason_candidate_counts": dict(sorted(start_reason_counts.items())),
        "sequence_end_reason_candidate_counts": dict(sorted(end_reason_counts.items())),
        "trace_signal_candidate_counts": dict(sorted(trace_counts.items())),
        "sequence_zone_span_candidate_counts": dict(sorted(zone_span_counts.items())),
        "sequence_consequence_composition_candidate_counts": dict(
            sorted(composition_counts.items())
        ),
        "team_action_family_visible_sequence_profiles": team_profiles,
        "team_action_family_visible_sequence_profile_count": len(team_profiles),
        "actor_action_family_visible_sequence_profiles": actor_profiles,
        "actor_action_family_visible_sequence_profile_count": len(actor_profiles),
        "max_gap_seconds": MAX_GAP_SECONDS,
        "cross_team_context_support_review_count": cross_team_context_support_count,
        "hard_block_hits": blocks,
        "review_hits": review_hits,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "restart_trace_is_set_piece_design_truth": False,
        "shot_chain_is_chance_quality_truth": False,
        "progression_to_handover_is_bad_decision_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "analysis_sentence_generated": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "source_selected_action_node_count",
        "visible_action_time_layer_candidate_count",
        "time_layer_state_counts",
        "primary_sequence_eligible_node_count",
        "team_context_support_node_count",
        "visible_action_sequence_candidate_count",
        "sequence_admission_status_counts",
        "sequence_context_review_required_count",
        "visible_sequence_boundary_candidate_count",
        "review_or_context_only_time_layer_count",
        "node_assignment_count",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA VISIBLE ACTION SEQUENCE CANDIDATE ADMISSION LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend(["canonical_event_count=UNKNOWN", "production_release=false"])
    return "\n".join(lines) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — VISIBLE ACTION SEQUENCE CANDIDATE ADMISSION",
        f"Visible time-layer candidates: {payload.get('visible_action_time_layer_candidate_count', 0)}",
        f"Primary sequence-eligible action nodes: {payload.get('primary_sequence_eligible_node_count', 0)}",
        f"Team-context support nodes: {payload.get('team_context_support_node_count', 0)}",
        f"Visible sequence candidates: {payload.get('visible_action_sequence_candidate_count', 0)}",
        f"Sequence context review-required: {payload.get('sequence_context_review_required_count', 0)}",
        f"Review/context-only time layers: {payload.get('review_or_context_only_time_layer_count', 0)}",
        f"Trace signals: {payload.get('trace_signal_candidate_counts')}",
        f"Sequence zone-span candidates: {payload.get('sequence_zone_span_candidate_counts')}",
        f"Sequence consequence composition candidates: {payload.get('sequence_consequence_composition_candidate_counts')}",
        "Analyst-safe meaning: actor-bound visible action nodes are grouped into same-team, strictly ordered time-layer chains with explicit gap, handover, restart and ambiguity boundaries.",
        "These chains are candidate traces. They are not physical event counts, possession truth, phase truth, tactical design or control truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--selected-event-consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_visible_action_sequence_candidate_admission(
        load_json(
            args.selected_action_consequence,
            "selected_action_consequence_input_unreadable_or_malformed",
        ),
        load_json(
            args.selected_event_consequence,
            "selected_event_consequence_input_unreadable_or_malformed",
        ),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "visible_action_time_layer_candidate_count",
                    "visible_action_sequence_candidate_count",
                    "sequence_context_review_required_count",
                    "review_or_context_only_time_layer_count",
                    "node_assignment_count",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
