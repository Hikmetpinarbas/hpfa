from __future__ import annotations

import math
from collections import Counter
from typing import Any

FIELD_SEMANTICS_VERSION = "selected_action_consequence_field_semantics_v1_1"
NOT_APPLICABLE = "NOT_APPLICABLE"
PRESSURE_STATUS = "UNAVAILABLE_EVENT_ONLY_NO_TRACKING_OR_EXPLICIT_PRESSURE_EVENT"
PROGRESSION_STATUS = "WAIT_ATTACK_DIRECTION_AND_COORDINATE_SCALE_CONTRACT"
COORDINATE_SCALE_STATUS = "UNVERIFIED_PROVIDER_SCALE"
BREAKDOWN_FAMILIES = {"TURNOVER", "CONTROL_ERROR"}
RECOVERY_FAMILIES = {"RECOVERY", "INTERCEPTION"}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def actor_identity_applicability(record: dict[str, Any]) -> str:
    role = clean(record.get("source_role"))
    actor = clean(record.get("actor_identity_candidate_id"))
    if role == "TEAM_SURFACE_CANDIDATE":
        return "NOT_APPLICABLE_TEAM_SURFACE"
    if actor:
        return "APPLICABLE_BOUND_CANDIDATE"
    return "MISSING_REVIEW_REQUIRED"


