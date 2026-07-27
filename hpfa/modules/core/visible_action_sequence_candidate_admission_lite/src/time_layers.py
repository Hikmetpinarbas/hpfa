from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .common import (
        CANONICAL_EVENT_COUNT,
        clean,
        digest,
        is_primary_node,
        is_team_context_node,
        node_sort_key,
        number,
        number_key,
        period_sort_key,
    )
except ImportError:
    from common import (
        CANONICAL_EVENT_COUNT,
        clean,
        digest,
        is_primary_node,
        is_team_context_node,
        node_sort_key,
        number,
        number_key,
        period_sort_key,
    )


def build_visible_time_layers(
    nodes: list[dict[str, Any]],
    event_by_node: dict[str, dict[str, Any]],
    binding: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[str] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            blocks.append(f"selected_action_node_invalid:{index}")
            continue
        node_id = clean(node.get("selected_action_node_id"))
        if not node_id or node_id in seen_ids:
            blocks.append(f"selected_action_node_id_invalid_or_duplicate:{index}")
            continue
        seen_ids.add(node_id)
        if node.get("match_surface_binding_id") != binding:
            blocks.append(f"selected_action_node_binding_mismatch:{node_id}")
        if number(node.get("start_candidate")) is None:
            blocks.append(f"selected_action_node_start_time_invalid:{node_id}")
        if node_id not in event_by_node:
            blocks.append(f"event_consequence_mapping_missing:{node_id}")
        groups[(clean(node.get("period_candidate")), number_key(node.get("start_candidate")))].append(node)

    layers: list[dict[str, Any]] = []
    for (period, start_key), members in groups.items():
        members = sorted(members, key=node_sort_key)
        primary = [node for node in members if is_primary_node(node)]
        team_context = [node for node in members if is_team_context_node(node)]
        unsupported = [node for node in members if node not in primary and node not in team_context]
        if unsupported:
            blocks.extend(
                f"unsupported_sequence_node_role:{clean(node.get('selected_action_node_id'))}"
                for node in unsupported
            )
        primary_teams = sorted(
            {
                clean(node.get("team_identity_candidate_id"))
                for node in primary
                if clean(node.get("team_identity_candidate_id"))
            }
        )
        context_teams = sorted(
            {
                clean(node.get("team_identity_candidate_id"))
                for node in team_context
                if clean(node.get("team_identity_candidate_id"))
            }
        )
        if len(primary_teams) == 1:
            state = "SINGLE_TEAM_PRIMARY_LAYER"
        elif len(primary_teams) > 1:
            state = "MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED"
        elif team_context:
            state = "TEAM_CONTEXT_ONLY_LAYER"
        else:
            state = "UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED"

        primary_ids = [clean(node.get("selected_action_node_id")) for node in primary]
        context_ids = [clean(node.get("selected_action_node_id")) for node in team_context]
        families = Counter(
            clean(family)
            for node in primary
            for family in (node.get("action_family_candidates") or [])
            if clean(family)
        )
        context_families = Counter(
            clean(family)
            for node in team_context
            for family in (node.get("action_family_candidates") or [])
            if clean(family)
        )
        unresolved_count = sum(
            clean(event_by_node[node_id].get("consequence_class_candidate"))
            == "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"
            for node_id in primary_ids
        )
        layer_id = "vatl_" + digest(binding, period, start_key, primary_ids, context_ids)[:24]
        layers.append(
            {
                "visible_action_time_layer_candidate_id": layer_id,
                "match_surface_binding_id": binding,
                "period_candidate": period,
                "start_candidate": float(start_key),
                "layer_state": state,
                "primary_team_identity_candidate_ids": primary_teams,
                "team_context_identity_candidate_ids": context_teams,
                "primary_selected_action_node_ids": primary_ids,
                "team_context_selected_action_node_ids": context_ids,
                "primary_node_count": len(primary_ids),
                "team_context_node_count": len(context_ids),
                "primary_action_family_counts": dict(sorted(families.items())),
                "team_context_action_family_counts": dict(sorted(context_families.items())),
                "unresolved_event_consequence_context_count": unresolved_count,
                "same_timestamp_internal_ordering_allowed": False,
                "time_layer_is_event_group_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
    layers.sort(
        key=lambda layer: (
            period_sort_key(layer.get("period_candidate")),
            layer.get("start_candidate"),
            layer.get("visible_action_time_layer_candidate_id"),
        )
    )
    return layers, sorted(set(blocks))
