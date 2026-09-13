from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "OBSERVED_ANCHOR_CENTERED_SEQUENCE_BRANCHING_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _count_dict(values: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in values:
        if not isinstance(row, dict):
            continue
        label = _clean(row.get(key))
        if not label:
            continue
        try:
            count = int(row.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            counts[label] += count
    return dict(sorted(counts.items()))


def build_anchor_centered_sequence_branch_maps(payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if payload.get("primary_sequence_projection_mode") != "OCCURRENCE_TEMPORAL_PRIMARY":
        blocks.append("occurrence_temporal_primary_inventory_not_admitted")
    if payload.get("occurrence_temporal_primary_inventory_admitted") is not True:
        blocks.append("occurrence_temporal_primary_inventory_flag_not_true")
    if payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if payload.get("sequence_truth") is True or payload.get("possession_truth") is True:
        blocks.append("upstream_truth_promotion_breached")
    if payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    layers = [row for row in (payload.get("visible_action_time_layer_candidates") or []) if isinstance(row, dict)]
    sequences = [row for row in (payload.get("visible_action_sequence_candidates") or []) if isinstance(row, dict)]
    layer_by_id = {
        _clean(row.get("visible_action_time_layer_candidate_id")): row
        for row in layers
        if _clean(row.get("visible_action_time_layer_candidate_id"))
    }

    # One anchor key is team + period + admitted time-layer candidate. Sequence ids may branch
    # away from or converge into the same anchor. We never convert branch count into recurrence.
    neighbors: dict[tuple[str, str, str], dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: {"PREDECESSOR": defaultdict(set), "SUCCESSOR": defaultdict(set)}
    )
    sequence_by_id: dict[str, dict[str, Any]] = {}

    for sequence in sequences:
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        team = _clean(sequence.get("team_identity_candidate_id"))
        period = _clean(sequence.get("period_candidate"))
        layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
        if not sequence_id or not team or not period or len(layer_ids) < 2:
            reviews.append(f"branch_map_sequence_not_eligible:{sequence_id or 'UNKNOWN'}")
            continue
        if sequence.get("same_timestamp_internal_ordering_allowed") is not False:
            blocks.append(f"branch_map_sequence_same_time_policy_breached:{sequence_id}")
            continue
        if sequence.get("source_row_order_is_temporal_truth") is not False:
            blocks.append(f"branch_map_sequence_row_order_policy_breached:{sequence_id}")
            continue
        if sequence.get("visible_sequence_candidate_is_sequence_truth") is True:
            blocks.append(f"branch_map_sequence_truth_promotion_breached:{sequence_id}")
            continue
        if any(layer_id not in layer_by_id for layer_id in layer_ids):
            blocks.append(f"branch_map_layer_reference_missing:{sequence_id}")
            continue

        sequence_by_id[sequence_id] = sequence
        for idx, anchor_layer_id in enumerate(layer_ids):
            key = (team, period, anchor_layer_id)
            if idx > 0:
                neighbors[key]["PREDECESSOR"][layer_ids[idx - 1]].add(sequence_id)
            if idx + 1 < len(layer_ids):
                neighbors[key]["SUCCESSOR"][layer_ids[idx + 1]].add(sequence_id)

    branch_maps: list[dict[str, Any]] = []
    for (team, period, anchor_layer_id), direction_map in sorted(neighbors.items()):
        predecessor_ids = sorted(direction_map["PREDECESSOR"])
        successor_ids = sorted(direction_map["SUCCESSOR"])
        # A branch surface needs at least two distinct visible paths around the same anchor.
        if len(predecessor_ids) + len(successor_ids) < 2:
            continue

        anchor = layer_by_id.get(anchor_layer_id)
        if anchor is None:
            blocks.append(f"branch_map_anchor_layer_missing:{anchor_layer_id}")
            continue

        branch_records: list[dict[str, Any]] = []
        supporting_sequence_ids: set[str] = set()
        supporting_occurrence_ids: set[str] = {
            _clean(value)
            for value in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
            if _clean(value)
        }

        for direction in ("PREDECESSOR", "SUCCESSOR"):
            for neighbor_layer_id, sequence_ids_set in sorted(direction_map[direction].items()):
                neighbor = layer_by_id.get(neighbor_layer_id)
                if neighbor is None:
                    blocks.append(f"branch_map_neighbor_layer_missing:{neighbor_layer_id}")
                    continue
                sequence_ids = sorted(sequence_ids_set)
                supporting_sequence_ids.update(sequence_ids)
                branch_occurrence_ids = sorted({
                    _clean(value)
                    for value in (neighbor.get("supporting_action_occurrence_candidate_ids") or [])
                    if _clean(value)
                })
                supporting_occurrence_ids.update(branch_occurrence_ids)

                consequence_counts: Counter[str] = Counter()
                consequence_ids: set[str] = set()
                for sequence_id in sequence_ids:
                    sequence = sequence_by_id.get(sequence_id) or {}
                    consequence_counts.update(sequence.get("consequence_candidate_counts") or {})
                    consequence_ids.update(
                        _clean(value)
                        for value in (sequence.get("supporting_consequence_candidate_ids") or [])
                        if _clean(value)
                    )

                branch_records.append({
                    "branch_direction": direction,
                    "neighbor_time_layer_ref": neighbor_layer_id,
                    "neighbor_time_candidate": neighbor.get("start_candidate"),
                    "neighbor_action_family_counts": dict(sorted((neighbor.get("action_family_counts") or {}).items())),
                    "neighbor_supporting_action_occurrence_candidate_ids": branch_occurrence_ids,
                    "supporting_visible_sequence_candidate_ids": sequence_ids,
                    "supporting_consequence_candidate_ids": sorted(consequence_ids),
                    "observed_consequence_candidate_counts": dict(sorted(consequence_counts.items())),
                    "branch_supporting_sequence_count": len(sequence_ids),
                    "branch_support_count_is_recurrence_count": False,
                    "branch_is_tactical_route_truth": False,
                    "branch_is_causal_path_truth": False,
                })

        if blocks:
            continue

        predecessor_count = sum(1 for row in branch_records if row["branch_direction"] == "PREDECESSOR")
        successor_count = sum(1 for row in branch_records if row["branch_direction"] == "SUCCESSOR")
        map_id = "acbm_" + _digest(team, period, anchor_layer_id, branch_records)[:24]
        branch_maps.append({
            "anchor_centered_sequence_branch_map_id": map_id,
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "anchor_type": "OCCURRENCE_TEMPORAL_TIME_LAYER_CANDIDATE",
            "anchor_time_layer_ref": anchor_layer_id,
            "anchor_time_candidate": anchor.get("start_candidate"),
            "anchor_action_family_counts": dict(sorted((anchor.get("action_family_counts") or {}).items())),
            "anchor_supporting_action_occurrence_candidate_ids": sorted({
                _clean(value)
                for value in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(value)
            }),
            "predecessor_branch_count": predecessor_count,
            "successor_branch_count": successor_count,
            "total_visible_branch_count": len(branch_records),
            "branch_records": branch_records,
            "supporting_visible_sequence_candidate_ids": sorted(supporting_sequence_ids),
            "supporting_action_occurrence_candidate_ids": sorted(supporting_occurrence_ids),
            "branch_count_is_recurrence_count": False,
            "branch_map_is_sequence_truth": False,
            "branch_map_is_possession_truth": False,
            "branch_map_is_tactical_plan_truth": False,
            "branch_map_is_causal_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or str(payload.get("status") or "").upper() == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "anchor_centered_sequence_branch_maps": branch_maps if not blocks else [],
        "anchor_centered_sequence_branch_map_count": len(branch_maps) if not blocks else 0,
        "source_visible_action_sequence_candidate_count": len(sequences),
        "source_visible_action_time_layer_candidate_count": len(layers),
        "total_visible_branch_count": sum(row.get("total_visible_branch_count", 0) for row in branch_maps) if not blocks else 0,
        "branch_count_is_recurrence_count": False,
        "branch_map_is_sequence_truth": False,
        "branch_map_is_possession_truth": False,
        "branch_map_is_tactical_plan_truth": False,
        "branch_map_is_causal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
