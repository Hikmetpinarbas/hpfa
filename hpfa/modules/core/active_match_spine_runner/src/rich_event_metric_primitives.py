from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "rich_event_metric_primitives_v1"
CLAIM_SAFETY = "DETERMINISTIC_EVENT_SURFACE_CANDIDATES_ONLY"

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "provider_row_id": ("id", "provider_row_id", "event_id", "row_id"),
    "action": ("action", "event_type", "event", "type", "label", "code"),
    "team": ("team", "team_name", "team_raw", "squad", "side"),
    "player": ("player", "player_name", "player_raw", "actor", "performer"),
    "receiver": ("receiver", "recipient", "target_player", "pass_receiver", "receiver_name"),
    "outcome": ("outcome", "result", "success", "successful", "accurate", "is_successful"),
    "start_time": ("start", "start_time", "time_start", "timestamp", "time"),
    "end_time": ("end", "end_time", "time_end"),
    "period": ("half", "period", "match_period"),
    "start_x": ("start_x", "x", "pos_x", "x1"),
    "start_y": ("start_y", "y", "pos_y", "y1"),
    "end_x": ("end_x", "x_end", "end_pos_x", "x2", "target_x"),
    "end_y": ("end_y", "y_end", "end_pos_y", "y2", "target_y"),
    "coordinate_system": ("coordinate_system", "coordinate_schema", "pitch_coordinate_system", "coordinate_scale"),
    "pitch_length": ("pitch_length", "field_length", "coordinate_max_x"),
    "pitch_width": ("pitch_width", "field_width", "coordinate_max_y"),
    "attacking_direction": ("attacking_direction", "attack_direction", "playing_direction", "coordinate_direction"),
    "coordinate_system_admission_status": ("coordinate_system_admission_status", "coordinate_admission_status", "coordinate_gate_status"),
    "attacking_direction_admission_status": ("attacking_direction_admission_status", "direction_admission_status", "attacking_direction_gate_status"),
}

SUCCESS_VALUES = {"1", "true", "yes", "success", "successful", "complete", "completed", "accurate", "won"}
FAILURE_VALUES = {"0", "false", "no", "fail", "failed", "failure", "incomplete", "inaccurate", "lost", "unsuccessful"}


def _norm_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace(" ", "_").replace("-", "_")


def _norm_text(value: Any) -> str | None:
    text = " ".join(str(value or "").strip().split())
    return text if text else None


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _source_role(path: Path) -> str:
    name = path.name.casefold()
    if "goalkeeper" in name:
        return "GOALKEEPER"
    if "player" in name:
        return "PLAYER"
    if "team" in name:
        return "TEAM"
    return "UNKNOWN"


def _source_namespace(path: Path) -> str:
    """Cross-format namespace only; preserves export suffixes such as (1)/(2)."""
    return _norm_key(path.stem)


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:4096]
    first = (sample.splitlines() or [""])[0]
    candidates = {",": first.count(","), ";": first.count(";"), "\t": first.count("\t"), "|": first.count("|")}
    return max(candidates, key=candidates.get) if max(candidates.values()) > 0 else ","


def _flatten_xml_instance(instance: ET.Element) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for child in list(instance):
        tag = _norm_key(child.tag)
        if tag == "label":
            group = None
            text = None
            for nested in list(child):
                ntag = _norm_key(nested.tag)
                value = _norm_text(nested.text)
                if ntag == "group":
                    group = value
                elif ntag == "text":
                    text = value
            if group and text:
                raw.setdefault(group, text)
            continue
        value = _norm_text(child.text)
        if value is not None:
            raw.setdefault(child.tag, value)
        for key, attr_value in child.attrib.items():
            raw.setdefault(key, attr_value)
    for key, value in instance.attrib.items():
        raw.setdefault(key, value)
    return raw


def _read_raw(path: Path) -> list[dict[str, Any]]:
    if path.suffix.casefold() in {".csv", ".tsv"}:
        delim = "\t" if path.suffix.casefold() == ".tsv" else _detect_delimiter(path)
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return [dict(row) for row in csv.DictReader(f, delimiter=delim)]
    if path.suffix.casefold() == ".xml":
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            return []
        return [_flatten_xml_instance(node) for node in root.iter() if _norm_key(node.tag) == "instance"]
    return []


def _lower_row(raw: dict[str, Any]) -> dict[str, Any]:
    return {_norm_key(key): value for key, value in raw.items()}


