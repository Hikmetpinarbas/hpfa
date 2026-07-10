from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "deterministic_analysis_command_runtime_v1"
PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0
GOAL_WIDTH = 7.32
SUPPORTED_COMMANDS = {
    "RAW-PARSER",
    "MATH-METRIC",
    "TACTIC-MATRIX",
    "DEFENSIVE-ACTION-HEIGHT-PROXY",
    "XT-MATRIX",
    "RAW-DEBUG",
}
SUPPORTED_EVENT_TYPES = {
    "pass", "shot", "tackle", "interception", "foul", "carry", "dribble",
    "ball_recovery", "reception", "touch",
}
TOUCH_EVENT_TYPES = {"pass", "shot", "carry", "dribble", "reception", "touch"}
DEFENSIVE_ACTION_TYPES = {"tackle", "interception", "foul"}
SUCCESS_OUTCOMES = {"success", "successful", "complete", "completed", "won", "true", "1"}
FAILURE_OUTCOMES = {
    "fail", "failed", "failure", "unsuccessful", "incomplete", "incompleted",
    "lost", "false", "0",
}
FIELD_ALIASES = {
    "event_id": ("event_id", "id", "eventId"),
    "event_type": ("event_type", "type", "event", "action", "eventName"),
    "team_id": ("team_id", "team", "teamId", "team_name"),
    "player_id": ("player_id", "player", "playerId", "player_name"),
    "timestamp_s": ("timestamp_s", "second", "seconds", "time_seconds", "timestamp"),
    "minute": ("minute", "min"),
    "period": ("period", "half"),
    "outcome": ("outcome", "result", "success"),
    "x": ("x", "start_x", "x1"),
    "y": ("y", "start_y", "y1"),
    "end_x": ("end_x", "x2", "to_x"),
    "end_y": ("end_y", "y2", "to_y"),
    "attacking_direction": ("attacking_direction", "direction", "attack_direction"),
}


def _first(record: dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    return None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _event_type(value: Any) -> str:
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "passes": "pass",
        "shot_attempt": "shot",
        "attempt": "shot",
        "ball_recovery": "ball_recovery",
        "recovery": "ball_recovery",
        "intercept": "interception",
        "take_on": "dribble",
    }
    return aliases.get(text, text)


def _outcome(value: Any) -> str:
    if isinstance(value, bool):
        return "success" if value else "failure"
    text = _text(value).lower()
    if text in SUCCESS_OUTCOMES:
        return "success"
    if text in FAILURE_OUTCOMES:
        return "failure"
    return "unknown"


def _direction(value: Any) -> str:
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ltr": "left_to_right",
        "lefttoright": "left_to_right",
        "rtl": "right_to_left",
        "righttoleft": "right_to_left",
    }
    return aliases.get(text, text)


def _coord_valid(x: float | None, y: float | None) -> bool:
    return x is not None and y is not None and 0.0 <= x <= PITCH_LENGTH and 0.0 <= y <= PITCH_WIDTH


