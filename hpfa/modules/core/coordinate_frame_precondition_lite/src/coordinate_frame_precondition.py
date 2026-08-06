from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

MODULE_ID = "coordinate_frame_precondition_lite_v1"
VERSION = "1.0.0"
CANONICAL_EVENT_COUNT = "UNKNOWN"
INPUT_MODULES = {
    "provider_labels": "provider_label_value_semantics_lite_v1",
    "action_bundles": "semantic_role_action_bundle_candidates_lite_v1",
    "selected_event": "selected_event_consequence_surface_lite_v1",
}
OUTPUTS = {
    "json": "coordinate_frame_precondition_lite_v1.json",
    "summary": "coordinate_frame_precondition_lite_v1.txt",
    "analyst": "coordinate_frame_precondition_analyst_audit_v1.txt",
}
EXACT_MAPPING_STATUSES = {
    "EXACT_REVIEWED_CANDIDATE",
    "EXACT_ALIAS_CANDIDATE",
}
RESOLVED_DIRECTIONS = {
    "ATTACK_TOWARD_HIGH_X_CANDIDATE",
    "ATTACK_TOWARD_LOW_X_CANDIDATE",
}
GOALKEEPER_ROLE = "GOALKEEPER_SURFACE_CANDIDATE"
NON_TEAM_ROLES = {"PLAYER_SURFACE_CANDIDATE", GOALKEEPER_ROLE}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def load_json(path: str | Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(code) from exc
    if not isinstance(payload, dict):
        raise ValueError(code)
    return payload


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _input_guard(name: str, payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != INPUT_MODULES[name]:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    status = clean(payload.get("module_status") or payload.get("status"))
    if status == "FAIL_CLOSED":
        blocks.append(f"{name}_fail_closed")
    elif status not in {"PASS", "SMOKE_PASS"}:
        reviews.append(f"{name}_status_review:{status or 'UNKNOWN'}")
    return blocks, reviews


def _records(
    payload: dict[str, Any], key: str, declared_key: str, code: str
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return [], [f"{code}_inventory_invalid"]
    blocks: list[str] = []
    if payload.get(declared_key) != len(rows):
        blocks.append(f"{code}_count_mismatch")
    if any(not isinstance(row, dict) for row in rows):
        blocks.append(f"{code}_record_invalid")
        rows = [row for row in rows if isinstance(row, dict)]
    return rows, blocks


def _goal_kick_label_index(provider_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for row in provider_rows:
        if clean(row.get("mapping_status")) not in EXACT_MAPPING_STATUSES:
            continue
        if clean(row.get("restart_type_candidate")).upper() != "GOAL_KICK":
            continue
        role = clean(row.get("source_role"))
        label = clean(row.get("normalized_label"))
        if role and label:
            index[role].add(label)
    return index


def _bundle_labels(bundle: dict[str, Any]) -> set[str]:
    values = bundle.get("normalized_labels")
    if not isinstance(values, list):
        return set()
    return {clean(value) for value in values if clean(value)}


def _group_x(
    bundles: list[dict[str, Any]],
    *,
    family: str,
    allowed_roles: set[str],
    exact_labels_by_role: dict[str, set[str]] | None = None,
) -> dict[tuple[str, str], list[float]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for bundle in bundles:
        role = clean(bundle.get("source_role"))
        if role not in allowed_roles:
            continue
        if clean(bundle.get("action_family_candidate")).upper() != family:
            continue
        if exact_labels_by_role is not None:
            allowed = exact_labels_by_role.get(role, set())
            if not allowed or not (_bundle_labels(bundle) & allowed):
                continue
        team = clean(bundle.get("team_identity_candidate_id"))
        period = clean(bundle.get("period_candidate"))
        x = number(bundle.get("pos_x_candidate"))
        if team and period and x is not None:
            grouped[(team, period)].append(x)
    return grouped


def _goal_side_direction(
    xs: list[float], length: float, minimum: int
) -> tuple[str, str, float | None]:
    if len(xs) < minimum:
        return (
            "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
            "INSUFFICIENT_ANCHOR_SUPPORT",
            None,
        )
    med = median(value / length for value in xs)
    if med <= 0.30:
        return (
            "ATTACK_TOWARD_HIGH_X_CANDIDATE",
            "PASS_GOAL_SIDE_COUNTER_ANCHOR_CANDIDATE",
            med,
        )
    if med >= 0.70:
        return (
            "ATTACK_TOWARD_LOW_X_CANDIDATE",
            "PASS_GOAL_SIDE_COUNTER_ANCHOR_CANDIDATE",
            med,
        )
    return (
        "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
        "ANCHOR_DISTRIBUTION_AMBIGUOUS_REVIEW_REQUIRED",
        med,
    )


def _clearance_direction(xs: list[float], length: float) -> tuple[str, str, float | None]:
    if len(xs) < 3:
        return (
            "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
            "INSUFFICIENT_CLEARANCE_COUNTER_SUPPORT",
            None,
        )
    med = median(value / length for value in xs)
    if med <= 0.45:
        return (
            "ATTACK_TOWARD_HIGH_X_CANDIDATE",
            "CLEARANCE_COUNTER_SUPPORT_CANDIDATE",
            med,
        )
    if med >= 0.55:
        return (
            "ATTACK_TOWARD_LOW_X_CANDIDATE",
            "CLEARANCE_COUNTER_SUPPORT_CANDIDATE",
            med,
        )
    return (
        "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
        "CLEARANCE_DISTRIBUTION_AMBIGUOUS_REVIEW_REQUIRED",
        med,
    )


def _shot_index(
    frame: dict[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    rows = frame.get("team_period_attack_direction_candidates")
    blocks: list[str] = []
    if not isinstance(rows, list):
        return {}, ["shot_direction_inventory_invalid"]
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"shot_direction_record_invalid:{position}")
            continue
        key = (
            clean(row.get("team_identity_candidate_id")),
            clean(row.get("period_candidate")),
        )
        if not all(key) or key in index:
            blocks.append(f"shot_direction_group_invalid_or_duplicate:{position}")
            continue
        index[key] = row
    return index, blocks


def build_coordinate_frame_precondition(
    provider_labels: dict[str, Any],
    action_bundles: dict[str, Any],
    selected_event: dict[str, Any],
) -> dict[str, Any]:
    payloads = {
        "provider_labels": provider_labels,
        "action_bundles": action_bundles,
        "selected_event": selected_event,
    }
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload in payloads.items():
        found_blocks, found_reviews = _input_guard(name, payload)
        blocks.extend(found_blocks)
        reviews.extend(found_reviews)

    provider_rows, found = _records(
        provider_labels,
        "provider_label_records",
        "provider_label_record_count",
        "provider_label",
    )
    blocks.extend(found)
    bundle_rows, found = _records(
        action_bundles,
        "action_bundle_candidates",
        "action_bundle_candidate_count",
        "action_bundle",
    )
    blocks.extend(found)

    bindings = {
        clean(action_bundles.get("match_surface_binding_id")),
        clean(selected_event.get("match_surface_binding_id")),
    }
    bindings.discard("")
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch_or_missing")
    binding = next(iter(bindings), "")

    frame = selected_event.get("coordinate_frame_candidate")
    if not isinstance(frame, dict):
        frame = {}
        blocks.append("coordinate_frame_candidate_invalid")
    shot_by_group, shot_blocks = _shot_index(frame)
    blocks.extend(shot_blocks)

    goal_labels = _goal_kick_label_index(provider_rows)
    if not goal_labels.get(GOALKEEPER_ROLE):
        reviews.append("goalkeeper_goal_kick_exact_label_lineage_unavailable")

    goal_kick_x = _group_x(
        bundle_rows,
        family="RESTART",
        allowed_roles={GOALKEEPER_ROLE},
        exact_labels_by_role=goal_labels,
    )
    clearance_x = _group_x(
        bundle_rows,
        family="CLEARANCE",
        allowed_roles=NON_TEAM_ROLES,
    )

    length = number(frame.get("pitch_length_candidate"))
    scale_gate = (
        clean(frame.get("coordinate_scale_candidate"))
        == "PROVIDER_105X68_SCALE_CANDIDATE"
        and clean(frame.get("coordinate_bounds_status"))
        == "PASS_CANDIDATE_BOUNDS"
        and length == 105.0
    )
    if not scale_gate:
        reviews.append("coordinate_scale_or_bounds_precondition_not_met")

    expected_groups = sorted(shot_by_group)
    if not expected_groups:
        reviews.append("shot_anchor_groups_unavailable")

    group_records: list[dict[str, Any]] = []
    primary_pass_count = 0
    conflict_count = 0
    clearance_agreement_count = 0
    for team, period in expected_groups:
        shot = shot_by_group[(team, period)]
        shot_direction = clean(shot.get("attack_direction_candidate"))
        shot_support = clean(shot.get("attack_direction_support_status"))
        shot_count = int(shot.get("shot_support_node_count") or 0)
        if (
            shot_support != "PASS_SHOT_CONCENTRATION_CANDIDATE"
            or shot_direction not in RESOLVED_DIRECTIONS
        ):
            shot_direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"

        goal_direction, goal_support, goal_median = (
            _goal_side_direction(goal_kick_x.get((team, period), []), length, 2)
            if length
            else (
                "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
                "SCALE_REQUIRED",
                None,
            )
        )
        clearance_direction, clearance_support, clearance_median = (
            _clearance_direction(clearance_x.get((team, period), []), length)
            if length
            else (
                "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
                "SCALE_REQUIRED",
                None,
            )
        )

        primary_directions = [
            direction
            for direction in (shot_direction, goal_direction)
            if direction in RESOLVED_DIRECTIONS
        ]
        if len(primary_directions) == 2 and len(set(primary_directions)) == 1:
            gate = "PASS_MULTI_ANCHOR_CANDIDATE"
            direction = primary_directions[0]
            primary_pass_count += 1
        elif len(primary_directions) == 2:
            gate = "CONFLICTING_PRIMARY_ANCHORS_REVIEW_REQUIRED"
            direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"
            conflict_count += 1
        else:
            gate = "INDEPENDENT_PRIMARY_ANCHORS_INSUFFICIENT"
            direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"

        if (
            direction in RESOLVED_DIRECTIONS
            and clearance_direction in RESOLVED_DIRECTIONS
        ):
            clearance_relation = (
                "AGREES_WITH_PRIMARY_DIRECTION"
                if clearance_direction == direction
                else "CONFLICTS_WITH_PRIMARY_DIRECTION_REVIEW_REQUIRED"
            )
            if clearance_direction == direction:
                clearance_agreement_count += 1
            else:
                reviews.append(
                    f"clearance_counter_support_conflict:{team}:{period}"
                )
        else:
            clearance_relation = "COUNTER_SUPPORT_UNAVAILABLE_OR_AMBIGUOUS"

        confidence = (
            "MEDIUM_WITH_CLEARANCE_COUNTER_SUPPORT"
            if gate == "PASS_MULTI_ANCHOR_CANDIDATE"
            and clearance_relation == "AGREES_WITH_PRIMARY_DIRECTION"
            else "MEDIUM_PRIMARY_ANCHOR_AGREEMENT"
            if gate == "PASS_MULTI_ANCHOR_CANDIDATE"
            else "LOW"
        )
        group_records.append(
            {
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "shot_support_node_count": shot_count,
                "shot_direction_candidate": shot_direction,
                "shot_support_status": shot_support or None,
                "goalkeeper_goal_kick_anchor_count": len(
                    goal_kick_x.get((team, period), [])
                ),
                "goalkeeper_goal_kick_normalized_x_median": (
                    None if goal_median is None else round(goal_median, 6)
                ),
                "goalkeeper_goal_kick_direction_candidate": goal_direction,
                "goalkeeper_goal_kick_support_status": goal_support,
                "clearance_counter_anchor_count": len(
                    clearance_x.get((team, period), [])
                ),
                "clearance_normalized_x_median": (
                    None if clearance_median is None else round(clearance_median, 6)
                ),
                "clearance_direction_candidate": clearance_direction,
                "clearance_support_status": clearance_support,
                "clearance_relation_to_primary": clearance_relation,
                "multi_anchor_gate": gate,
                "attack_direction_candidate": direction,
                "coordinate_frame_confidence_tier": confidence,
                "attack_direction_is_validated_truth": False,
            }
        )

    all_expected_groups_pass = (
        bool(expected_groups) and primary_pass_count == len(expected_groups)
    )
    progression_metric_recheck_allowed = bool(
        not blocks and scale_gate and all_expected_groups_pass and conflict_count == 0
    )
    resolved_directions = {
        row["attack_direction_candidate"]
        for row in group_records
        if row["attack_direction_candidate"] in RESOLVED_DIRECTIONS
    }
    if (
        progression_metric_recheck_allowed
        and resolved_directions == {"ATTACK_TOWARD_HIGH_X_CANDIDATE"}
    ):
        frame_candidate = "TEAM_ATTACK_NORMALIZED_POSITIVE_X_CANDIDATE"
    elif progression_metric_recheck_allowed:
        frame_candidate = "TEAM_PERIOD_DIRECTION_MAP_CANDIDATE"
    else:
        frame_candidate = "FRAME_UNRESOLVED"

    if not all_expected_groups_pass:
        reviews.append(
            "independent_direction_anchor_families_insufficient_or_conflicted"
        )
    decision = (
        "PASS_COORDINATE_FRAME_PRECONDITION_CANDIDATE"
        if progression_metric_recheck_allowed
        else "REVIEW_REQUIRED_COORDINATE_FRAME_PRECONDITION"
    )

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    anchor_families = ["SHOT_CONCENTRATION", "GOALKEEPER_GOAL_KICK_START"]
    if clearance_x:
        anchor_families.append("CLEARANCE_COUNTER_SUPPORT")

    return {
        "module_id": MODULE_ID,
        "version": VERSION,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "decision": decision,
        "match_surface_binding_id": binding or None,
        "source_module_ids": dict(INPUT_MODULES),
        "coordinate_scale_candidate": frame.get("coordinate_scale_candidate"),
        "coordinate_bounds_status": frame.get("coordinate_bounds_status"),
        "pitch_length_candidate": frame.get("pitch_length_candidate"),
        "pitch_width_candidate": frame.get("pitch_width_candidate"),
        "coordinate_frame_candidate": frame_candidate,
        "direction_anchor_families": anchor_families,
        "expected_team_period_group_count": len(expected_groups),
        "multi_anchor_pass_group_count": primary_pass_count,
        "multi_anchor_conflict_group_count": conflict_count,
        "clearance_counter_support_agreement_group_count": (
            clearance_agreement_count
        ),
        "team_period_coordinate_frame_candidates": group_records,
        "goalkeeper_goal_kick_anchor_count": sum(
            len(values) for values in goal_kick_x.values()
        ),
        "clearance_counter_anchor_count": sum(
            len(values) for values in clearance_x.values()
        ),
        "progression_metric_recheck_allowed": progression_metric_recheck_allowed,
        "blocked_metric_recheck_allowed": progression_metric_recheck_allowed,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "clearance_is_primary_direction_anchor": False,
        "coordinate_frame_is_validated_provider_truth": False,
        "attack_direction_is_validated_truth": False,
        "progression_truth": False,
        "line_break_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "decision",
        "coordinate_scale_candidate",
        "coordinate_bounds_status",
        "coordinate_frame_candidate",
        "direction_anchor_families",
        "expected_team_period_group_count",
        "multi_anchor_pass_group_count",
        "multi_anchor_conflict_group_count",
        "goalkeeper_goal_kick_anchor_count",
        "clearance_counter_anchor_count",
        "progression_metric_recheck_allowed",
        "hard_block_hits",
        "review_hits",
    )
    return "\n".join(
        ["HPFA COORDINATE FRAME PRECONDITION LITE V1"]
        + [f"{key}={payload.get(key)}" for key in keys]
        + ["canonical_event_count=UNKNOWN", "production_release=false", ""]
    )


def analyst_audit(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — COORDINATE FRAME PRECONDITION LITE V1",
        f"Scale candidate: {payload.get('coordinate_scale_candidate')}",
        f"Bounds status: {payload.get('coordinate_bounds_status')}",
        f"Frame candidate: {payload.get('coordinate_frame_candidate')}",
        f"Goalkeeper goal-kick anchors: {payload.get('goalkeeper_goal_kick_anchor_count', 0)}",
        f"Clearance counter-support anchors: {payload.get('clearance_counter_anchor_count', 0)}",
        f"Team-period multi-anchor pass groups: {payload.get('multi_anchor_pass_group_count', 0)}/{payload.get('expected_team_period_group_count', 0)}",
        f"Progression metric recheck allowed: {payload.get('progression_metric_recheck_allowed')}",
        "Analyst-safe meaning: visible shot concentration and exact goalkeeper goal-kick start surfaces are compared as independent direction-anchor candidates. Clearance is support-only.",
        "This output is not provider-frame truth, attack-direction truth, progression truth, possession truth or tactical truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-labels", required=True)
    parser.add_argument("--action-bundles", required=True)
    parser.add_argument("--selected-event", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_coordinate_frame_precondition(
        load_json(
            args.provider_labels,
            "provider_label_input_unreadable_or_malformed",
        ),
        load_json(
            args.action_bundles,
            "action_bundle_input_unreadable_or_malformed",
        ),
        load_json(
            args.selected_event,
            "selected_event_input_unreadable_or_malformed",
        ),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "decision",
                    "coordinate_frame_candidate",
                    "multi_anchor_pass_group_count",
                    "multi_anchor_conflict_group_count",
                    "progression_metric_recheck_allowed",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