def _first(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        value = row.get(_norm_key(alias))
        if value not in (None, ""):
            return value
    return None


def _semantic_values(raw: dict[str, Any]) -> dict[str, Any]:
    row = _lower_row(raw)
    return {name: _first(row, aliases) for name, aliases in FIELD_ALIASES.items()}


def _outcome_candidate(value: Any) -> str:
    text = _norm_key(value)
    if text in SUCCESS_VALUES:
        return "SUCCESS_CANDIDATE"
    if text in FAILURE_VALUES:
        return "FAILURE_CANDIDATE"
    return "UNKNOWN_OUTCOME"


def _is_admitted_status(value: Any) -> bool:
    return _norm_key(value) in {"admitted", "validated", "pass", "approved"}


def _coordinate_context(resolved: dict[str, Any], source_namespace: Any) -> dict[str, Any]:
    label = _norm_key(resolved.get("coordinate_system"))
    length = _num(resolved.get("pitch_length"))
    width = _num(resolved.get("pitch_width"))
    basis = None

    if length is not None and width is not None and length > 0 and width > 0:
        basis = "EXPLICIT_DIMENSIONS"
    elif label in {"0_100", "0to100", "normalized_0_100", "normalized100", "percentage", "percent"}:
        length, width, basis = 100.0, 100.0, "EXPLICIT_NORMALIZED_0_100_LABEL"
    elif label:
        match = re.fullmatch(r"(?:meters?_?)?(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", label)
        if match:
            length, width = float(match.group(1)), float(match.group(2))
            if length > 0 and width > 0:
                basis = "EXPLICIT_DIMENSION_LABEL"

    admission_status_ok = _is_admitted_status(resolved.get("coordinate_system_admission_status"))
    source_scope_ok = _norm_text(source_namespace) is not None
    admitted = bool(admission_status_ok and source_scope_ok and basis and length is not None and width is not None)
    if admitted:
        admission_basis = f"{basis}:EXPLICIT_SOURCE_SCOPED_ADMISSION"
    elif not admission_status_ok:
        admission_basis = "WITHHELD_NO_EXPLICIT_COORDINATE_ADMISSION"
    elif not source_scope_ok:
        admission_basis = "WITHHELD_NO_SOURCE_NAMESPACE"
    else:
        admission_basis = "WITHHELD_NO_EXPLICIT_COORDINATE_SYSTEM"
    return {
        "coordinate_system_admitted": admitted,
        "coordinate_system_basis": admission_basis,
        "pitch_length": length if admitted else None,
        "pitch_width": width if admitted else None,
    }


def _attack_sign(value: Any) -> int | None:
    text = _norm_key(value)
    if text in {"left_to_right", "ltr", "increasing_x", "positive_x", "plus_x", "+x", "1"}:
        return 1
    if text in {"right_to_left", "rtl", "decreasing_x", "negative_x", "minus_x", "_x", "-1"}:
        return -1
    return None


def _coord_in_range(value: float | None, maximum: float | None) -> bool:
    return value is not None and maximum is not None and 0.0 <= value <= maximum


def _normalized_xy(x: float, y: float, length: float, width: float, attack_sign: int) -> tuple[float, float]:
    if attack_sign == 1:
        return x, y
    return length - x, width - y


def _pitch_zone(x: float | None, y: float | None, length: float | None, width: float | None) -> str | None:
    if x is None or y is None or length is None or width is None:
        return None
    if not (_coord_in_range(x, length) and _coord_in_range(y, width)):
        return None
    x_idx = min(2, int((x / length) * 3)) if x < length else 2
    y_idx = min(2, int((y / width) * 3)) if y < width else 2
    return f"PITCH_X_THIRD_{x_idx + 1}:WIDTH_BAND_{y_idx + 1}"


def _attacking_zone(x: float | None, y: float | None, length: float | None, width: float | None, attack_sign: int | None) -> str | None:
    if x is None or y is None or length is None or width is None or attack_sign is None:
        return None
    if not (_coord_in_range(x, length) and _coord_in_range(y, width)):
        return None
    nx, ny = _normalized_xy(x, y, length, width, attack_sign)
    third = "DEFENSIVE_THIRD" if nx < length / 3 else "MIDDLE_THIRD" if nx < 2 * length / 3 else "FINAL_THIRD"
    channel = "LEFT" if ny < width / 3 else "CENTRAL" if ny < 2 * width / 3 else "RIGHT"
    return f"{third}:{channel}"


def _direction(normalized_dx: float | None, pitch_length: float | None) -> str | None:
    if normalized_dx is None or pitch_length is None:
        return None
    threshold = pitch_length * 0.01
    if abs(normalized_dx) < threshold:
        return "LATERAL_CANDIDATE"
    return "FORWARD_CANDIDATE" if normalized_dx > 0 else "BACKWARD_CANDIDATE"


def _attacking_third_index(x: float | None, length: float | None, attack_sign: int | None) -> int | None:
    if x is None or length is None or attack_sign is None or not _coord_in_range(x, length):
        return None
    nx = x if attack_sign == 1 else length - x
    return 0 if nx < length / 3 else 1 if nx < 2 * length / 3 else 2


def _geometric_third_skip(start_x: float | None, end_x: float | None, length: float | None, attack_sign: int | None) -> int | None:
    a = _attacking_third_index(start_x, length, attack_sign)
    b = _attacking_third_index(end_x, length, attack_sign)
    if a is None or b is None:
        return None
    return max(0, abs(b - a) - 1)


def build_projection(active_match_dir: str | Path) -> dict[str, Any]:
    root = Path(active_match_dir).expanduser().resolve(strict=False)
    files = [p for p in sorted(root.iterdir() if root.exists() else []) if p.is_file() and p.suffix.casefold() in {".csv", ".tsv", ".xml"}]
    seen_sha: dict[str, Path] = {}
    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    raw_field_counts: Counter[str] = Counter()
    duplicate_file_reflections: list[dict[str, Any]] = []

    for path in files:
        digest = _file_sha(path)
        if digest in seen_sha:
            duplicate_file_reflections.append({"source_file": path.name, "reflected_from_file": seen_sha[digest].name, "sha256": digest})
            continue
        seen_sha[digest] = path
        role = _source_role(path)
        namespace = _source_namespace(path)
        for idx, raw in enumerate(_read_raw(path)):
            lowered = _lower_row(raw)
            raw_field_counts.update(lowered.keys())
            sem = _semantic_values(raw)
            provider_id = _norm_text(sem.get("provider_row_id"))
            provider_id_present = provider_id is not None
            if provider_id_present:
                identity_key = str(provider_id)
            else:
                identity_key = "__MISSING__:" + hashlib.sha256(f"{namespace}|{path.suffix.casefold()}|{idx}".encode()).hexdigest()[:20]
            rows_by_key[(namespace, identity_key)].append({
                "source_file": path.name,
                "source_namespace": namespace,
                "source_format": path.suffix.casefold().lstrip("."),
                "source_role": role,
                "source_row_index": idx,
                "source_sha256": digest,
                "provider_row_id_present": provider_id_present,
                "raw_fields": {str(k): v for k, v in raw.items()},
                "semantic_candidates": sem,
            })

    projections: list[dict[str, Any]] = []
    for (namespace, identity_key), surfaces in sorted(rows_by_key.items()):
        field_candidates: dict[str, list[str]] = {}
        resolved: dict[str, Any] = {}
        conflicts: list[str] = []
        for semantic_name in FIELD_ALIASES:
            values = sorted({_norm_text(item["semantic_candidates"].get(semantic_name)) for item in surfaces if _norm_text(item["semantic_candidates"].get(semantic_name)) is not None})
            field_candidates[semantic_name] = values
            if len(values) == 1:
                resolved[semantic_name] = values[0]
            else:
                resolved[semantic_name] = None
                if len(values) > 1:
                    conflicts.append(semantic_name)
        provider_id_present = all(bool(item.get("provider_row_id_present")) for item in surfaces)
        aggregation_eligible = provider_id_present
        provider_id = _norm_text(resolved.get("provider_row_id")) if provider_id_present else None
        projections.append({
            "rich_field_projection_id": hashlib.sha256(f"{namespace}|{identity_key}".encode()).hexdigest(),
            "source_namespace": namespace,
            "source_roles": sorted({str(item.get("source_role")) for item in surfaces}),
            "provider_row_id_candidate": provider_id,
            "provider_row_id_is_action_identity_truth": False,
            "identity_reconciliation_status": "PROVIDER_ID_NAMESPACE_SCOPED_CANDIDATE" if provider_id_present else "WITHHELD_PROVIDER_ID_MISSING",
            "aggregate_primitives_eligible": aggregation_eligible,
            "aggregate_primitives_withheld_reason": None if aggregation_eligible else "provider_id_missing_cross_format_identity_unreconciled",
            "semantic_field_candidates": field_candidates,
            "resolved_semantic_fields": resolved,
            "semantic_conflict_fields": conflicts,
            "surface_refs": surfaces,
            "raw_field_union": sorted({_norm_key(key) for item in surfaces for key in item["raw_fields"]}),
            "reflection_surface_count": len(surfaces),
            "independent_source_vote_allowed": False,
        })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "claim_safety": CLAIM_SAFETY,
        "projection_count": len(projections),
        "observed_raw_field_count": len(raw_field_counts),
        "observed_raw_fields": dict(raw_field_counts.most_common()),
        "duplicate_file_reflections": duplicate_file_reflections,
        "projections": projections,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def build_primitives(projection_report: dict[str, Any]) -> dict[str, Any]:
    geometry_rows: list[dict[str, Any]] = []
    pass_edges: Counter[tuple[str, str, str]] = Counter()
    player_directions: dict[str, Counter[str]] = defaultdict(Counter)
    team_directions: dict[str, Counter[str]] = defaultdict(Counter)
    zone_transitions: Counter[tuple[str, str]] = Counter()
    outcome_counts: Counter[str] = Counter()
    withheld_counts: Counter[str] = Counter()

    for item in projection_report.get("projections", []) or []:
        if not item.get("aggregate_primitives_eligible", False):
            withheld_counts["identity_unreconciled"] += 1
            continue

        resolved = item.get("resolved_semantic_fields") or {}
        action = _norm_text(resolved.get("action"))
        player = _norm_text(resolved.get("player"))
        team = _norm_text(resolved.get("team"))
        period = _norm_text(resolved.get("period"))
        receiver = _norm_text(resolved.get("receiver"))
        sx = _num(resolved.get("start_x"))
        sy = _num(resolved.get("start_y"))
        ex = _num(resolved.get("end_x"))
        ey = _num(resolved.get("end_y"))
        outcome = _outcome_candidate(resolved.get("outcome"))
        outcome_counts[outcome] += 1

        coord = _coordinate_context(resolved, item.get("source_namespace"))
        length = coord.get("pitch_length")
        width = coord.get("pitch_width")
        direction_scope_admitted = bool(
            _is_admitted_status(resolved.get("attacking_direction_admission_status"))
            and team
            and period
            and _norm_text(item.get("source_namespace"))
        )
        attack_sign = _attack_sign(resolved.get("attacking_direction")) if direction_scope_admitted else None
        coordinate_admitted = bool(coord.get("coordinate_system_admitted"))

        raw_dx = ex - sx if sx is not None and ex is not None else None
        raw_dy = ey - sy if sy is not None and ey is not None else None
        x_range_valid = bool(coordinate_admitted and _coord_in_range(sx, length) and _coord_in_range(ex, length))
        y_range_valid = bool(coordinate_admitted and _coord_in_range(sy, width) and _coord_in_range(ey, width))
        full_range_valid = x_range_valid and y_range_valid

        euclidean = math.hypot(raw_dx, raw_dy) if full_range_valid and raw_dx is not None and raw_dy is not None else None
        angle = math.degrees(math.atan2(raw_dy, raw_dx)) if full_range_valid and raw_dx is not None and raw_dy is not None else None
        forward_gain = attack_sign * raw_dx if x_range_valid and attack_sign is not None and raw_dx is not None else None
        direction = _direction(forward_gain, length) if forward_gain is not None else None
        origin_pitch = _pitch_zone(sx, sy, length, width) if full_range_valid else None
        destination_pitch = _pitch_zone(ex, ey, length, width) if full_range_valid else None
        origin_attacking = _attacking_zone(sx, sy, length, width, attack_sign) if full_range_valid else None
        destination_attacking = _attacking_zone(ex, ey, length, width, attack_sign) if full_range_valid else None
        third_skip = _geometric_third_skip(sx, ex, length, attack_sign) if x_range_valid else None

        if raw_dx is not None or raw_dy is not None:
            geometry_rows.append({
                "rich_field_projection_id": item.get("rich_field_projection_id"),
                "provider_row_id_candidate": item.get("provider_row_id_candidate"),
                "source_namespace": item.get("source_namespace"),
                "action_candidate": action,
                "team_candidate": team,
                "period_candidate": period,
                "player_candidate": player,
                "receiver_candidate": receiver,
                "start_x": sx,
                "start_y": sy,
                "end_x": ex,
                "end_y": ey,
                "raw_x_displacement": raw_dx,
                "raw_y_displacement": raw_dy,
                "coordinate_system_admitted": coordinate_admitted,
                "coordinate_system_basis": coord.get("coordinate_system_basis"),
                "pitch_length": length,
                "pitch_width": width,
                "coordinate_range_valid": full_range_valid,
                "attacking_direction_admitted": attack_sign is not None,
                "attacking_direction_basis": "EXPLICIT_TEAM_PERIOD_SOURCE_ADMISSION" if attack_sign is not None else "WITHHELD_NO_TEAM_PERIOD_SOURCE_DIRECTION_ADMISSION",
                "euclidean_displacement": euclidean,
                "forward_gain": forward_gain,
                "lateral_displacement_abs": abs(raw_dy) if full_range_valid and raw_dy is not None else None,
                "direction_angle_degrees": angle,
                "direction_candidate": direction,
                "origin_pitch_zone_candidate": origin_pitch,
                "destination_pitch_zone_candidate": destination_pitch,
                "origin_zone_candidate": origin_attacking,
                "destination_zone_candidate": destination_attacking,
                "geometric_third_skip_count": third_skip,
                "outcome_candidate": outcome,
                "physical_speed_truth": False,
                "defensive_line_bypass_truth": False,
                "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY",
            })

        if origin_attacking and destination_attacking:
            zone_transitions[(origin_attacking, destination_attacking)] += 1
        if player and direction:
            player_directions[player][direction] += 1
        if team and direction:
            team_directions[team][direction] += 1

        if action and "pass" in action.casefold() and player and receiver:
            pass_edges[(team or "UNKNOWN_TEAM", player, receiver)] += 1

        if not coordinate_admitted:
            withheld_counts["coordinate_system_not_admitted"] += 1
        elif not x_range_valid:
            withheld_counts["coordinate_x_range_invalid_or_missing"] += 1
        if attack_sign is None:
            withheld_counts["attacking_direction_not_admitted"] += 1

    pass_edge_rows = [
        {"team_candidate": team, "passer_candidate": passer, "receiver_candidate": receiver, "explicit_edge_count": count, "receiver_edge_basis": "EXPLICIT_RECEIVER_FIELD_ONLY", "formation_truth": False}
        for (team, passer, receiver), count in pass_edges.most_common()
    ]
    zone_rows = [
        {"origin_zone_candidate": origin, "destination_zone_candidate": destination, "transition_candidate_count": count, "zone_basis": "ATTACKING_DIRECTION_NORMALIZED_DECLARED_COORDINATE_SYSTEM", "pitch_control_truth": False}
        for (origin, destination), count in zone_transitions.most_common()
    ]
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "geometry_action_candidates": geometry_rows,
        "geometry_action_candidate_count": len(geometry_rows),
        "pass_network_edges": pass_edge_rows,
        "pass_network_edge_count": len(pass_edge_rows),
        "player_direction_profiles": {key: dict(value) for key, value in sorted(player_directions.items())},
        "team_direction_profiles": {key: dict(value) for key, value in sorted(team_directions.items())},
        "zone_transition_matrix_candidates": zone_rows,
        "outcome_candidate_counts": dict(outcome_counts),
        "withheld_primitive_counts": dict(withheld_counts),
        "metric_contracts": [
            {"metric_id": "raw_x_displacement_observation", "formula": "x_end-x_start", "unit": "provider_coordinate_unit", "claim_ceiling": "RAW_COORDINATE_DIFFERENCE_ONLY"},
            {"metric_id": "event_euclidean_displacement", "formula": "sqrt((x_end-x_start)^2+(y_end-y_start)^2)", "unit": "provider_coordinate_unit", "requires": ["start_x", "start_y", "end_x", "end_y", "coordinate_system"], "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "event_forward_gain", "formula": "attack_sign*(x_end-x_start)", "unit": "provider_coordinate_unit", "requires": ["start_x", "end_x", "coordinate_system", "attacking_direction_normalization"], "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "event_direction_angle", "formula": "atan2(y_end-y_start,x_end-x_start)", "unit": "degrees", "requires": ["start_x", "start_y", "end_x", "end_y", "coordinate_system"], "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "zone_transition_candidate", "formula": "count(origin_zone,destination_zone)", "unit": "candidate_count", "requires": ["coordinate_system", "attacking_direction_normalization", "reflection_identity"], "claim_ceiling": "ZONE_TRANSITION_CANDIDATE_ONLY"},
            {"metric_id": "explicit_passer_receiver_edge", "formula": "count(explicit passer, explicit receiver)", "unit": "candidate_count", "requires": ["explicit_receiver", "reflection_identity"], "claim_ceiling": "PASS_RELATION_CANDIDATE_ONLY"},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "pass_network_is_team_shape_truth": False,
        "geometric_skip_is_defensive_line_bypass_truth": False,
        "production_release": False,
    }


def run(active_match_dir: str | Path) -> dict[str, Any]:
    projection = build_projection(active_match_dir)
    primitives = build_primitives(projection)
    return {"projection": projection, "primitives": primitives}