def normalize_event(raw: Any, row_index: int) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(raw, dict):
        return None, ["event_not_object"]

    event_type = _event_type(_first(raw, FIELD_ALIASES["event_type"]))
    team_id = _text(_first(raw, FIELD_ALIASES["team_id"]))
    player_id = _text(_first(raw, FIELD_ALIASES["player_id"]))
    timestamp = _float(_first(raw, FIELD_ALIASES["timestamp_s"]))
    if timestamp is None:
        minute = _float(_first(raw, FIELD_ALIASES["minute"]))
        timestamp = minute * 60.0 if minute is not None else None

    x = _float(_first(raw, FIELD_ALIASES["x"]))
    y = _float(_first(raw, FIELD_ALIASES["y"]))
    end_x = _float(_first(raw, FIELD_ALIASES["end_x"]))
    end_y = _float(_first(raw, FIELD_ALIASES["end_y"]))
    outcome = _outcome(_first(raw, FIELD_ALIASES["outcome"]))
    reasons: list[str] = []

    if not event_type:
        reasons.append("event_type_missing")
    elif event_type not in SUPPORTED_EVENT_TYPES:
        reasons.append("unsupported_event_type")
    if not team_id:
        reasons.append("team_id_missing")
    if not player_id:
        reasons.append("player_id_missing")
    if timestamp is None or timestamp < 0:
        reasons.append("timestamp_invalid")
    if not _coord_valid(x, y):
        reasons.append("start_coordinate_invalid")
    if event_type in {"pass", "carry"} and not _coord_valid(end_x, end_y):
        reasons.append("end_coordinate_invalid")
    if event_type == "pass" and outcome == "unknown":
        reasons.append("pass_outcome_unknown")

    if reasons:
        return None, reasons

    normalized = {
        "event_id": _text(_first(raw, FIELD_ALIASES["event_id"])) or f"row_{row_index}",
        "source_row_index": row_index,
        "event_type": event_type,
        "team_id": team_id,
        "player_id": player_id,
        "timestamp_s": timestamp,
        "period": _text(_first(raw, FIELD_ALIASES["period"])) or None,
        "outcome": outcome,
        "x": x,
        "y": y,
        "end_x": end_x,
        "end_y": end_y,
        "attacking_direction": _direction(_first(raw, FIELD_ALIASES["attacking_direction"])) or None,
    }
    return normalized, []


def parse_events(raw_events: Any) -> dict[str, Any]:
    if not isinstance(raw_events, list):
        return {
            "status": "FAIL_CLOSED",
            "valid_events": [],
            "invalid_events": [{"source_row_index": None, "reasons": ["input_not_list"]}],
            "surface_row_count": 0,
            "valid_event_record_count": 0,
            "canonical_event_count": "UNKNOWN",
        }

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_events):
        event, reasons = normalize_event(raw, index)
        if event is None:
            invalid.append({"source_row_index": index, "reasons": reasons, "raw_event": raw})
        else:
            valid.append(event)

    passes = [event for event in valid if event["event_type"] == "pass"]
    successful = sum(event["outcome"] == "success" for event in passes)
    pass_rate = successful / len(passes) if passes else None

    touches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in valid:
        if event["event_type"] in TOUCH_EVENT_TYPES:
            touches[event["player_id"]].append(event)
    for player_events in touches.values():
        player_events.sort(key=lambda item: (item["timestamp_s"], item["source_row_index"]))

    status = "PASS" if valid and not invalid else "DEGRADED" if valid else "FAIL_CLOSED"
    return {
        "status": status,
        "surface_row_count": len(raw_events),
        "valid_event_record_count": len(valid),
        "invalid_event_record_count": len(invalid),
        "valid_events": valid,
        "invalid_events": invalid,
        "pass_summary": {
            "attempted": len(passes),
            "successful": successful,
            "success_rate": pass_rate,
        },
        "player_touch_timeline": dict(sorted(touches.items())),
        "canonical_event_count": "UNKNOWN",
        "claim_safety": "VALIDATED_EVENT_RECORDS_NOT_CANONICAL_EVENT_TRUTH",
    }


def _attacking_x(event: dict[str, Any], field: str, coordinate_frame: str) -> float:
    value = event.get(field)
    if value is None:
        raise ValueError(f"{field}_missing")
    x = float(value)
    if coordinate_frame == "attacking_normalized":
        return x
    if coordinate_frame != "absolute_with_direction":
        raise ValueError("coordinate_frame_unsupported")
    direction = event.get("attacking_direction")
    if direction == "left_to_right":
        return x
    if direction == "right_to_left":
        return PITCH_LENGTH - x
    raise ValueError("attacking_direction_required")