def enrich_actor_semantics(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        record["actor_identity_applicability"] = actor_identity_applicability(record)
    return records


def response_latency_class(delta_seconds: float | None, *, visible: bool) -> str:
    if not visible:
        return "NO_VISIBLE_RESPONSE"
    if delta_seconds is None or delta_seconds <= 0 or delta_seconds > 12:
        return "UNKNOWN_REVIEW"
    if delta_seconds <= 5:
        return "WITHIN_5S"
    if delta_seconds <= 8:
        return "BETWEEN_5_AND_8S"
    return "BETWEEN_8_AND_12S"


def _first_layer(record: dict[str, Any], node_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    layers = record.get("follow_up_node_ids_by_layer") or []
    if not layers:
        return [], False
    first_ids = layers[0] if isinstance(layers[0], list) else []
    first_nodes: list[dict[str, Any]] = []
    missing_reference = False
    for raw_id in first_ids:
        node = node_by_id.get(clean(raw_id))
        if node is None:
            missing_reference = True
        else:
            first_nodes.append(node)
    return first_nodes, missing_reference


def first_layer_team_state(anchor_team: str, first_nodes: list[dict[str, Any]], missing_reference: bool = False) -> str:
    if missing_reference:
        return "UNKNOWN"
    if not first_nodes:
        return "NONE"
    if not anchor_team:
        return "UNKNOWN"
    teams = {clean(node.get("team_identity_candidate_id")) for node in first_nodes}
    if "" in teams:
        return "UNKNOWN"
    has_same = anchor_team in teams
    has_opponent = any(team != anchor_team for team in teams)
    if has_same and has_opponent:
        return "MIXED"
    if has_same:
        return "SAME_TEAM"
    if has_opponent:
        return "OPPONENT"
    return "UNKNOWN"


def retention_candidate(team_state: str) -> str:
    return {
        "SAME_TEAM": "SAME_TEAM_VISIBLE_RETENTION_CANDIDATE",
        "OPPONENT": "OPPONENT_VISIBLE_HANDOVER_CANDIDATE",
        "MIXED": "MIXED_TEAM_SAME_TIME_REVIEW_REQUIRED_CANDIDATE",
        "NONE": "NO_VISIBLE_RETENTION_SIGNAL_WITHIN_12S",
        "UNKNOWN": "RETENTION_RELATION_UNKNOWN_REVIEW",
    }.get(team_state, "RETENTION_RELATION_UNKNOWN_REVIEW")


def turnover_response_candidate(anchor_families: set[str], team_state: str, first_families: set[str]) -> str:
    if not (anchor_families & BREAKDOWN_FAMILIES):
        return NOT_APPLICABLE
    if team_state == "OPPONENT":
        return "OPPONENT_VISIBLE_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
    if team_state == "SAME_TEAM" and first_families & RECOVERY_FAMILIES:
        return "SAME_TEAM_RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
    if team_state == "SAME_TEAM":
        return "SAME_TEAM_VISIBLE_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
    if team_state == "MIXED":
        return "MIXED_TEAM_BREAKDOWN_RESPONSE_REVIEW_REQUIRED_CANDIDATE"
    if team_state == "NONE":
        return "NO_VISIBLE_RESPONSE_WITHIN_12S_AFTER_BREAKDOWN_CANDIDATE"
    return "BREAKDOWN_RESPONSE_UNKNOWN_REVIEW"


def _minimum_team_delta(anchor: dict[str, Any], visible_nodes: list[dict[str, Any]], *, relation: str) -> tuple[float | None, bool, bool]:
    anchor_team = clean(anchor.get("team_identity_candidate_id"))
    anchor_start = number(anchor.get("start_candidate"))
    if not anchor_team or anchor_start is None:
        return None, False, True
    candidates: list[float] = []
    unknown = False
    for node in visible_nodes:
        team = clean(node.get("team_identity_candidate_id"))
        start = number(node.get("start_candidate"))
        if not team or start is None:
            unknown = True
            continue
        is_match = team == anchor_team if relation == "same" else team != anchor_team
        delta = start - anchor_start
        if is_match and 0 < delta <= 12:
            candidates.append(delta)
    if candidates:
        return min(candidates), True, False
    return None, False, unknown


def _coordinate_displacement(anchor: dict[str, Any], first_nodes: list[dict[str, Any]], missing_reference: bool) -> dict[str, Any]:
    base = {
        "raw_coordinate_delta_x_candidate": None,
        "raw_coordinate_delta_y_candidate": None,
        "raw_coordinate_displacement_candidate": None,
        "raw_coordinate_displacement_class": "NOT_AVAILABLE",
        "coordinate_displacement_status": "NOT_AVAILABLE",
        "coordinate_scale_status": COORDINATE_SCALE_STATUS,
        "progression_interpretation_status": PROGRESSION_STATUS,
        "raw_coordinate_delta_is_progression_truth": False,
    }
    if missing_reference:
        base["coordinate_displacement_status"] = "FOLLOW_UP_REFERENCE_MISSING_REVIEW_REQUIRED"
        return base
    if not first_nodes:
        base["coordinate_displacement_status"] = "NOT_VISIBLE_WITHIN_12S"
        return base
    anchor_x = number(anchor.get("pos_x_candidate"))
    anchor_y = number(anchor.get("pos_y_candidate"))
    if anchor_x is None or anchor_y is None:
        base["coordinate_displacement_status"] = "ANCHOR_COORDINATE_MISSING_REVIEW_REQUIRED"
        return base
    coordinates: set[tuple[float, float]] = set()
    for node in first_nodes:
        x = number(node.get("pos_x_candidate"))
        y = number(node.get("pos_y_candidate"))
        if x is None or y is None:
            base["coordinate_displacement_status"] = "FOLLOW_UP_COORDINATE_MISSING_REVIEW_REQUIRED"
            return base
        coordinates.add((x, y))
    if len(coordinates) != 1:
        base["coordinate_displacement_status"] = "MIXED_FIRST_LAYER_COORDINATE_REVIEW_REQUIRED"
        return base
    target_x, target_y = next(iter(coordinates))
    dx = round(target_x - anchor_x, 6)
    dy = round(target_y - anchor_y, 6)
    distance = round(math.hypot(dx, dy), 6)
    if distance <= 10:
        displacement_class = "SHORT_RAW_PROVIDER_DISPLACEMENT"
    elif distance <= 25:
        displacement_class = "MEDIUM_RAW_PROVIDER_DISPLACEMENT"
    else:
        displacement_class = "LONG_RAW_PROVIDER_DISPLACEMENT"
    base.update({
        "raw_coordinate_delta_x_candidate": dx,
        "raw_coordinate_delta_y_candidate": dy,
        "raw_coordinate_displacement_candidate": distance,
        "raw_coordinate_displacement_class": displacement_class,
        "coordinate_displacement_status": "RAW_PROVIDER_COORDINATE_DISPLACEMENT_AVAILABLE",
    })
    return base


def enrich_consequence_records(records: list[dict[str, Any]], node_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        anchor = node_by_id.get(clean(record.get("anchor_selected_action_node_id")))
        if anchor is None:
            record.update({
                "field_semantics_version": FIELD_SEMANTICS_VERSION,
                "field_semantics_status": "ANCHOR_NODE_REFERENCE_MISSING_FAIL_CLOSED",
                "first_visible_follow_up_status": "UNKNOWN_REVIEW",
                "first_visible_follow_up_delta_status": "UNKNOWN_REVIEW",
                "first_layer_team_state": "UNKNOWN",
                "first_layer_node_ids": [],
                "first_layer_team_candidate_ids": [],
                "first_layer_action_families": [],
                "first_follow_up_window_class": "UNKNOWN_REVIEW",
                "retention_after_action_candidate": "RETENTION_RELATION_UNKNOWN_REVIEW",
                "same_team_response_latency_seconds_candidate": None,
                "same_team_response_latency_class": "UNKNOWN_REVIEW",
                "opponent_response_latency_seconds_candidate": None,
                "opponent_response_latency_class": "UNKNOWN_REVIEW",
                "turnover_response_candidate": "BREAKDOWN_RESPONSE_UNKNOWN_REVIEW",
                "actor_identity_applicability": "MISSING_REVIEW_REQUIRED",
                "pressure_interpretation_status": PRESSURE_STATUS,
                **_coordinate_displacement({}, [], True),
            })
            continue
        first_nodes, missing_reference = _first_layer(record, node_by_id)
        first_ids = [clean(node.get("selected_action_node_id")) for node in first_nodes]
        anchor_team = clean(anchor.get("team_identity_candidate_id"))
        team_state = first_layer_team_state(anchor_team, first_nodes, missing_reference)
        first_families = set().union(*(set(node.get("action_family_candidates") or []) for node in first_nodes)) if first_nodes else set()
        visible_nodes = [node_by_id[node_id] for node_id in (record.get("visible_follow_up_node_ids") or []) if clean(node_id) in node_by_id]
        declared_visible_ids = [clean(node_id) for node_id in (record.get("visible_follow_up_node_ids") or [])]
        missing_visible_refs = len(visible_nodes) != len(declared_visible_ids)
        delta = number(record.get("first_visible_follow_up_delta_seconds"))
        if missing_reference or missing_visible_refs:
            visible_status = "UNKNOWN_REVIEW"
            delta_status = "UNKNOWN_REVIEW"
        elif first_nodes and delta is not None and 0 < delta <= 12:
            visible_status = "VISIBLE_WITHIN_12S"
            delta_status = "AVAILABLE_STRICT_POSITIVE_WITHIN_12S"
        elif not first_nodes and delta is None:
            visible_status = "NOT_VISIBLE_WITHIN_12S"
            delta_status = "NOT_APPLICABLE_NO_VISIBLE_FOLLOW_UP"
        else:
            visible_status = "UNKNOWN_REVIEW"
            delta_status = "UNKNOWN_REVIEW"
        same_delta, same_visible, same_unknown = _minimum_team_delta(anchor, visible_nodes, relation="same")
        opponent_delta, opponent_visible, opponent_unknown = _minimum_team_delta(anchor, visible_nodes, relation="opponent")
        same_latency = "UNKNOWN_REVIEW" if same_unknown and not same_visible else response_latency_class(same_delta, visible=same_visible)
        opponent_latency = "UNKNOWN_REVIEW" if opponent_unknown and not opponent_visible else response_latency_class(opponent_delta, visible=opponent_visible)
        anchor_families = set(anchor.get("action_family_candidates") or [])
        record.update({
            "field_semantics_version": FIELD_SEMANTICS_VERSION,
            "field_semantics_status": "PASS_CANDIDATE_SEMANTICS" if visible_status != "UNKNOWN_REVIEW" and team_state != "UNKNOWN" else "REVIEW_REQUIRED",
            "actor_identity_applicability": actor_identity_applicability(anchor),
            "first_visible_follow_up_status": visible_status,
            "first_visible_follow_up_delta_status": delta_status,
            "first_layer_team_state": team_state,
            "first_layer_node_ids": sorted(first_ids),
            "first_layer_team_candidate_ids": sorted({clean(node.get("team_identity_candidate_id")) for node in first_nodes if clean(node.get("team_identity_candidate_id"))}),
            "first_layer_actor_candidate_ids": sorted({clean(node.get("actor_identity_candidate_id")) for node in first_nodes if clean(node.get("actor_identity_candidate_id"))}),
            "first_layer_source_roles": sorted({clean(node.get("source_role")) for node in first_nodes if clean(node.get("source_role"))}),
            "first_layer_action_families": sorted(first_families),
            "first_follow_up_window_class": response_latency_class(delta, visible=bool(first_nodes)) if visible_status != "UNKNOWN_REVIEW" else "UNKNOWN_REVIEW",
            "retention_after_action_candidate": retention_candidate(team_state),
            "retention_candidate_is_possession_truth": False,
            "same_team_response_latency_seconds_candidate": None if same_delta is None else round(same_delta, 6),
            "same_team_response_latency_class": same_latency,
            "opponent_response_latency_seconds_candidate": None if opponent_delta is None else round(opponent_delta, 6),
            "opponent_response_latency_class": opponent_latency,
            "response_latency_class_is_pressure_truth": False,
            "turnover_response_candidate": turnover_response_candidate(anchor_families, team_state, first_families),
            "turnover_response_is_counterpress_success_truth": False,
            "pressure_interpretation_status": PRESSURE_STATUS,
            **_coordinate_displacement(anchor, first_nodes, missing_reference),
        })
    return records


def semantic_counters(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    fields = (
        "field_semantics_status",
        "actor_identity_applicability",
        "first_visible_follow_up_status",
        "first_layer_team_state",
        "first_follow_up_window_class",
        "retention_after_action_candidate",
        "same_team_response_latency_class",
        "opponent_response_latency_class",
        "turnover_response_candidate",
        "coordinate_displacement_status",
        "raw_coordinate_displacement_class",
        "pressure_interpretation_status",
        "progression_interpretation_status",
    )
    return {
        f"{field}_counts": dict(sorted(Counter(clean(record.get(field)) or "UNDEFINED" for record in records).items()))
        for field in fields
    }
