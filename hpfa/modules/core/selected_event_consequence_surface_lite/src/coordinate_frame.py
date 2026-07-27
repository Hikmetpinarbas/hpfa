from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any

try:
    from .common import clean, number
except ImportError:
    from common import clean, number

SHOT_FAMILY = "SHOT"


def _scale_candidate(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    coords = []
    for node in nodes:
        x = number(node.get("pos_x_candidate"))
        y = number(node.get("pos_y_candidate"))
        if x is not None and y is not None:
            coords.append((x, y))
    base = {
        "coordinate_scale_candidate": "UNRESOLVED_COORDINATE_SCALE_REVIEW_REQUIRED",
        "pitch_length_candidate": None,
        "pitch_width_candidate": None,
        "coordinate_bounds_status": "UNRESOLVED",
        "observed_coordinate_count": len(coords),
        "observed_x_min": None,
        "observed_x_max": None,
        "observed_y_min": None,
        "observed_y_max": None,
    }
    if not coords:
        return base
    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    base.update({
        "observed_x_min": min(xs),
        "observed_x_max": max(xs),
        "observed_y_min": min(ys),
        "observed_y_max": max(ys),
    })
    if min(xs) >= -0.5 and min(ys) >= -0.5 and max(xs) <= 105.5 and max(ys) <= 68.5 and max(xs) >= 100 and max(ys) >= 64:
        base.update({
            "coordinate_scale_candidate": "PROVIDER_105X68_SCALE_CANDIDATE",
            "pitch_length_candidate": 105.0,
            "pitch_width_candidate": 68.0,
            "coordinate_bounds_status": "PASS_CANDIDATE_BOUNDS",
        })
    elif min(xs) >= -0.5 and min(ys) >= -0.5 and max(xs) <= 100.5 and max(ys) <= 100.5 and max(xs) >= 95 and max(ys) >= 95:
        base.update({
            "coordinate_scale_candidate": "PROVIDER_100X100_SCALE_CANDIDATE",
            "pitch_length_candidate": 100.0,
            "pitch_width_candidate": 100.0,
            "coordinate_bounds_status": "PASS_CANDIDATE_BOUNDS",
        })
    else:
        base["coordinate_bounds_status"] = "OUTSIDE_SUPPORTED_SCALE_REVIEW_REQUIRED"
    return base


def resolve_coordinate_frame(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    scale = _scale_candidate(nodes)
    length = scale.get("pitch_length_candidate")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    action_group_counts: Counter[tuple[str, str]] = Counter()
    for node in nodes:
        team = clean(node.get("team_identity_candidate_id"))
        period = clean(node.get("period_candidate"))
        if team and period:
            action_group_counts[(team, period)] += 1
        if SHOT_FAMILY in set(node.get("action_family_candidates") or []) and team and period:
            groups[(team, period)].append(node)
    direction_records = []
    direction_map: dict[str, str] = {}
    for group in sorted(action_group_counts):
        shots = groups.get(group, [])
        xs = [number(node.get("pos_x_candidate")) for node in shots]
        xs = [x for x in xs if x is not None]
        direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"
        support_status = "INSUFFICIENT_SHOT_SUPPORT"
        high_share = low_share = None
        med = None
        if length and len(xs) >= 3:
            normalized = [x / length for x in xs]
            med = median(normalized)
            high_share = sum(value >= 0.70 for value in normalized) / len(normalized)
            low_share = sum(value <= 0.30 for value in normalized) / len(normalized)
            if med >= 0.72 and high_share >= 0.75:
                direction = "ATTACK_TOWARD_HIGH_X_CANDIDATE"
                support_status = "PASS_SHOT_CONCENTRATION_CANDIDATE"
            elif med <= 0.28 and low_share >= 0.75:
                direction = "ATTACK_TOWARD_LOW_X_CANDIDATE"
                support_status = "PASS_SHOT_CONCENTRATION_CANDIDATE"
            else:
                support_status = "SHOT_CONCENTRATION_AMBIGUOUS_REVIEW_REQUIRED"
        key = f"{group[0]}|{group[1]}"
        direction_map[key] = direction
        direction_records.append({
            "team_identity_candidate_id": group[0],
            "period_candidate": group[1],
            "selected_action_node_count": action_group_counts[group],
            "shot_support_node_count": len(xs),
            "shot_normalized_x_median": None if med is None else round(med, 6),
            "shot_high_x_share": None if high_share is None else round(high_share, 6),
            "shot_low_x_share": None if low_share is None else round(low_share, 6),
            "attack_direction_candidate": direction,
            "attack_direction_support_status": support_status,
            "attack_direction_is_validated_truth": False,
        })
    resolved = {"ATTACK_TOWARD_HIGH_X_CANDIDATE", "ATTACK_TOWARD_LOW_X_CANDIDATE"}
    all_resolved = bool(direction_records) and all(row["attack_direction_candidate"] in resolved for row in direction_records)
    frame_status = "PASS_CANDIDATE_FRAME" if scale.get("coordinate_bounds_status") == "PASS_CANDIDATE_BOUNDS" and all_resolved else "REVIEW_REQUIRED"
    return {
        **scale,
        "coordinate_frame_status": frame_status,
        "team_period_attack_direction_candidates": direction_records,
        "team_period_attack_direction_map": direction_map,
        "coordinate_frame_is_validated_provider_truth": False,
        "attack_direction_is_validated_truth": False,
        "zone_grid_is_value_model": False,
    }


def direction_for(node: dict[str, Any], frame: dict[str, Any]) -> str:
    key = f"{clean(node.get('team_identity_candidate_id'))}|{clean(node.get('period_candidate'))}"
    return clean((frame.get("team_period_attack_direction_map") or {}).get(key))


def zone_candidate(node: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    length = number(frame.get("pitch_length_candidate"))
    width = number(frame.get("pitch_width_candidate"))
    direction = direction_for(node, frame)
    x = number(node.get("pos_x_candidate"))
    y = number(node.get("pos_y_candidate"))
    base = {
        "zone_candidate": "UNRESOLVED_ZONE_REVIEW_REQUIRED",
        "zone_rank_candidate": None,
        "attack_progress_ratio_candidate": None,
        "normalized_lateral_ratio_candidate": None,
        "zone_candidate_status": "UNRESOLVED",
        "high_value_grid_is_goal_probability_truth": False,
    }
    if frame.get("coordinate_frame_status") != "PASS_CANDIDATE_FRAME" or not length or not width or x is None or y is None:
        return base
    if direction == "ATTACK_TOWARD_HIGH_X_CANDIDATE":
        progress = x / length
    elif direction == "ATTACK_TOWARD_LOW_X_CANDIDATE":
        progress = 1.0 - (x / length)
    else:
        return base
    lateral = y / width
    if not (-0.01 <= progress <= 1.01 and -0.01 <= lateral <= 1.01):
        base["zone_candidate_status"] = "OUT_OF_FRAME_REVIEW_REQUIRED"
        return base
    if progress < 1 / 3:
        zone, rank = "OWN_THIRD_CANDIDATE", 0
    elif progress < 2 / 3:
        zone, rank = "MIDDLE_THIRD_CANDIDATE", 1
    elif progress < (88.5 / 105.0 if length == 105 else 0.84):
        zone, rank = "FINAL_THIRD_OUTSIDE_BOX_CANDIDATE", 2
    else:
        in_box_band = (13.84 / 68.0 <= lateral <= 54.16 / 68.0) if width == 68 else (0.20 <= lateral <= 0.80)
        deep_central = progress >= 0.90 and 0.33 <= lateral <= 0.67
        if deep_central:
            zone, rank = "CENTRAL_DEEP_BOX_GRID_CANDIDATE", 4
        elif in_box_band:
            zone, rank = "BOX_COORDINATE_CANDIDATE", 3
        else:
            zone, rank = "FINAL_THIRD_WIDE_OR_OUTSIDE_BOX_BAND_CANDIDATE", 2
    base.update({
        "zone_candidate": zone,
        "zone_rank_candidate": rank,
        "attack_progress_ratio_candidate": round(progress, 6),
        "normalized_lateral_ratio_candidate": round(lateral, 6),
        "zone_candidate_status": "PASS_CANDIDATE_ZONE",
    })
    return base