def shot_geometry(
    x: float,
    y: float,
    attacking_direction: str = "left_to_right",
    coefficients: dict[str, float] | None = None,
) -> dict[str, Any]:
    if not _coord_valid(_float(x), _float(y)):
        raise ValueError("shot_coordinate_invalid")
    direction = _direction(attacking_direction)
    shot_x = float(x) if direction == "left_to_right" else PITCH_LENGTH - float(x) if direction == "right_to_left" else None
    if shot_x is None:
        raise ValueError("attacking_direction_required")

    goal_x = PITCH_LENGTH
    goal_y = PITCH_WIDTH / 2.0
    half_goal = GOAL_WIDTH / 2.0
    dx = goal_x - shot_x
    dy = goal_y - float(y)
    distance = math.hypot(dx, dy)

    left_vector = (goal_x - shot_x, goal_y - half_goal - float(y))
    right_vector = (goal_x - shot_x, goal_y + half_goal - float(y))
    cross = abs(left_vector[0] * right_vector[1] - left_vector[1] * right_vector[0])
    dot = left_vector[0] * right_vector[0] + left_vector[1] * right_vector[1]
    angle = math.atan2(cross, dot)

    coeff = {"intercept": -0.5, "distance": -0.09, "angle": 1.8}
    if coefficients:
        coeff.update({key: float(value) for key, value in coefficients.items() if key in coeff})
    z = coeff["intercept"] + coeff["distance"] * distance + coeff["angle"] * angle
    probability = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
    return {
        "distance_to_goal_center_m": distance,
        "shot_angle_rad": angle,
        "shot_angle_deg": math.degrees(angle),
        "heuristic_xg_candidate": probability,
        "logistic_z": z,
        "coefficients": coeff,
        "model_status": "HEURISTIC_UNCALIBRATED",
        "claim_boundary": "not_validated_xg_until_fitted_and_calibrated_on_owned_outcome_corpus",
    }


def calculate_ppda(
    events: list[dict[str, Any]],
    defending_team_id: str,
    coordinate_frame: str,
) -> dict[str, Any]:
    team = str(defending_team_id)
    opponent_passes = 0
    defensive_actions = 0
    excluded_orientation = 0

    for event in events:
        try:
            x_norm = _attacking_x(event, "x", coordinate_frame)
        except ValueError:
            excluded_orientation += 1
            continue
        if event["event_type"] == "pass" and event["team_id"] != team and x_norm <= PITCH_LENGTH * 0.60:
            opponent_passes += 1
        if event["event_type"] in DEFENSIVE_ACTION_TYPES and event["team_id"] == team and x_norm >= PITCH_LENGTH * 0.40:
            defensive_actions += 1

    value = opponent_passes / defensive_actions if defensive_actions else None
    return {
        "metric_id": "ppda_event_proxy",
        "defending_team_id": team,
        "opponent_passes_in_build_zone": opponent_passes,
        "defensive_actions_in_equivalent_zone": defensive_actions,
        "value": value,
        "status": "PASS" if defensive_actions else "INSUFFICIENT_DENOMINATOR",
        "excluded_orientation_count": excluded_orientation,
        "defensive_action_types": sorted(DEFENSIVE_ACTION_TYPES),
        "zone_contract": {
            "opponent_actor_frame": "x <= 60% pitch length",
            "defending_actor_frame": "x >= 40% pitch length",
        },
        "claim_boundary": "event_only_pressing_activity_proxy_not_press_intensity_truth",
    }


def defensive_action_height_proxy(
    events: list[dict[str, Any]],
    team_id: str,
    coordinate_frame: str,
) -> dict[str, Any]:
    values: list[float] = []
    excluded_orientation = 0
    for event in events:
        if event["team_id"] != str(team_id) or event["event_type"] not in DEFENSIVE_ACTION_TYPES:
            continue
        try:
            values.append(_attacking_x(event, "x", coordinate_frame))
        except ValueError:
            excluded_orientation += 1
    return {
        "metric_id": "defensive_action_height_proxy",
        "team_id": str(team_id),
        "value_m": sum(values) / len(values) if values else None,
        "sample_size": len(values),
        "excluded_orientation_count": excluded_orientation,
        "status": "PASS" if values else "INSUFFICIENT_SAMPLE",
        "claim_boundary": "average_defensive_action_x_not_defensive_line_height_or_off_ball_shape",
    }


