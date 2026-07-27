from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .common import (
        CANONICAL_EVENT_COUNT, MAX_FOLLOW_UP_LAYERS, MODULE_ID, OUTPUTS,
        WINDOW_SECONDS, clean, load_json, validate_inputs, validate_out,
    )
    from .consequence import build_consequences, profiles
    from .field_semantics import (
        FIELD_SEMANTICS_VERSION,
        enrich_actor_semantics,
        enrich_consequence_records,
        semantic_counters,
    )
    from .selection import build_nodes, select_surfaces
except ImportError:  # direct src-path test import
    from common import (
        CANONICAL_EVENT_COUNT, MAX_FOLLOW_UP_LAYERS, MODULE_ID, OUTPUTS,
        WINDOW_SECONDS, clean, load_json, validate_inputs, validate_out,
    )
    from consequence import build_consequences, profiles
    from field_semantics import (
        FIELD_SEMANTICS_VERSION,
        enrich_actor_semantics,
        enrich_consequence_records,
        semantic_counters,
    )
    from selection import build_nodes, select_surfaces


def build_selected_action_consequence_surface(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks, binding, bundles, tax_records, relation_records, atoms = validate_inputs(action_payload, taxonomy_payload, relation_payload, evidence_payload)
    selected: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    if not blocks:
        selected, suppressed, quarantined, selection_blocks = select_surfaces(bundles, tax_records, relation_records, binding)
        blocks.extend(selection_blocks)
    enrich_actor_semantics(selected)
    enrich_actor_semantics(suppressed)
    enrich_actor_semantics(quarantined)
    nodes = build_nodes(selected, binding, atoms) if not blocks else []
    enrich_actor_semantics(nodes)
    consequences = build_consequences(nodes) if not blocks else []
    node_by_id = {clean(node.get("selected_action_node_id")): node for node in nodes}
    enrich_consequence_records(consequences, node_by_id)
    semantics = semantic_counters(consequences)
    team_profiles = profiles(consequences, node_by_id, "team_identity_candidate_id", "TEAM_ACTION_FAMILY_CONSEQUENCE_PROFILE_CANDIDATE")
    actor_profiles = profiles(consequences, node_by_id, "actor_identity_candidate_id", "ACTOR_ACTION_FAMILY_CONSEQUENCE_PROFILE_CANDIDATE")
    reviews: list[str] = []
    for name, payload in {"action": action_payload, "taxonomy": taxonomy_payload, "relation": relation_payload, "evidence": evidence_payload}.items():
        status = clean(payload.get("module_status") or payload.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"{name}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{name}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{name}_upstream_status_review:{status}")
    if quarantined:
        reviews.append("unresolved_action_surfaces_quarantined")
    if any(node.get("coordinate_evidence_status") != "COORDINATE_PRESENT" for node in nodes):
        reviews.append("selected_action_coordinate_missing_preserved")
    if any(record.get("field_semantics_status") == "REVIEW_REQUIRED" for record in consequences):
        reviews.append("field_semantics_review_required_records_present")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    selected_roles = Counter(clean(row.get("source_role")) for row in selected)
    selected_families = Counter(clean(row.get("action_family_candidate")) for row in selected)
    consequence_counts = Counter(clean(row.get("primary_consequence_candidate")) for row in consequences)
    support_counts = Counter()
    for node in nodes:
        support_counts.update({key: int(value) for key, value in (node.get("support_atom_class_counts") or {}).items()})
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "field_semantics_version": FIELD_SEMANTICS_VERSION,
        "field_semantics_record_count": len(consequences),
        "selection_records": selected,
        "selected_action_surface_candidate_count": len(selected),
        "suppressed_reflection_records": suppressed,
        "suppressed_team_reflection_candidate_count": len(suppressed),
        "quarantined_action_surface_records": quarantined,
        "quarantined_unresolved_surface_count": len(quarantined),
        "selected_action_nodes": nodes,
        "selected_action_node_count": len(nodes),
        "same_time_multi_family_node_count": sum(bool(node.get("same_time_multi_family_grouping")) for node in nodes),
        "selected_action_consequence_candidates": consequences,
        "selected_action_consequence_candidate_count": len(consequences),
        "team_action_family_consequence_profiles": team_profiles,
        "team_action_family_consequence_profile_count": len(team_profiles),
        "actor_action_family_consequence_profiles": actor_profiles,
        "actor_action_family_consequence_profile_count": len(actor_profiles),
        "selected_source_role_counts": dict(sorted(selected_roles.items())),
        "selected_action_family_counts": dict(sorted(selected_families.items())),
        "primary_consequence_candidate_counts": dict(sorted(consequence_counts.items())),
        "support_atom_class_counts": dict(sorted(support_counts.items())),
        **semantics,
        "window_seconds": [int(value) for value in WINDOW_SECONDS],
        "max_follow_up_layers": MAX_FOLLOW_UP_LAYERS,
        "source_action_bundle_candidate_count": len(bundles),
        "source_taxonomy_record_count": len(tax_records),
        "source_resolved_relation_candidate_count": len(relation_records),
        "source_evidence_atom_count": len(atoms),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "selected_action_surface_is_canonical_event": False,
        "consequence_candidate_is_causal_truth": False,
        "continuation_candidate_is_possession_truth": False,
        "retention_candidate_is_possession_truth": False,
        "response_latency_class_is_pressure_truth": False,
        "turnover_response_is_counterpress_success_truth": False,
        "raw_coordinate_delta_is_progression_truth": False,
        "window_is_sequence_truth": False,
        "team_response_is_tactical_truth": False,
        "same_time_link_allowed": False,
        "negative_time_link_allowed": False,
        "cross_period_link_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "field_semantics_version",
        "source_action_bundle_candidate_count",
        "selected_action_surface_candidate_count",
        "suppressed_team_reflection_candidate_count",
        "quarantined_unresolved_surface_count",
        "selected_action_node_count",
        "selected_action_consequence_candidate_count",
        "primary_consequence_candidate_counts",
        "first_layer_team_state_counts",
        "retention_after_action_candidate_counts",
        "same_team_response_latency_class_counts",
        "opponent_response_latency_class_counts",
        "turnover_response_candidate_counts",
        "coordinate_displacement_status_counts",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA SELECTED ACTION CONSEQUENCE SURFACE LITE V1.1"] + [f"{key}={payload.get(key)}" for key in keys]
    return "\n".join(lines + ["canonical_event_count=UNKNOWN", "production_release=false"]) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    counts = payload.get("primary_consequence_candidate_counts") or {}
    lines = [
        "HPFA ANALYST AUDIT — SELECTED ACTION CONSEQUENCE SURFACE V1.1",
        f"Visible action-bundle candidates inspected: {payload.get('source_action_bundle_candidate_count', 0)}",
        f"Distinct selected action surfaces: {payload.get('selected_action_surface_candidate_count', 0)}",
        f"Team reflection candidates separated: {payload.get('suppressed_team_reflection_candidate_count', 0)}",
        f"Unresolved action surfaces quarantined: {payload.get('quarantined_unresolved_surface_count', 0)}",
        f"Same-time multi-family action nodes: {payload.get('same_time_multi_family_node_count', 0)}",
        f"Same-team continuation candidates: {counts.get('SAME_TEAM_CONTINUATION_CANDIDATE', 0)}",
        f"Opponent handover candidates: {counts.get('OPPONENT_HANDOVER_CANDIDATE', 0)}",
        f"Shot follow-up candidates: {counts.get('SHOT_FOLLOW_UP_CANDIDATE', 0)}",
        f"First-layer team states: {payload.get('first_layer_team_state_counts')}",
        f"Retention/handover candidates: {payload.get('retention_after_action_candidate_counts')}",
        f"Same-team response latency: {payload.get('same_team_response_latency_class_counts')}",
        f"Opponent response latency: {payload.get('opponent_response_latency_class_counts')}",
        f"Turnover response candidates: {payload.get('turnover_response_candidate_counts')}",
        f"Raw coordinate displacement status: {payload.get('coordinate_displacement_status_counts')}",
        "Analyst-safe meaning: visible actions now carry explicit first-layer team relation, response latency, retention/handover, breakdown response and raw coordinate-displacement candidates.",
        "Raw coordinate displacement is not progression; response latency is not pressure; retention is not possession truth; turnover response is not counterpress success truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-bundle", required=True)
    parser.add_argument("--multi-family-taxonomy", required=True)
    parser.add_argument("--cross-role-relations", required=True)
    parser.add_argument("--evidence-atoms", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_selected_action_consequence_surface(
        load_json(args.action_bundle, "action_bundle_input_unreadable_or_malformed"),
        load_json(args.multi_family_taxonomy, "multi_family_taxonomy_input_unreadable_or_malformed"),
        load_json(args.cross_role_relations, "cross_role_relation_input_unreadable_or_malformed"),
        load_json(args.evidence_atoms, "evidence_atom_input_unreadable_or_malformed"),
    )
    write_outputs(payload, args.out)
    print(json.dumps({key: payload.get(key) for key in ("status", "field_semantics_version", "selected_action_surface_candidate_count", "selected_action_node_count", "selected_action_consequence_candidate_count", "quarantined_unresolved_surface_count", "canonical_event_count", "production_release")}, ensure_ascii=False, indent=2))
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
