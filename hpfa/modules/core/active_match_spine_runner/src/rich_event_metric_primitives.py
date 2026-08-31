from __future__ import annotations

import csv
import hashlib
import json
import math
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


def _zone(x: float | None, y: float | None) -> str | None:
    if x is None or y is None:
        return None
    third = "DEFENSIVE_THIRD" if x < 35 else "MIDDLE_THIRD" if x < 70 else "FINAL_THIRD"
    channel = "LEFT" if y < 22.67 else "CENTRAL" if y < 45.34 else "RIGHT"
    return f"{third}:{channel}"


def _direction(dx: float | None, dy: float | None) -> str | None:
    if dx is None or dy is None:
        return None
    if abs(dx) < 1.0:
        return "LATERAL_CANDIDATE"
    return "FORWARD_CANDIDATE" if dx > 0 else "BACKWARD_CANDIDATE"


def _third_index(x: float | None) -> int | None:
    if x is None:
        return None
    return 0 if x < 35 else 1 if x < 70 else 2


def _geometric_third_skip(start_x: float | None, end_x: float | None) -> int | None:
    a = _third_index(start_x)
    b = _third_index(end_x)
    if a is None or b is None:
        return None
    return max(0, abs(b - a) - 1)


def build_projection(active_match_dir: str | Path) -> dict[str, Any]:
    root = Path(active_match_dir).expanduser().resolve(strict=False)
    files = [p for p in sorted(root.iterdir() if root.exists() else []) if p.is_file() and p.suffix.casefold() in {".csv", ".tsv", ".xml"}]
    seen_sha: dict[tuple[str, str], Path] = {}
    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    raw_field_counts: Counter[str] = Counter()
    duplicate_file_reflections: list[dict[str, Any]] = []

    for path in files:
        digest = _file_sha(path)
        key_sha = (path.suffix.casefold(), digest)
        if key_sha in seen_sha:
            duplicate_file_reflections.append({"source_file": path.name, "reflected_from_file": seen_sha[key_sha].name, "sha256": digest})
            continue
        seen_sha[key_sha] = path
        role = _source_role(path)
        for idx, raw in enumerate(_read_raw(path)):
            lowered = _lower_row(raw)
            raw_field_counts.update(lowered.keys())
            sem = _semantic_values(raw)
            provider_id = _norm_text(sem.get("provider_row_id"))
            if not provider_id:
                provider_id = "__MISSING__:" + hashlib.sha256(f"{role}|{path.name}|{idx}".encode()).hexdigest()[:20]
            rows_by_key[(role, provider_id)].append({
                "source_file": path.name,
                "source_format": path.suffix.casefold().lstrip("."),
                "source_role": role,
                "source_row_index": idx,
                "source_sha256": digest,
                "raw_fields": {str(k): v for k, v in raw.items()},
                "semantic_candidates": sem,
            })

    projections: list[dict[str, Any]] = []
    for (role, provider_id), surfaces in sorted(rows_by_key.items()):
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
        projections.append({
            "rich_field_projection_id": hashlib.sha256(f"{role}|{provider_id}".encode()).hexdigest(),
            "source_role": role,
            "provider_row_id_candidate": provider_id,
            "provider_row_id_is_action_identity_truth": False,
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

    for item in projection_report.get("projections", []) or []:
        resolved = item.get("resolved_semantic_fields") or {}
        action = _norm_text(resolved.get("action"))
        player = _norm_text(resolved.get("player"))
        team = _norm_text(resolved.get("team"))
        receiver = _norm_text(resolved.get("receiver"))
        sx = _num(resolved.get("start_x"))
        sy = _num(resolved.get("start_y"))
        ex = _num(resolved.get("end_x"))
        ey = _num(resolved.get("end_y"))
        outcome = _outcome_candidate(resolved.get("outcome"))
        outcome_counts[outcome] += 1

        if None not in (sx, sy, ex, ey):
            dx = ex - sx  # type: ignore[operator]
            dy = ey - sy  # type: ignore[operator]
            distance = math.hypot(dx, dy)
            angle = math.degrees(math.atan2(dy, dx))
            origin = _zone(sx, sy)
            destination = _zone(ex, ey)
            direction = _direction(dx, dy)
            geometry_rows.append({
                "rich_field_projection_id": item.get("rich_field_projection_id"),
                "provider_row_id_candidate": item.get("provider_row_id_candidate"),
                "source_role": item.get("source_role"),
                "action_candidate": action,
                "team_candidate": team,
                "player_candidate": player,
                "receiver_candidate": receiver,
                "start_x": sx,
                "start_y": sy,
                "end_x": ex,
                "end_y": ey,
                "euclidean_displacement": distance,
                "forward_gain": dx,
                "lateral_displacement_abs": abs(dy),
                "direction_angle_degrees": angle,
                "direction_candidate": direction,
                "origin_zone_candidate": origin,
                "destination_zone_candidate": destination,
                "geometric_third_skip_count": _geometric_third_skip(sx, ex),
                "outcome_candidate": outcome,
                "physical_speed_truth": False,
                "defensive_line_bypass_truth": False,
                "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY",
            })
            if origin and destination:
                zone_transitions[(origin, destination)] += 1
            if player and direction:
                player_directions[player][direction] += 1
            if team and direction:
                team_directions[team][direction] += 1

        if action and "pass" in action.casefold() and player and receiver:
            pass_edges[(team or "UNKNOWN_TEAM", player, receiver)] += 1

    pass_edge_rows = [
        {"team_candidate": team, "passer_candidate": passer, "receiver_candidate": receiver, "explicit_edge_count": count, "receiver_edge_basis": "EXPLICIT_RECEIVER_FIELD_ONLY", "formation_truth": False}
        for (team, passer, receiver), count in pass_edges.most_common()
    ]
    zone_rows = [
        {"origin_zone_candidate": origin, "destination_zone_candidate": destination, "transition_candidate_count": count, "pitch_control_truth": False}
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
        "metric_contracts": [
            {"metric_id": "event_euclidean_displacement", "formula": "sqrt((x_end-x_start)^2+(y_end-y_start)^2)", "unit": "provider_coordinate_unit", "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "event_forward_gain", "formula": "x_end-x_start", "unit": "provider_coordinate_unit", "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "event_direction_angle", "formula": "atan2(y_end-y_start,x_end-x_start)", "unit": "degrees", "claim_ceiling": "EVENT_GEOMETRY_CANDIDATE_ONLY"},
            {"metric_id": "zone_transition_candidate", "formula": "count(origin_zone,destination_zone)", "unit": "candidate_count", "claim_ceiling": "ZONE_TRANSITION_CANDIDATE_ONLY"},
            {"metric_id": "explicit_passer_receiver_edge", "formula": "count(explicit passer, explicit receiver)", "unit": "candidate_count", "claim_ceiling": "PASS_RELATION_CANDIDATE_ONLY"},
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
