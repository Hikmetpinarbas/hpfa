from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "visible_geometry_lens_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
CLAIM_CEILING = "RAW_PROVIDER_COORDINATE_POINT_DISTRIBUTION_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
OUTPUT_JSON = "visible_geometry_lens_lite_v1.json"
OUTPUT_TXT = "visible_geometry_lens_lite_v1.txt"
ANALYST_TXT = "visible_geometry_lens_analyst_audit_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _number(value: Any) -> float | None:
    try:
        number = float(_clean(value))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def _summary(points: list[tuple[float, float]]) -> dict[str, Any]:
    if not points:
        return {
            "coordinate_point_count": 0,
            "centroid_x_candidate": None,
            "centroid_y_candidate": None,
            "median_x_candidate": None,
            "median_y_candidate": None,
            "x_span_candidate": None,
            "y_span_candidate": None,
            "x_std_candidate": None,
            "y_std_candidate": None,
            "rms_radial_dispersion_candidate": None,
            "central_80_x_span_candidate": None,
            "central_80_y_span_candidate": None,
            "central_80_rectangle_area_candidate": None,
        }
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx = statistics.fmean(xs)
    cy = statistics.fmean(ys)
    radial = [math.hypot(x - cx, y - cy) for x, y in points]
    x10, x90 = _quantile(xs, 0.10), _quantile(xs, 0.90)
    y10, y90 = _quantile(ys, 0.10), _quantile(ys, 0.90)
    x80 = (x90 - x10) if x10 is not None and x90 is not None else None
    y80 = (y90 - y10) if y10 is not None and y90 is not None else None
    return {
        "coordinate_point_count": len(points),
        "centroid_x_candidate": round(cx, 4),
        "centroid_y_candidate": round(cy, 4),
        "median_x_candidate": round(statistics.median(xs), 4),
        "median_y_candidate": round(statistics.median(ys), 4),
        "min_x_candidate": round(min(xs), 4),
        "max_x_candidate": round(max(xs), 4),
        "min_y_candidate": round(min(ys), 4),
        "max_y_candidate": round(max(ys), 4),
        "x_span_candidate": round(max(xs) - min(xs), 4),
        "y_span_candidate": round(max(ys) - min(ys), 4),
        "x_std_candidate": round(statistics.pstdev(xs), 4),
        "y_std_candidate": round(statistics.pstdev(ys), 4),
        "rms_radial_dispersion_candidate": round(
            math.sqrt(statistics.fmean([r * r for r in radial])), 4
        ),
        "central_80_x_span_candidate": round(x80, 4) if x80 is not None else None,
        "central_80_y_span_candidate": round(y80, 4) if y80 is not None else None,
        "central_80_rectangle_area_candidate": (
            round(x80 * y80, 4) if x80 is not None and y80 is not None else None
        ),
    }


