from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .common import (
        CANONICAL_EVENT_COUNT, MAX_FOLLOW_UP_LAYERS, WINDOW_SECONDS, clean, digest,
        number, timeline_key,
    )
except ImportError:  # direct src-path test import
    from common import (
        CANONICAL_EVENT_COUNT, MAX_FOLLOW_UP_LAYERS, WINDOW_SECONDS, clean, digest,
        number, timeline_key,
    )


def _team_qualified_families(
    anchor_team: str,
    future: list[dict[str, Any]],
) -> tuple[set[str], set[str], bool]:
    same_team_families: set[str] = set()
    opponent_families: set[str] = set()
    missing_team_identity = False
    for node in future:
        node_team = clean(node.get("team_identity_candidate_id"))
        families = set(node.get("action_family_candidates") or [])
        if not node_team:
            missing_team_identity = True
        elif node_team == anchor_team:
            same_team_families.update(families)
        else:
            opponent_families.update(families)
    return same_team_families, opponent_families, missing_team_identity


def _first_layer_team_state(anchor_team: str, future: list[dict[str, Any]]) -> str:
    if not future:
        return "NONE"
    first_start = number(future[0].get("start_candidate"))
    first_layer = [node for node in future if number(node.get("start_candidate")) == first_start]
    teams = {clean(node.get("team_identity_candidate_id")) for node in first_layer}
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


def consequence_class(anchor: dict[str, Any], future: list[dict[str, Any]]) -> tuple[str, list[str]]:
    team = clean(anchor.get("team_identity_candidate_id"))
    anchor_families = set(anchor.get("action_family_candidates") or [])
    signals: set[str] = set()
    if anchor.get("terminal_outcome_support_visible"):
        signals.add("TERMINAL_OUTCOME_SUPPORT_VISIBLE")
    if anchor.get("derived_consequence_support_visible"):
        signals.add("DERIVED_CONSEQUENCE_SUPPORT_VISIBLE")
    if not team:
        signals.add("ANCHOR_TEAM_IDENTITY_MISSING")
        return "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE", sorted(signals)
    if not future:
        primary = "TERMINAL_OUTCOME_SUPPORT_CANDIDATE" if "TERMINAL_OUTCOME_SUPPORT_VISIBLE" in signals else "NO_VISIBLE_FOLLOW_UP_CANDIDATE"
        return primary, sorted(signals)

    same_team_families, opponent_families, missing_team_identity = _team_qualified_families(team, future)
    first_layer_state = _first_layer_team_state(team, future)
    flags = {
        "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE": "SHOT" in same_team_families,
        "OPPONENT_SHOT_FOLLOW_UP_VISIBLE": "SHOT" in opponent_families,
        "SAME_TEAM_RESTART_FOLLOW_UP_VISIBLE": "RESTART" in same_team_families,
        "OPPONENT_RESTART_FOLLOW_UP_VISIBLE": "RESTART" in opponent_families,
        "SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE": bool({"RECOVERY", "INTERCEPTION"} & same_team_families),
        "OPPONENT_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE": bool({"RECOVERY", "INTERCEPTION"} & opponent_families),
        "SAME_TEAM_TURNOVER_OR_CONTROL_ERROR_FOLLOW_UP_VISIBLE": bool({"TURNOVER", "CONTROL_ERROR"} & same_team_families),
        "OPPONENT_TURNOVER_OR_CONTROL_ERROR_FOLLOW_UP_VISIBLE": bool({"TURNOVER", "CONTROL_ERROR"} & opponent_families),
        "SAME_TEAM_FOLLOW_UP_VISIBLE": bool(same_team_families),
        "OPPONENT_FOLLOW_UP_VISIBLE": bool(opponent_families),
        "MIXED_TEAM_FIRST_LAYER_VISIBLE": first_layer_state == "MIXED",
        "FOLLOW_UP_TEAM_IDENTITY_MISSING": missing_team_identity,
    }
    signals.update(name for name, active in flags.items() if active)

    if "TERMINAL_OUTCOME_SUPPORT_VISIBLE" in signals:
        primary = "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"
    elif missing_team_identity:
        primary = "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    elif first_layer_state == "MIXED":
        primary = "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    elif flags["SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE"]:
        primary = "SHOT_FOLLOW_UP_CANDIDATE"
    elif anchor_families & {"TURNOVER", "CONTROL_ERROR"}:
        if flags["SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE"]:
            primary = "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
        elif first_layer_state == "OPPONENT":
            primary = "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
        else:
            primary = "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE"
    elif anchor_families & {"RECOVERY", "INTERCEPTION"} and first_layer_state == "SAME_TEAM":
        primary = "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    elif first_layer_state == "SAME_TEAM" and "RESTART" in same_team_families:
        primary = "RESTART_OR_RESET_CANDIDATE"
    elif first_layer_state == "SAME_TEAM":
        primary = "SAME_TEAM_CONTINUATION_CANDIDATE"
    elif first_layer_state == "OPPONENT":
        primary = "OPPONENT_HANDOVER_CANDIDATE"
    else:
        primary = "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    return primary, sorted(signals)


