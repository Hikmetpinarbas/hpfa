from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

MODULE_ID = "coordinate_anchor_family_discovery_v1"
VERSION = "1.0.0"
CANONICAL_EVENT_COUNT = "UNKNOWN"
GK_ROLE = "GOALKEEPER_SURFACE_CANDIDATE"
PLAYER_ROLE = "PLAYER_SURFACE_CANDIDATE"
TEAM_ROLE = "TEAM_SURFACE_CANDIDATE"
EXACT_MAPPING_STATUSES = {"EXACT_REVIEWED_CANDIDATE", "EXACT_ALIAS_CANDIDATE"}
RESOLVED_DIRECTIONS = {
    "ATTACK_TOWARD_HIGH_X_CANDIDATE",
    "ATTACK_TOWARD_LOW_X_CANDIDATE",
}
OUTPUTS = {
    "json": "coordinate_anchor_family_discovery_v1.json",
    "summary": "coordinate_anchor_family_discovery_v1.txt",
    "analyst": "coordinate_anchor_family_discovery_analyst_audit_v1.txt",
}

CANDIDATE_SPECS = {
    "GK_SAVE": {
        "action_family": "GOALKEEPER_ACTION",
        "outcome": "SUCCESS",
        "shot_result": "SAVED",
        "action_subtype": "SAVE",
        "object_action_family": "SHOT",
        "reflection_families": {"SHOT"},
    },
    "GK_CROSS_PASS_INTERCEPTION_SUCCESS": {
        "action_family": "INTERCEPTION",
        "outcome": "SUCCESS",
        "action_subtype": "CROSS_OR_PASS_INTERCEPTION",
        "object_action_family": "PASS_OR_CROSS",
        "reflection_families": {"PASS", "CROSS"},
    },
    "GK_CROSS_PASS_INTERCEPTION_FAILURE": {
        "action_family": "INTERCEPTION",
        "outcome": "FAILURE",
        "action_subtype": "CROSS_OR_PASS_INTERCEPTION",
        "object_action_family": "PASS_OR_CROSS",
        "reflection_families": {"PASS", "CROSS"},
    },
}


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


def _input_guard(name: str, payload: dict[str, Any], expected_module: str) -> list[str]:
    blocks: list[str] = []
    if payload.get("module_id") != expected_module:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    return blocks