def build_visible_geometry_lens(
    trace_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Summarize raw provider-coordinate point distributions by team/player/period.

    No attacking-direction normalization is assumed. Therefore x/y centroids and
    dispersion are descriptive provider-coordinate geometry only; they are not
    formation, average-position role, pitch-control, team-shape, width, compactness,
    territorial control or movement-trajectory truth.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_module_id_mismatch")
    if identity_payload.get("module_id") != IDENTITY_MODULE_ID:
        blocks.append("identity_module_id_mismatch")
    for label, payload in (("trace", trace_payload), ("identity", identity_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")
        if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED":
            blocks.append(f"{label}_input_fail_closed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{label}_input_hard_blocked")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    actors = identity_payload.get("actor_identity_candidates") or []
    teams = identity_payload.get("team_identity_candidates") or []
    if not isinstance(traces, list):
        blocks.append("trace_collection_invalid")
        traces = []
    if not isinstance(actors, list):
        blocks.append("actor_identity_collection_invalid")
        actors = []
    if not isinstance(teams, list):
        blocks.append("team_identity_collection_invalid")
        teams = []

    actor_meta = {
        _clean(row.get("actor_identity_candidate_id")): row
        for row in actors
        if isinstance(row, dict) and _clean(row.get("actor_identity_candidate_id"))
    }
    team_meta = {
        _clean(row.get("team_identity_candidate_id")): row
        for row in teams
        if isinstance(row, dict) and _clean(row.get("team_identity_candidate_id"))
    }

    team_points: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    actor_points: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    all_points: list[tuple[float, float]] = []
    coordinate_missing = 0
    team_missing = 0
    actor_missing = 0

    if not blocks:
        for row in traces:
            if not isinstance(row, dict):
                continue
            x = _number(row.get("pos_x_candidate"))
            y = _number(row.get("pos_y_candidate"))
            if x is None or y is None or row.get("coordinate_evidence_status") != "COORDINATE_PRESENT":
                coordinate_missing += 1
                continue
            team_id = _clean(row.get("team_identity_candidate_id"))
            actor_id = _clean(row.get("actor_identity_candidate_id"))
            period = _clean(row.get("period_candidate")) or "UNKNOWN_PERIOD"
            if not team_id:
                team_missing += 1
                continue
            team_points[(team_id, period)].append((x, y))
            all_points.append((x, y))
            if actor_id:
                actor_points[(actor_id, team_id, period)].append((x, y))
            else:
                actor_missing += 1

    team_rows = []
    for (team_id, period), points in sorted(team_points.items()):
        meta = team_meta.get(team_id) or {}
        team_rows.append({
            "team_identity_candidate_id": team_id,
            "team_normalized_key_candidate": meta.get("team_normalized_key"),
            "period_candidate": period,
            **_summary(points),
            "direction_normalized": False,
            "centroid_is_average_position_or_formation_truth": False,
            "dispersion_is_team_shape_or_compactness_truth": False,
            "coordinate_distribution_is_territorial_control_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    player_rows = []
    for (actor_id, team_id, period), points in sorted(actor_points.items()):
        actor = actor_meta.get(actor_id) or {}
        player_rows.append({
            "actor_identity_candidate_id": actor_id,
            "actor_normalized_key_candidate": actor.get("actor_normalized_key"),
            "team_identity_candidate_id": team_id,
            "period_candidate": period,
            **_summary(points),
            "direction_normalized": False,
            "centroid_is_player_position_or_role_truth": False,
            "dispersion_is_mobility_or_work_rate_truth": False,
            "coordinate_distribution_is_off_ball_movement_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    overall = _summary(all_points)
    if all_points:
        overall["observed_coordinate_domain_candidate"] = {
            "min_x": overall.get("min_x_candidate"),
            "max_x": overall.get("max_x_candidate"),
            "min_y": overall.get("min_y_candidate"),
            "max_y": overall.get("max_y_candidate"),
        }

    for label, payload in (("trace", trace_payload), ("identity", identity_payload)):
        if _status(payload.get("status") or payload.get("module_status")) == "REVIEW_REQUIRED":
            reviews.append(f"{label}_upstream_review_required")

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "VISIBLE_GEOMETRY_LENS_BUILT" if not blocks else "VISIBLE_GEOMETRY_LENS_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "overall_coordinate_surface": overall if not blocks else {},
        "team_period_geometry_rows": team_rows if not blocks else [],
        "team_period_geometry_row_count": len(team_rows) if not blocks else 0,
        "player_period_geometry_rows": player_rows if not blocks else [],
        "player_period_geometry_row_count": len(player_rows) if not blocks else 0,
        "coordinate_missing_or_unadmitted_trace_count": coordinate_missing if not blocks else 0,
        "team_missing_coordinate_trace_count": team_missing if not blocks else 0,
        "actor_missing_coordinate_trace_count": actor_missing if not blocks else 0,
        "direction_normalized": False,
        "formation_truth": False,
        "team_shape_truth": False,
        "compactness_truth": False,
        "pitch_control_truth": False,
        "territorial_control_truth": False,
        "off_ball_movement_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    analyst_path = output / ANALYST_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA VISIBLE GEOMETRY LENS LITE V1",
        f"status={payload.get('status')}",
        f"team_period_geometry_row_count={payload.get('team_period_geometry_row_count', 0)}",
        f"player_period_geometry_row_count={payload.get('player_period_geometry_row_count', 0)}",
        f"coordinate_point_count={(payload.get('overall_coordinate_surface') or {}).get('coordinate_point_count', 0)}",
        "direction_normalized=false",
        "formation_truth=false",
        "team_shape_truth=false",
        "compactness_truth=false",
        "pitch_control_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    lines = [
        "HPFA ANALYST AUDIT — VISIBLE PROVIDER-COORDINATE GEOMETRY",
        "Geometry is period-conditioned point-distribution evidence only. No attacking-direction normalization is assumed.",
    ]
    for row in payload.get("team_period_geometry_rows") or []:
        lines.append(
            f"- {row.get('team_normalized_key_candidate') or row.get('team_identity_candidate_id')} P{row.get('period_candidate')}: "
            f"points={row.get('coordinate_point_count')} centroid=({row.get('centroid_x_candidate')},{row.get('centroid_y_candidate')}) "
            f"central80=({row.get('central_80_x_span_candidate')} x {row.get('central_80_y_span_candidate')})"
        )
    lines.extend([
        "Do not read these centroids/spreads as formation, team shape, width, compactness, territorial control or player role truth.",
        "",
    ])
    analyst_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "summary": txt_path, "analyst": analyst_path}