def build_consequences(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_period[clean(node.get("period_candidate"))].append(node)
    records: list[dict[str, Any]] = []
    for period_nodes in by_period.values():
        period_nodes.sort(key=timeline_key)
        for index, anchor in enumerate(period_nodes):
            anchor_start = number(anchor.get("start_candidate"))
            layer_map: dict[float, list[dict[str, Any]]] = defaultdict(list)
            if anchor_start is not None:
                for candidate in period_nodes[index + 1 :]:
                    candidate_start = number(candidate.get("start_candidate"))
                    if candidate_start is None:
                        continue
                    delta = candidate_start - anchor_start
                    if delta <= 0:
                        continue
                    if delta > WINDOW_SECONDS[-1]:
                        break
                    layer_map[candidate_start].append(candidate)
            layers = [sorted(layer_map[start], key=timeline_key) for start in sorted(layer_map)[:MAX_FOLLOW_UP_LAYERS]]
            future = [node for layer in layers for node in layer]
            first_delta = None if not future or anchor_start is None else round((number(future[0].get("start_candidate")) or anchor_start) - anchor_start, 6)
            primary, signals = consequence_class(anchor, future)
            window_counts = {}
            for seconds in WINDOW_SECONDS:
                window_counts[f"visible_follow_up_node_count_{int(seconds)}s"] = sum(
                    1
                    for node in future
                    if number(node.get("start_candidate")) is not None
                    and anchor_start is not None
                    and 0 < (number(node.get("start_candidate")) or anchor_start) - anchor_start <= seconds
                )
            records.append(
                {
                    "selected_action_consequence_candidate_id": "sacc_" + digest(anchor.get("selected_action_node_id"), [node.get("selected_action_node_id") for node in future])[:24],
                    "anchor_selected_action_node_id": anchor.get("selected_action_node_id"),
                    "match_surface_binding_id": anchor.get("match_surface_binding_id"),
                    "source_role": anchor.get("source_role"),
                    "team_identity_candidate_id": anchor.get("team_identity_candidate_id"),
                    "actor_identity_candidate_id": anchor.get("actor_identity_candidate_id"),
                    "period_candidate": anchor.get("period_candidate"),
                    "anchor_start_candidate": anchor.get("start_candidate"),
                    "anchor_end_candidate": anchor.get("end_candidate"),
                    "anchor_action_family_candidates": anchor.get("action_family_candidates"),
                    "follow_up_layer_count": len(layers),
                    "follow_up_node_ids_by_layer": [[node.get("selected_action_node_id") for node in layer] for layer in layers],
                    "visible_follow_up_node_ids": [node.get("selected_action_node_id") for node in future],
                    "first_visible_follow_up_delta_seconds": first_delta,
                    **window_counts,
                    "primary_consequence_candidate": primary,
                    "consequence_signal_candidates": signals,
                    "same_time_link_allowed": False,
                    "negative_time_link_allowed": False,
                    "cross_period_link_allowed": False,
                    "window_is_sequence_truth": False,
                    "continuation_is_possession_truth": False,
                    "consequence_candidate_is_causal_truth": False,
                    "event_instance_allowed": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                }
            )
    return sorted(records, key=lambda record: clean(record.get("anchor_selected_action_node_id")))


def profiles(records: list[dict[str, Any]], nodes: dict[str, dict[str, Any]], identity_field: str, profile_type: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        identity = clean(record.get(identity_field))
        if not identity:
            continue
        node = nodes[clean(record.get("anchor_selected_action_node_id"))]
        for family in node.get("action_family_candidates") or []:
            grouped[(identity, clean(family))].append(record)
    output = []
    for (identity, family), rows in sorted(grouped.items()):
        output.append(
            {
                "profile_type": profile_type,
                "identity_candidate_id": identity,
                "action_family_candidate": family,
                "selected_action_node_count": len(rows),
                "primary_consequence_candidate_counts": dict(sorted(Counter(clean(row.get("primary_consequence_candidate")) for row in rows).items())),
                "visible_follow_up_5s_count": sum(int(row.get("visible_follow_up_node_count_5s") or 0) > 0 for row in rows),
                "visible_follow_up_8s_count": sum(int(row.get("visible_follow_up_node_count_8s") or 0) > 0 for row in rows),
                "visible_follow_up_12s_count": sum(int(row.get("visible_follow_up_node_count_12s") or 0) > 0 for row in rows),
                "profile_is_player_or_team_quality_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
    return output