def _fixed_xt_matrix() -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in range(8):
        center_distance = abs((row + 0.5) - 4.0) / 4.0
        centrality = 1.0 - center_distance
        values: list[float] = []
        for column in range(12):
            progress = (column + 0.5) / 12.0
            value = 0.002 + 0.45 * (progress ** 3) * (0.35 + 0.65 * centrality)
            values.append(round(value, 6))
        matrix.append(values)
    return matrix


FIXED_XT_MATRIX_12X8 = _fixed_xt_matrix()


def _cell(x: float, y: float) -> tuple[int, int]:
    column = min(11, max(0, int(x / (PITCH_LENGTH / 12.0))))
    row = min(7, max(0, int(y / (PITCH_WIDTH / 8.0))))
    return row, column


def calculate_xt(
    events: list[dict[str, Any]],
    coordinate_frame: str,
) -> dict[str, Any]:
    player_totals: dict[str, dict[str, Any]] = {}
    action_values: list[dict[str, Any]] = []
    excluded = 0

    for event in events:
        if event["event_type"] not in {"pass", "carry"}:
            continue
        if event["outcome"] == "failure":
            continue
        if event["event_type"] == "pass" and event["outcome"] != "success":
            continue
        try:
            start_x = _attacking_x(event, "x", coordinate_frame)
            end_x = _attacking_x(event, "end_x", coordinate_frame)
        except ValueError:
            excluded += 1
            continue
        start_y = float(event["y"])
        end_y = float(event["end_y"])
        start_row, start_column = _cell(start_x, start_y)
        end_row, end_column = _cell(end_x, end_y)
        start_value = FIXED_XT_MATRIX_12X8[start_row][start_column]
        end_value = FIXED_XT_MATRIX_12X8[end_row][end_column]
        delta = end_value - start_value
        player = event["player_id"]
        totals = player_totals.setdefault(player, {"player_id": player, "net_xt": 0.0, "positive_xt": 0.0, "action_count": 0})
        totals["net_xt"] += delta
        totals["positive_xt"] += max(0.0, delta)
        totals["action_count"] += 1
        action_values.append({
            "event_id": event["event_id"],
            "player_id": player,
            "start_cell": [start_row, start_column],
            "end_cell": [end_row, end_column],
            "xt_delta": delta,
        })

    ranking = sorted(
        player_totals.values(),
        key=lambda item: (-item["positive_xt"], -item["net_xt"], item["player_id"]),
    )
    for item in ranking:
        item["net_xt"] = round(item["net_xt"], 6)
        item["positive_xt"] = round(item["positive_xt"], 6)

    return {
        "metric_id": "fixed_grid_xt_candidate",
        "matrix_rows": 8,
        "matrix_columns": 12,
        "matrix": FIXED_XT_MATRIX_12X8,
        "player_ranking": ranking,
        "action_values": action_values,
        "excluded_orientation_count": excluded,
        "model_status": "HEURISTIC_FIXED_MATRIX_NOT_LEARNED",
        "claim_boundary": "xT_candidate_not_validated_action_value_until_fitted_on_owned_transition_goal_corpus",
    }


def debug_event(raw_event: Any, error_text: str = "") -> dict[str, Any]:
    _, reasons = normalize_event(raw_event, 0)
    error = error_text.lower()
    categories: list[str] = []
    if reasons:
        categories.extend(reasons)
    if any(token in error for token in ("none", "null", "nonetype")):
        categories.append("null_access_candidate")
    if any(token in error for token in ("keyerror", "missing")):
        categories.append("missing_key_candidate")
    if any(token in error for token in ("zero", "division")):
        categories.append("zero_denominator_candidate")
    if any(token in error for token in ("float", "int", "typeerror", "valueerror")):
        categories.append("type_coercion_candidate")
    categories = sorted(set(categories)) or ["unclassified_runtime_error"]
    return {
        "status": "REVIEW_REQUIRED",
        "diagnostic_categories": categories,
        "guard_strategy": [
            "validate object type before field access",
            "resolve aliases before required-field checks",
            "coerce finite numeric values through one boundary function",
            "quarantine invalid rows with source_row_index and reasons",
            "return null plus explicit denominator status instead of infinity",
            "never swallow exceptions without an audit record",
        ],
        "raw_event": raw_event,
        "error_text": error_text,
        "claim_boundary": "deterministic_debug_candidate_not_automatic_root_cause_truth",
    }


