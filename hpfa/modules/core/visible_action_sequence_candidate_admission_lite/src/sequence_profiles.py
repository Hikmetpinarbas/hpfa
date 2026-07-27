from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .common import CANONICAL_EVENT_COUNT, clean
except ImportError:
    from common import CANONICAL_EVENT_COUNT, clean


def build_sequence_profiles(
    sequences: list[dict[str, Any]],
    node_by_id: dict[str, dict[str, Any]],
    identity_field: str,
    profile_type: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for sequence in sequences:
        primary_nodes = [
            node_by_id[node_id]
            for node_id in sequence.get("primary_selected_action_node_ids") or []
            if node_id in node_by_id
        ]
        seen_pairs: set[tuple[str, str]] = set()
        for node in primary_nodes:
            identity = clean(
                sequence.get("team_identity_candidate_id")
                if identity_field == "team_identity_candidate_id"
                else node.get(identity_field)
            )
            for family in node.get("action_family_candidates") or []:
                pair = (identity, clean(family))
                if identity and pair not in seen_pairs:
                    grouped[pair].append(sequence)
                    seen_pairs.add(pair)
    output = []
    for (identity, family), rows in sorted(grouped.items()):
        output.append(
            {
                "profile_type": profile_type,
                "identity_candidate_id": identity,
                "action_family_candidate": family,
                "visible_sequence_candidate_count": len(rows),
                "multi_layer_sequence_candidate_count": sum(
                    int(row.get("time_layer_count") or 0) >= 2 for row in rows
                ),
                "trace_signal_candidate_counts": dict(
                    sorted(
                        Counter(
                            signal
                            for row in rows
                            for signal in (row.get("trace_signal_candidates") or [])
                        ).items()
                    )
                ),
                "sequence_consequence_composition_candidate_counts": dict(
                    sorted(
                        Counter(
                            clean(row.get("sequence_consequence_composition_candidate"))
                            for row in rows
                        ).items()
                    )
                ),
                "profile_is_quality_truth": False,
                "profile_is_possession_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
    return output