def _labels_for_spec(provider_rows: list[dict[str, Any]], spec: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in provider_rows:
        if clean(row.get("mapping_status")) not in EXACT_MAPPING_STATUSES:
            continue
        if clean(row.get("source_role")) != GK_ROLE:
            continue
        if clean(row.get("downstream_eligibility")) != "ACTION_CANDIDATE_ELIGIBLE":
            continue
        if clean(row.get("action_family_candidate")).upper() != spec["action_family"]:
            continue
        if clean(row.get("outcome_candidate")).upper() != spec["outcome"]:
            continue
        if clean(row.get("action_subtype_candidate")).upper() != spec["action_subtype"]:
            continue
        if clean(row.get("object_action_family_candidate")).upper() != spec["object_action_family"]:
            continue
        required_shot_result = spec.get("shot_result")
        if required_shot_result and clean(row.get("shot_result_candidate")).upper() != required_shot_result:
            continue
        label = clean(row.get("normalized_label"))
        if label:
            labels.add(label)
    return labels


def _team_period_key(row: dict[str, Any]) -> tuple[str, str]:
    return clean(row.get("team_identity_candidate_id")), clean(row.get("period_candidate"))


def _surface_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    x = number(row.get("pos_x_candidate"))
    y = number(row.get("pos_y_candidate"))
    return (
        clean(row.get("period_candidate")),
        clean(row.get("start_candidate")),
        clean(row.get("end_candidate")),
        "" if x is None else f"{x:.6f}",
        "" if y is None else f"{y:.6f}",
    )


def _goal_side_direction(xs: list[float], pitch_length: float, minimum: int = 2) -> tuple[str, float | None]:
    if len(xs) < minimum:
        return "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED", None
    med = median(value / pitch_length for value in xs)
    if med <= 0.30:
        return "ATTACK_TOWARD_HIGH_X_CANDIDATE", med
    if med >= 0.70:
        return "ATTACK_TOWARD_LOW_X_CANDIDATE", med
    return "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED", med


def _direction_relation(candidate: str, reference: str, label: str) -> str:
    if candidate in RESOLVED_DIRECTIONS and reference in RESOLVED_DIRECTIONS:
        return f"AGREES_WITH_{label}" if candidate == reference else f"CONFLICTS_WITH_{label}_REVIEW_REQUIRED"
    return f"{label}_RELATION_UNRESOLVED"


def _bundle_labels(bundle: dict[str, Any]) -> set[str]:
    values = bundle.get("normalized_labels")
    if not isinstance(values, list):
        return set()
    return {clean(item) for item in values if clean(item)}


def build_discovery(
    provider_labels: dict[str, Any],
    action_bundles: dict[str, Any],
    coordinate_frame: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    blocks.extend(_input_guard("provider_labels", provider_labels, "provider_label_value_semantics_lite_v1"))
    blocks.extend(_input_guard("action_bundles", action_bundles, "semantic_role_action_bundle_candidates_lite_v1"))
    blocks.extend(_input_guard("coordinate_frame", coordinate_frame, "coordinate_frame_precondition_lite_v1"))

    binding_a = clean(action_bundles.get("match_surface_binding_id"))
    binding_b = clean(coordinate_frame.get("match_surface_binding_id"))
    if not binding_a or binding_a != binding_b:
        blocks.append("match_surface_binding_mismatch_or_missing")

    provider_rows = provider_labels.get("provider_label_records")
    bundles = action_bundles.get("action_bundle_candidates")
    frame_rows = coordinate_frame.get("team_period_coordinate_frame_candidates")
    if not isinstance(provider_rows, list):
        provider_rows = []
        blocks.append("provider_label_records_invalid")
    if provider_labels.get("provider_label_record_count") != len(provider_rows):
        blocks.append("provider_label_record_count_mismatch")
    if not isinstance(bundles, list):
        bundles = []
        blocks.append("action_bundle_candidates_invalid")
    if action_bundles.get("action_bundle_candidate_count") != len(bundles):
        blocks.append("action_bundle_candidate_count_mismatch")
    if not isinstance(frame_rows, list):
        frame_rows = []
        blocks.append("coordinate_frame_group_inventory_invalid")

    pitch_length = number(coordinate_frame.get("pitch_length_candidate"))
    if pitch_length is None or pitch_length <= 0:
        blocks.append("pitch_length_candidate_invalid")

    frame_by_group: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(frame_rows):
        if not isinstance(row, dict):
            blocks.append(f"coordinate_frame_group_invalid:{index}")
            continue
        key = _team_period_key(row)
        if not all(key) or key in frame_by_group:
            blocks.append(f"coordinate_frame_group_key_invalid_or_duplicate:{index}")
            continue
        frame_by_group[key] = row

    reflection_surfaces: dict[str, set[tuple[str, str, str, str, str]]] = defaultdict(set)
    for bundle in bundles:
        if not isinstance(bundle, dict):
            continue
        if clean(bundle.get("bundle_status")) != "PASS":
            continue
        role = clean(bundle.get("source_role"))
        if role not in {PLAYER_ROLE, TEAM_ROLE}:
            continue
        family = clean(bundle.get("action_family_candidate")).upper()
        reflection_surfaces[family].add(_surface_key(bundle))

    family_records: list[dict[str, Any]] = []
    unresolved_groups = {
        key
        for key, row in frame_by_group.items()
        if clean(row.get("multi_anchor_gate")) != "PASS_MULTI_ANCHOR_CANDIDATE"
    }

    for family_id, spec in CANDIDATE_SPECS.items():
        labels = _labels_for_spec(provider_rows, spec)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        exact_reflection_surfaces = set().union(*(reflection_surfaces[f] for f in spec["reflection_families"]))
        for bundle in bundles:
            if not isinstance(bundle, dict):
                continue
            if clean(bundle.get("bundle_status")) != "PASS":
                continue
            if clean(bundle.get("source_role")) != GK_ROLE:
                continue
            if clean(bundle.get("action_family_candidate")).upper() != spec["action_family"]:
                continue
            if not (_bundle_labels(bundle) & labels):
                continue
            grouped[_team_period_key(bundle)].append(bundle)

        group_records: list[dict[str, Any]] = []
        covered_unresolved = 0
        exact_reflection_overlap_total = 0
        directional_conflicts = 0
        for key, frame_row in sorted(frame_by_group.items()):
            visible = grouped.get(key, [])
            xs = [number(row.get("pos_x_candidate")) for row in visible]
            xs = [value for value in xs if value is not None]
            direction, normalized_median = (
                _goal_side_direction(xs, pitch_length, 2)
                if pitch_length is not None
                else ("UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED", None)
            )
            overlaps = sum(1 for row in visible if _surface_key(row) in exact_reflection_surfaces)
            exact_reflection_overlap_total += overlaps
            independence_status = (
                "EXACT_OBJECT_ACTION_SURFACE_OVERLAP_REVIEW_REQUIRED"
                if overlaps
                else "NO_EXACT_OBJECT_ACTION_SURFACE_OVERLAP_OBSERVED_CANDIDATE"
                if visible
                else "NO_VISIBLE_CANDIDATE_SURFACE"
            )
            shot_relation = _direction_relation(
                direction,
                clean(frame_row.get("shot_direction_candidate")),
                "SHOT_DIRECTION",
            )
            goal_kick_relation = _direction_relation(
                direction,
                clean(frame_row.get("goalkeeper_goal_kick_direction_candidate")),
                "GOAL_KICK_DIRECTION",
            )
            clearance_relation = _direction_relation(
                direction,
                clean(frame_row.get("clearance_direction_candidate")),
                "CLEARANCE_DIRECTION",
            )
            if shot_relation.startswith("CONFLICTS_WITH_"):
                directional_conflicts += 1
            unresolved_target = key in unresolved_groups
            if unresolved_target and visible:
                covered_unresolved += 1

            coordinate_attachment = "UNVERIFIED_PROVIDER_COORDINATE_ATTACHMENT"
            if not labels or not visible:
                recommended = "REJECT"
            elif overlaps or shot_relation.startswith("CONFLICTS_WITH_"):
                recommended = "REJECT"
            else:
                recommended = "COUNTER_SUPPORT_ONLY"

            group_records.append(
                {
                    "team_identity_candidate_id": key[0],
                    "period_candidate": key[1],
                    "current_multi_anchor_gate": frame_row.get("multi_anchor_gate"),
                    "current_group_unresolved": unresolved_target,
                    "visible_anchor_count": len(visible),
                    "coordinate_eligible_anchor_count": len(xs),
                    "normalized_x_median": None if normalized_median is None else round(normalized_median, 6),
                    "goal_side_direction_candidate": direction,
                    "shot_relation": shot_relation,
                    "goal_kick_relation": goal_kick_relation,
                    "clearance_relation": clearance_relation,
                    "exact_object_action_surface_overlap_count": overlaps,
                    "lineage_independence_status": independence_status,
                    "coordinate_attachment_semantics_status": coordinate_attachment,
                    "recommended_role": recommended,
                    "primary_anchor_admission_allowed": False,
                }
            )

        family_records.append(
            {
                "anchor_family": family_id,
                "source_role": GK_ROLE,
                "exact_semantic_lineage_status": "EXACT_REVIEWED_CANDIDATE" if labels else "EXACT_SEMANTIC_LINEAGE_UNAVAILABLE",
                "exact_normalized_labels": sorted(labels),
                "directional_semantics_status": "EMPIRICAL_GOAL_SIDE_DISTRIBUTION_CANDIDATE_ONLY",
                "coordinate_attachment_semantics_status": "UNVERIFIED_PROVIDER_COORDINATE_ATTACHMENT",
                "independence_status": (
                    "EXACT_OBJECT_ACTION_SURFACE_OVERLAP_REVIEW_REQUIRED"
                    if exact_reflection_overlap_total
                    else "NO_EXACT_OBJECT_ACTION_SURFACE_OVERLAP_OBSERVED_CANDIDATE"
                ),
                "team_period_visible_support": sum(len(values) for values in grouped.values()),
                "coverage_count": sum(1 for values in grouped.values() if values),
                "unresolved_group_coverage_count": covered_unresolved,
                "exact_object_action_surface_overlap_count": exact_reflection_overlap_total,
                "directional_conflict_count": directional_conflicts,
                "recommended_role": (
                    "REJECT"
                    if not labels or exact_reflection_overlap_total or directional_conflicts
                    else "COUNTER_SUPPORT_ONLY"
                ),
                "primary_anchor_admission_allowed": False,
                "claim_boundary": "DISCOVERY_ONLY_NOT_DIRECTION_TRUTH",
                "team_period_records": group_records,
            }
        )

    status = "FAIL_CLOSED" if blocks else "DISCOVERY_PASS_PLAN_ONLY"
    return {
        "module_id": MODULE_ID,
        "version": VERSION,
        "status": status,
        "module_status": status,
        "match_surface_binding_id": binding_a or None,
        "source_module_ids": {
            "provider_labels": "provider_label_value_semantics_lite_v1",
            "action_bundles": "semantic_role_action_bundle_candidates_lite_v1",
            "coordinate_frame": "coordinate_frame_precondition_lite_v1",
        },
        "current_coordinate_frame_candidate": coordinate_frame.get("coordinate_frame_candidate"),
        "current_progression_metric_recheck_allowed": bool(coordinate_frame.get("progression_metric_recheck_allowed")),
        "expected_team_period_group_count": len(frame_by_group),
        "current_unresolved_team_period_group_count": len(unresolved_groups),
        "anchor_family_record_count": len(family_records),
        "anchor_family_records": family_records,
        "coordinate_frame_contract_change_allowed": False,
        "threshold_relaxation_allowed": False,
        "attack_direction_is_validated_truth": False,
        "coordinate_frame_is_validated_provider_truth": False,
        "progression_truth": False,
        "line_break_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "hard_block_hits": sorted(set(blocks)),
    }


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        "HPFA COORDINATE ANCHOR FAMILY DISCOVERY V1",
        f"status={result['status']}",
        f"expected_team_period_group_count={result['expected_team_period_group_count']}",
        f"current_unresolved_team_period_group_count={result['current_unresolved_team_period_group_count']}",
    ]
    for family in result.get("anchor_family_records", []):
        lines.append(
            f"{family['anchor_family']}: visible={family['team_period_visible_support']} "
            f"unresolved_coverage={family['unresolved_group_coverage_count']} "
            f"reflection_overlap={family['exact_object_action_surface_overlap_count']} "
            f"conflicts={family['directional_conflict_count']} role={family['recommended_role']}"
        )
    lines.extend(
        [
            "coordinate_frame_contract_change_allowed=false",
            "threshold_relaxation_allowed=false",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]
    )
    return "\n".join(lines) + "\n"


def render_analyst(result: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — COORDINATE ANCHOR FAMILY DISCOVERY",
        f"Current unresolved team-period groups: {result['current_unresolved_team_period_group_count']}",
    ]
    for family in result.get("anchor_family_records", []):
        lines.append(
            f"{family['anchor_family']}: visible support {family['team_period_visible_support']}; "
            f"unresolved-group coverage {family['unresolved_group_coverage_count']}; "
            f"exact reflection overlap {family['exact_object_action_surface_overlap_count']}; "
            f"safe role {family['recommended_role']}."
        )
    lines.extend(
        [
            "Observed goalkeeper coordinates are not promoted to goalkeeper-position truth because provider coordinate attachment semantics remain unverified.",
            "No candidate opens progression or changes the current coordinate-frame contract at this discovery layer.",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-labels", required=True)
    parser.add_argument("--action-bundles", required=True)
    parser.add_argument("--coordinate-frame", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = validate_out(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = build_discovery(
        load_json(args.provider_labels, "provider_labels_unreadable"),
        load_json(args.action_bundles, "action_bundles_unreadable"),
        load_json(args.coordinate_frame, "coordinate_frame_unreadable"),
    )
    (out / OUTPUTS["json"]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / OUTPUTS["summary"]).write_text(render_summary(result), encoding="utf-8")
    (out / OUTPUTS["analyst"]).write_text(render_analyst(result), encoding="utf-8")
    return 2 if result["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