def execute_command(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {"module_id": MODULE_ID, "status": "FAIL_CLOSED", "error": "request_not_object"}
    command = _text(request.get("command")).upper()
    if command not in SUPPORTED_COMMANDS:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "command": command,
            "error": "unsupported_command",
            "supported_commands": sorted(SUPPORTED_COMMANDS),
        }

    if command == "RAW-DEBUG":
        result = debug_event(request.get("raw_event"), _text(request.get("error")))
        return {"module_id": MODULE_ID, "command": command, **result}

    if command == "MATH-METRIC":
        shot = request.get("shot") if isinstance(request.get("shot"), dict) else {}
        try:
            result = shot_geometry(
                float(shot.get("x")),
                float(shot.get("y")),
                attacking_direction=_text(shot.get("attacking_direction")) or "left_to_right",
                coefficients=request.get("coefficients") if isinstance(request.get("coefficients"), dict) else None,
            )
        except (TypeError, ValueError) as exc:
            return {"module_id": MODULE_ID, "command": command, "status": "FAIL_CLOSED", "error": str(exc)}
        return {"module_id": MODULE_ID, "command": command, "status": "SMOKE_PASS", "result": result}

    parsed = parse_events(request.get("events"))
    if command == "RAW-PARSER":
        return {"module_id": MODULE_ID, "command": command, **parsed}
    if not parsed["valid_events"]:
        return {
            "module_id": MODULE_ID,
            "command": command,
            "status": "FAIL_CLOSED",
            "parser": parsed,
            "error": "no_valid_event_records",
        }

    frame = _text(request.get("coordinate_frame")) or "attacking_normalized"
    if command == "TACTIC-MATRIX":
        result = calculate_ppda(parsed["valid_events"], _text(request.get("team_id")), frame)
    elif command == "DEFENSIVE-ACTION-HEIGHT-PROXY":
        result = defensive_action_height_proxy(parsed["valid_events"], _text(request.get("team_id")), frame)
    else:
        result = calculate_xt(parsed["valid_events"], frame)

    status = "SMOKE_PASS"
    if parsed["status"] == "DEGRADED" or result.get("status", "PASS") not in {"PASS", "SMOKE_PASS"}:
        status = "REVIEW_REQUIRED"
    return {
        "module_id": MODULE_ID,
        "command": command,
        "status": status,
        "parser_summary": {
            "surface_row_count": parsed["surface_row_count"],
            "valid_event_record_count": parsed["valid_event_record_count"],
            "invalid_event_record_count": parsed["invalid_event_record_count"],
            "canonical_event_count": "UNKNOWN",
        },
        "result": result,
        "production_release": False,
    }


def load_events(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".json":
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError("json_event_input_not_list")
        return value
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError("unsupported_input_format")


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA deterministic analysis command runtime V1")
    parser.add_argument("--request", required=True, help="JSON request file")
    parser.add_argument("--events", help="Optional JSON/CSV event file injected into request")
    parser.add_argument("--out", required=True, help="Output JSON file")
    args = parser.parse_args()

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    if args.events:
        request["events"] = load_events(args.events)
    report = execute_command(request)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": report.get("status"), "command": report.get("command"), "out": args.out}, ensure_ascii=False))
    return 0 if report.get("status") in {"PASS", "SMOKE_PASS", "DEGRADED", "REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
