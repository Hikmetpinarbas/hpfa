from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .common import CANONICAL_EVENT_COUNT, clean, digest
    from .coordinate_frame import zone_candidate
except ImportError:
    from common import CANONICAL_EVENT_COUNT, clean, digest
    from coordinate_frame import zone_candidate

GAIN_CLASSES = {
    "ZONE_GAIN_CANDIDATE",
    "THIRD_BREAK_CANDIDATE",
    "BOX_ACCESS_CANDIDATE",
    "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE",
}
BREAKDOWN_FAMILIES = {"TURNOVER", "CONTROL_ERROR"}
RECOVERY_FAMILIES = {"RECOVERY", "INTERCEPTION"}


def _first_layer_nodes(record: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    layers = record.get("follow_up_node_ids_by_layer") or []
    if not layers:
        return [], False
    ids = layers[0] if isinstance(layers[0], list) else []
    result = []
    missing = False
    for raw_id in ids:
        node = nodes.get(clean(raw_id))
        if node is None:
            missing = True
        else:
            result.append(node)
    return result, missing


def _team_state(anchor_team: str, first_nodes: list[dict[str, Any]], missing: bool) -> str:
    if missing:
        return "UNKNOWN_REVIEW"
    if not first_nodes:
        return "NONE"
    teams = {clean(node.get("team_identity_candidate_id")) for node in first_nodes}
    if not anchor_team or "" in teams:
        return "UNKNOWN_REVIEW"
    same = anchor_team in teams
    opponent = any(team != anchor_team for team in teams)
    if same and opponent:
        return "MIXED_REVIEW_REQUIRED"
    if same:
        return "SAME_TEAM"
    if opponent:
        return "OPPONENT"
    return "UNKNOWN_REVIEW"


def _zone_delta(anchor: dict[str, Any], first_nodes: list[dict[str, Any]], team_state: str, frame: dict[str, Any]) -> dict[str, Any]:
    anchor_zone = zone_candidate(anchor, frame)
    base = {
        "anchor_zone_candidate": anchor_zone["zone_candidate"],
        "anchor_zone_rank_candidate": anchor_zone["zone_rank_candidate"],
        "first_same_team_zone_candidates": [],
        "first_same_team_zone_rank_candidates": [],
        "zone_delta_class": "UNRESOLVED_ZONE_DELTA_REVIEW_REQUIRED",
        "zone_delta_status": "UNRESOLVED",
        "zone_delta_not_xT": True,
        "zone_delta_not_progression_truth": True,
    }
    if team_state == "NONE":
        base.update({"zone_delta_class": "NO_VISIBLE_FOLLOW_UP_CANDIDATE", "zone_delta_status": "NOT_APPLICABLE"})
        return base
    if team_state == "OPPONENT":
        base.update({"zone_delta_class": "LOSS_OR_HANDOVER_CANDIDATE", "zone_delta_status": "PASS_CANDIDATE_CLASSIFICATION"})
        return base
    if team_state != "SAME_TEAM":
        return base
    anchor_team = clean(anchor.get("team_identity_candidate_id"))
    same_nodes = [node for node in first_nodes if clean(node.get("team_identity_candidate_id")) == anchor_team]
    zones = [zone_candidate(node, frame) for node in same_nodes]
    if anchor_zone["zone_candidate_status"] != "PASS_CANDIDATE_ZONE" or any(zone["zone_candidate_status"] != "PASS_CANDIDATE_ZONE" for zone in zones):
        return base
    zone_names = sorted({zone["zone_candidate"] for zone in zones})
    ranks = sorted({zone["zone_rank_candidate"] for zone in zones})
    base["first_same_team_zone_candidates"] = zone_names
    base["first_same_team_zone_rank_candidates"] = ranks
    if len(ranks) != 1:
        base["zone_delta_class"] = "MIXED_SAME_TEAM_ZONE_REVIEW_REQUIRED"
        return base
    anchor_rank = anchor_zone["zone_rank_candidate"]
    target_rank = ranks[0]
    if target_rank == anchor_rank:
        delta = "NO_ZONE_CHANGE_CANDIDATE"
    elif target_rank < anchor_rank:
        delta = "RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE"
    elif zone_names == ["CENTRAL_DEEP_BOX_GRID_CANDIDATE"]:
        delta = "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE"
    elif zone_names == ["BOX_COORDINATE_CANDIDATE"]:
        delta = "BOX_ACCESS_CANDIDATE"
    elif target_rank - anchor_rank >= 2:
        delta = "THIRD_BREAK_CANDIDATE"
    else:
        delta = "ZONE_GAIN_CANDIDATE"
    base.update({"zone_delta_class": delta, "zone_delta_status": "PASS_CANDIDATE_CLASSIFICATION"})
    return base


def _turnover_window(anchor: dict[str, Any], record: dict[str, Any], nodes: dict[str, dict[str, Any]], frame: dict[str, Any], team_state: str) -> str:
    families = set(anchor.get("action_family_candidates") or [])
    if not families & BREAKDOWN_FAMILIES:
        return "NOT_APPLICABLE"
    layers = record.get("follow_up_node_ids_by_layer") or []
    if not layers:
        return "TURNOVER_NO_VISIBLE_RESPONSE_WITHIN_12S_CANDIDATE"
    anchor_team = clean(anchor.get("team_identity_candidate_id"))
    first_ids = layers[0] if isinstance(layers[0], list) else []
    first_nodes = [nodes.get(clean(node_id)) for node_id in first_ids]
    if any(node is None for node in first_nodes):
        return "TURNOVER_WINDOW_REFERENCE_MISSING_REVIEW_REQUIRED"
    first_nodes = [node for node in first_nodes if node is not None]
    if team_state == "MIXED_REVIEW_REQUIRED":
        return "TURNOVER_MIXED_FIRST_LAYER_REVIEW_REQUIRED"
    if team_state == "SAME_TEAM":
        first_families = set().union(*(set(node.get("action_family_candidates") or []) for node in first_nodes)) if first_nodes else set()
        if first_families & RECOVERY_FAMILIES:
            return "TURNOVER_TO_SAME_TEAM_RECOVERY_CANDIDATE"
        return "TURNOVER_TO_SAME_TEAM_RETENTION_CANDIDATE"
    if team_state == "OPPONENT":
        visible = []
        for layer in layers:
            if isinstance(layer, list):
                visible.extend(nodes.get(clean(node_id)) for node_id in layer)
        visible = [node for node in visible if node is not None and clean(node.get("team_identity_candidate_id")) != anchor_team]
        if any("SHOT" in set(node.get("action_family_candidates") or []) for node in visible):
            return "TURNOVER_TO_OPPONENT_SHOT_CANDIDATE"
        opponent_zones = [zone_candidate(node, frame) for node in visible]
        if any(zone["zone_candidate"] in {"BOX_COORDINATE_CANDIDATE", "CENTRAL_DEEP_BOX_GRID_CANDIDATE"} for zone in opponent_zones):
            return "TURNOVER_TO_OPPONENT_BOX_ACCESS_CANDIDATE"
        return "TURNOVER_TO_OPPONENT_HANDOVER_CANDIDATE"
    if team_state == "NONE":
        return "TURNOVER_NO_VISIBLE_RESPONSE_WITHIN_12S_CANDIDATE"
    return "TURNOVER_WINDOW_UNRESOLVED_REVIEW_REQUIRED"


def _false_progression(anchor: dict[str, Any], record: dict[str, Any], nodes: dict[str, dict[str, Any]], zone_delta: str) -> str:
    if zone_delta not in GAIN_CLASSES:
        return "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN"
    anchor_team = clean(anchor.get("team_identity_candidate_id"))
    layers = record.get("follow_up_node_ids_by_layer") or []
    if not layers:
        return "UNRESOLVED_NO_FOLLOW_UP_AFTER_GAIN_REVIEW_REQUIRED"
    opponent_layer = None
    constructive_before = False
    for index, layer in enumerate(layers):
        if not isinstance(layer, list):
            continue
        layer_nodes = [nodes.get(clean(node_id)) for node_id in layer]
        if any(node is None for node in layer_nodes):
            return "UNRESOLVED_REFERENCE_MISSING_REVIEW_REQUIRED"
        for node in layer_nodes:
            team = clean(node.get("team_identity_candidate_id"))
            families = set(node.get("action_family_candidates") or [])
            if team == anchor_team and "SHOT" in families:
                constructive_before = True
            elif team and team != anchor_team and opponent_layer is None:
                opponent_layer = index
        if opponent_layer is not None:
            break
    if opponent_layer is None:
        return "VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE"
    if constructive_before:
        return "ZONE_GAIN_WITH_CONSTRUCTIVE_SUPPORT_BEFORE_HANDOVER_CANDIDATE"
    return "FALSE_PROGRESSION_CANDIDATE"


def _consequence_class(record: dict[str, Any]) -> str:
    zone_delta = clean(record.get("zone_delta_class"))
    turnover = clean(record.get("turnover_window_class"))
    team_state = clean(record.get("first_layer_team_state"))
    false_progression = clean(record.get("false_progression_candidate"))
    primary = clean(record.get("source_primary_consequence_candidate"))
    values = (zone_delta, turnover, team_state, false_progression)
    if any(marker in value for value in values for marker in ("UNRESOLVED", "REVIEW_REQUIRED", "UNKNOWN")):
        return "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"
    if turnover in {"TURNOVER_TO_OPPONENT_SHOT_CANDIDATE", "TURNOVER_TO_OPPONENT_BOX_ACCESS_CANDIDATE", "TURNOVER_TO_OPPONENT_HANDOVER_CANDIDATE"}:
        return "FAILED_VISIBLE_CONSEQUENCE_CANDIDATE"
    if zone_delta == "LOSS_OR_HANDOVER_CANDIDATE" or team_state == "OPPONENT":
        return "FAILED_VISIBLE_CONSEQUENCE_CANDIDATE"
    if false_progression == "FALSE_PROGRESSION_CANDIDATE":
        return "RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE"
    if primary in {"SHOT_FOLLOW_UP_CANDIDATE", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"} or zone_delta in {"BOX_ACCESS_CANDIDATE", "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE", "THIRD_BREAK_CANDIDATE"}:
        return "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE"
    if zone_delta == "ZONE_GAIN_CANDIDATE" and team_state == "SAME_TEAM":
        return "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE"
    return "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE"


def build_records(payload: dict[str, Any], frame: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    nodes = {clean(node.get("selected_action_node_id")): node for node in payload.get("selected_action_nodes") or []}
    records = []
    blocks = []
    for source in payload.get("selected_action_consequence_candidates") or []:
        anchor_id = clean(source.get("anchor_selected_action_node_id"))
        anchor = nodes.get(anchor_id)
        if anchor is None:
            blocks.append(f"anchor_node_missing:{anchor_id}")
            continue
        first_nodes, missing = _first_layer_nodes(source, nodes)
        team_state = _team_state(clean(anchor.get("team_identity_candidate_id")), first_nodes, missing)
        zone = _zone_delta(anchor, first_nodes, team_state, frame)
        turnover = _turnover_window(anchor, source, nodes, frame, team_state)
        retention_value = True if team_state == "SAME_TEAM" else (False if team_state == "OPPONENT" else None)
        retention_status = {
            "SAME_TEAM": "VISIBLE_RETENTION_CANDIDATE_TRUE",
            "OPPONENT": "VISIBLE_RETENTION_CANDIDATE_FALSE_HANDOVER",
            "MIXED_REVIEW_REQUIRED": "RETENTION_MIXED_REVIEW_REQUIRED",
            "NONE": "RETENTION_NO_VISIBLE_SIGNAL_WITHIN_12S",
        }.get(team_state, "RETENTION_UNRESOLVED_REVIEW_REQUIRED")
        false_progression = _false_progression(anchor, source, nodes, zone["zone_delta_class"])
        result = {
            "selected_event_consequence_candidate_id": "secs_" + digest(source.get("selected_action_consequence_candidate_id"), frame.get("coordinate_frame_status"))[:24],
            "source_selected_action_consequence_candidate_id": source.get("selected_action_consequence_candidate_id"),
            "anchor_selected_action_node_id": anchor_id,
            "match_surface_binding_id": payload.get("match_surface_binding_id"),
            "team_identity_candidate_id": anchor.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": anchor.get("actor_identity_candidate_id"),
            "source_role": anchor.get("source_role"),
            "period_candidate": anchor.get("period_candidate"),
            "anchor_action_family_candidates": anchor.get("action_family_candidates"),
            "source_primary_consequence_candidate": source.get("primary_consequence_candidate"),
            "first_layer_team_state": team_state,
            **zone,
            "pressure_first_action_class": "UNAVAILABLE_EVENT_ONLY_NO_EXPLICIT_PRESSURE_EVIDENCE",
            "pressure_first_action_status": "NOT_COMPUTABLE_FROM_CURRENT_EVENT_ONLY_SURFACE",
            "pressure_escape_not_pressure_truth": True,
            "turnover_window_class": turnover,
            "turnover_to_box_not_transition_superiority": True,
            "retention_after_action_candidate": retention_value,
            "retention_after_action_status": retention_status,
            "retention_after_action_is_possession_truth": False,
            "false_progression_candidate": false_progression,
            "false_progression_not_bad_decision": True,
            "consequence_class_candidate": None,
            "consequence_not_value": True,
            "consequence_not_quality": True,
            "analysis_sentence_generated": False,
            "claim_allowed": False,
            "event_instance_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }
        result["consequence_class_candidate"] = _consequence_class(result)
        records.append(result)
    return records, sorted(set(blocks))


def composite_profiles(records: list[dict[str, Any]], identity_field: str, profile_type: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        identity = clean(record.get(identity_field))
        if not identity:
            continue
        for family in record.get("anchor_action_family_candidates") or []:
            grouped[(identity, clean(family))].append(record)
    output = []
    for (identity, family), rows in sorted(grouped.items()):
        output.append({
            "profile_type": profile_type,
            "identity_candidate_id": identity,
            "action_family_candidate": family,
            "selected_event_consequence_candidate_count": len(rows),
            "consequence_class_candidate_counts": dict(sorted(Counter(clean(row.get("consequence_class_candidate")) for row in rows).items())),
            "zone_delta_class_counts": dict(sorted(Counter(clean(row.get("zone_delta_class")) for row in rows).items())),
            "turnover_window_class_counts": dict(sorted(Counter(clean(row.get("turnover_window_class")) for row in rows).items())),
            "false_progression_candidate_counts": dict(sorted(Counter(clean(row.get("false_progression_candidate")) for row in rows).items())),
            "profile_is_quality_truth": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        })
    return output
