from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

MODULE_ID = "coordinate_frame_anchor_recheck_lite_v1"
VERSION = "1.0.0"
CANONICAL_EVENT_COUNT = "UNKNOWN"
FRAME_MODULE = "coordinate_frame_precondition_lite_v1"
ATTACHMENT_MODULE = "provider_coordinate_attachment_semantics_lite_v1"
RESOLVED_DIRECTIONS = {
    "ATTACK_TOWARD_HIGH_X_CANDIDATE",
    "ATTACK_TOWARD_LOW_X_CANDIDATE",
}
MIN_PRIMARY_COUNTER_ANCHOR_SUPPORT = 2
OUTPUTS = {
    "json": "coordinate_frame_anchor_recheck_lite_v1.json",
    "summary": "coordinate_frame_anchor_recheck_lite_v1.txt",
    "analyst": "coordinate_frame_anchor_recheck_analyst_audit_v1.txt",
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


def _base_guard(frame: dict[str, Any], attachment: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    if frame.get("module_id") != FRAME_MODULE:
        blocks.append("coordinate_frame_module_id_mismatch")
    if attachment.get("module_id") != ATTACHMENT_MODULE:
        blocks.append("coordinate_attachment_module_id_mismatch")
    for name, payload in (("coordinate_frame", frame), ("coordinate_attachment", attachment)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
    if clean(attachment.get("status") or attachment.get("module_status")) != "PASS":
        blocks.append("coordinate_attachment_status_not_pass")
    if attachment.get("review_hits"):
        blocks.append("coordinate_attachment_review_hits_present")
    if (
        clean(attachment.get("goalkeeper_interception_attachment_status"))
        != "EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED"
    ):
        blocks.append("goalkeeper_interception_attachment_not_supported")
    if attachment.get("goalkeeper_interception_primary_direction_anchor_candidate_allowed") is not True:
        blocks.append("goalkeeper_interception_primary_anchor_not_admitted")
    if attachment.get("outcome_stratified_support_pooling_allowed") is not True:
        blocks.append("outcome_stratified_support_pooling_not_admitted")
    if attachment.get("event_fusion_allowed") is not False:
        blocks.append("event_fusion_boundary_missing_or_violated")
    if attachment.get("coordinate_attachment_is_validated_provider_truth") is not False:
        blocks.append("validated_provider_truth_boundary_missing_or_violated")
    if attachment.get("coordinate_is_goalkeeper_physical_position_truth") is not False:
        blocks.append("goalkeeper_physical_position_truth_boundary_missing_or_violated")
    fbind = clean(frame.get("match_surface_binding_id"))
    abind = clean(attachment.get("match_surface_binding_id"))
    if not fbind or not abind or fbind != abind:
        blocks.append("match_surface_binding_mismatch_or_missing")
    return blocks


def _interception_group_x(
    attachment: dict[str, Any]
) -> tuple[dict[tuple[str, str], list[float]], list[str]]:
    rows = attachment.get("interception_attachment_records")
    if not isinstance(rows, list):
        return {}, ["interception_attachment_inventory_invalid"]
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    blocks: list[str] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"interception_attachment_record_invalid:{index}")
            continue
        bundle_id = clean(row.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in seen_ids:
            blocks.append(f"interception_action_bundle_id_missing_or_duplicate:{index}")
            continue
        seen_ids.add(bundle_id)
        if clean(row.get("coordinate_attachment_candidate")) != "EVENT_ACTION_LOCATION_CANDIDATE":
            blocks.append(f"interception_attachment_candidate_invalid:{index}")
            continue
        if clean(row.get("cross_format_support_status")) != "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT":
            blocks.append(f"interception_cross_format_support_invalid:{index}")
            continue
        if int(row.get("exact_object_action_surface_overlap_count") or 0) != 0:
            blocks.append(f"interception_exact_object_reflection_present:{index}")
            continue
        if int(row.get("overlapping_same_coordinate_object_action_count") or 0) != 0:
            blocks.append(f"interception_window_coordinate_reflection_present:{index}")
            continue
        if row.get("validated_provider_semantics") is not False:
            blocks.append(f"interception_provider_truth_boundary_invalid:{index}")
            continue
        team = clean(row.get("team_identity_candidate_id"))
        period = clean(row.get("period_candidate"))
        x = number(row.get("pos_x_candidate"))
        if not team or not period or x is None:
            blocks.append(f"interception_group_or_coordinate_missing:{index}")
            continue
        grouped[(team, period)].append(x)
    declared = attachment.get("interception_pass_bundle_count")
    if isinstance(declared, int) and declared != len(rows):
        blocks.append("interception_pass_bundle_count_mismatch")
    return grouped, blocks


def _goal_side_direction(
    xs: list[float], pitch_length: float
) -> tuple[str, str, float | None]:
    if len(xs) < MIN_PRIMARY_COUNTER_ANCHOR_SUPPORT:
        return (
            "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
            "INSUFFICIENT_INTERCEPTION_COUNTER_ANCHOR_SUPPORT",
            None,
        )
    normalized = [x / pitch_length for x in xs]
    med = median(normalized)
    if med <= 0.30:
        return (
            "ATTACK_TOWARD_HIGH_X_CANDIDATE",
            "PASS_INTERCEPTION_GOAL_SIDE_COUNTER_ANCHOR_CANDIDATE",
            med,
        )
    if med >= 0.70:
        return (
            "ATTACK_TOWARD_LOW_X_CANDIDATE",
            "PASS_INTERCEPTION_GOAL_SIDE_COUNTER_ANCHOR_CANDIDATE",
            med,
        )
    return (
        "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
        "INTERCEPTION_ANCHOR_DISTRIBUTION_AMBIGUOUS_REVIEW_REQUIRED",
        med,
    )


def build_coordinate_frame_anchor_recheck(
    coordinate_frame: dict[str, Any],
    coordinate_attachment: dict[str, Any],
) -> dict[str, Any]:
    blocks = _base_guard(coordinate_frame, coordinate_attachment)
    grouped_x, group_blocks = _interception_group_x(coordinate_attachment)
    blocks.extend(group_blocks)

    rows = coordinate_frame.get("team_period_coordinate_frame_candidates")
    if not isinstance(rows, list):
        rows = []
        blocks.append("coordinate_frame_group_inventory_invalid")
    expected = coordinate_frame.get("expected_team_period_group_count")
    if not isinstance(expected, int) or expected != len(rows):
        blocks.append("coordinate_frame_group_count_mismatch")

    length = number(coordinate_frame.get("pitch_length_candidate"))
    scale_gate = (
        clean(coordinate_frame.get("coordinate_scale_candidate"))
        == "PROVIDER_105X68_SCALE_CANDIDATE"
        and clean(coordinate_frame.get("coordinate_bounds_status"))
        == "PASS_CANDIDATE_BOUNDS"
        and length == 105.0
    )
    if not scale_gate:
        blocks.append("coordinate_scale_or_bounds_precondition_not_met")

    group_records: list[dict[str, Any]] = []
    pass_count = 0
    conflict_count = 0
    interception_primary_group_count = 0
    interception_gap_closure_count = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"coordinate_frame_group_record_invalid:{index}")
            continue
        team = clean(row.get("team_identity_candidate_id"))
        period = clean(row.get("period_candidate"))
        if not team or not period:
            blocks.append(f"coordinate_frame_group_identity_missing:{index}")
            continue

        shot_direction = clean(row.get("shot_direction_candidate"))
        if shot_direction not in RESOLVED_DIRECTIONS:
            shot_direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"

        goal_direction = clean(row.get("goalkeeper_goal_kick_direction_candidate"))
        if goal_direction not in RESOLVED_DIRECTIONS:
            goal_direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"

        ix = grouped_x.get((team, period), [])
        if length:
            interception_direction, interception_support, interception_median = _goal_side_direction(ix, length)
        else:
            interception_direction, interception_support, interception_median = (
                "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED",
                "SCALE_REQUIRED",
                None,
            )

        counter_directions = [
            direction
            for direction in (goal_direction, interception_direction)
            if direction in RESOLVED_DIRECTIONS
        ]
        primary_directions = [
            direction
            for direction in (shot_direction, *counter_directions)
            if direction in RESOLVED_DIRECTIONS
        ]

        baseline_gate = clean(row.get("multi_anchor_gate"))
        baseline_pass = baseline_gate == "PASS_MULTI_ANCHOR_CANDIDATE"

        if (
            shot_direction in RESOLVED_DIRECTIONS
            and counter_directions
            and len(set(primary_directions)) == 1
        ):
            gate = "PASS_MULTI_ANCHOR_RECHECK_CANDIDATE"
            direction = shot_direction
            pass_count += 1
        elif len(primary_directions) >= 2 and len(set(primary_directions)) > 1:
            gate = "CONFLICTING_PRIMARY_ANCHORS_REVIEW_REQUIRED"
            direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"
            conflict_count += 1
        else:
            gate = "INDEPENDENT_PRIMARY_ANCHORS_INSUFFICIENT"
            direction = "UNRESOLVED_ATTACK_DIRECTION_REVIEW_REQUIRED"

        interception_admitted = interception_direction in RESOLVED_DIRECTIONS
        if interception_admitted:
            interception_primary_group_count += 1
        if not baseline_pass and gate == "PASS_MULTI_ANCHOR_RECHECK_CANDIDATE" and interception_admitted:
            interception_gap_closure_count += 1

        group_records.append(
            {
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "baseline_multi_anchor_gate": baseline_gate or None,
                "shot_direction_candidate": shot_direction,
                "goalkeeper_goal_kick_anchor_count": int(row.get("goalkeeper_goal_kick_anchor_count") or 0),
                "goalkeeper_goal_kick_direction_candidate": goal_direction,
                "goalkeeper_interception_anchor_count": len(ix),
                "goalkeeper_interception_normalized_x_median": (
                    None if interception_median is None else round(interception_median, 6)
                ),
                "goalkeeper_interception_direction_candidate": interception_direction,
                "goalkeeper_interception_support_status": interception_support,
                "goalkeeper_interception_primary_anchor_candidate_admitted": interception_admitted,
                "recheck_multi_anchor_gate": gate,
                "attack_direction_candidate": direction,
                "attack_direction_is_validated_truth": False,
            }
        )

    all_expected_pass = bool(rows) and pass_count == len(rows)
    allowed = bool(
        not blocks
        and scale_gate
        and all_expected_pass
        and conflict_count == 0
    )

    directions = {
        record["attack_direction_candidate"]
        for record in group_records
        if record["attack_direction_candidate"] in RESOLVED_DIRECTIONS
    }
    if allowed and directions == {"ATTACK_TOWARD_HIGH_X_CANDIDATE"}:
        frame_candidate = "TEAM_ATTACK_NORMALIZED_POSITIVE_X_CANDIDATE"
    elif allowed:
        frame_candidate = "TEAM_PERIOD_DIRECTION_MAP_CANDIDATE"
    else:
        frame_candidate = "FRAME_UNRESOLVED"

    baseline_pass_count = int(coordinate_frame.get("multi_anchor_pass_group_count") or 0)
    recheck_specific_reviews: list[str] = []
    if not all_expected_pass:
        recheck_specific_reviews.append("independent_primary_anchor_families_insufficient_or_conflicted")

    status = "FAIL_CLOSED" if blocks else "PASS" if allowed else "REVIEW_REQUIRED"
    baseline_reviews = coordinate_frame.get("review_hits")
    if not isinstance(baseline_reviews, list):
        baseline_reviews = []

    return {
        "module_id": MODULE_ID,
        "version": VERSION,
        "status": status,
        "module_status": status,
        "match_surface_binding_id": clean(coordinate_frame.get("match_surface_binding_id")),
        "source_module_ids": {
            "coordinate_frame": FRAME_MODULE,
            "coordinate_attachment": ATTACHMENT_MODULE,
        },
        "expected_team_period_group_count": len(rows),
        "baseline_multi_anchor_pass_group_count": baseline_pass_count,
        "recheck_multi_anchor_pass_group_count": pass_count,
        "primary_anchor_conflict_group_count": conflict_count,
        "goalkeeper_interception_primary_anchor_group_count": interception_primary_group_count,
        "goalkeeper_interception_gap_closure_group_count": interception_gap_closure_count,
        "primary_counter_anchor_minimum_support": MIN_PRIMARY_COUNTER_ANCHOR_SUPPORT,
        "threshold_relaxation_allowed": False,
        "coordinate_frame_contract_overwrite": False,
        "coordinate_frame_recheck_candidate": frame_candidate,
        "progression_metric_recheck_allowed": allowed,
        "team_period_coordinate_frame_recheck_candidates": group_records,
        "baseline_review_hits_preserved": baseline_reviews,
        "review_hits": recheck_specific_reviews,
        "hard_block_hits": blocks,
        "coordinate_attachment_is_validated_provider_truth": False,
        "coordinate_is_goalkeeper_physical_position_truth": False,
        "coordinate_frame_is_validated_provider_truth": False,
        "attack_direction_is_validated_truth": False,
        "progression_truth": False,
        "line_break_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "release_status": "NOT_PRODUCTION",
    }


def write_outputs(payload: dict[str, Any], out: str | Path) -> None:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    (output / OUTPUTS["json"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = "\n".join(
        [
            f"module_id={MODULE_ID}",
            f"status={payload['status']}",
            f"baseline_multi_anchor_pass_group_count={payload['baseline_multi_anchor_pass_group_count']}",
            f"recheck_multi_anchor_pass_group_count={payload['recheck_multi_anchor_pass_group_count']}",
            f"goalkeeper_interception_gap_closure_group_count={payload['goalkeeper_interception_gap_closure_group_count']}",
            f"primary_anchor_conflict_group_count={payload['primary_anchor_conflict_group_count']}",
            f"coordinate_frame_recheck_candidate={payload['coordinate_frame_recheck_candidate']}",
            f"progression_metric_recheck_allowed={payload['progression_metric_recheck_allowed']}",
            f"hard_block_hits={payload['hard_block_hits']}",
            f"review_hits={payload['review_hits']}",
            "canonical_event_count=UNKNOWN",
            "production_release=False",
        ]
    ) + "\n"
    (output / OUTPUTS["summary"]).write_text(summary, encoding="utf-8")
    analyst = "\n".join(
        [
            "HPFA ANALYST AUDIT — COORDINATE FRAME ANCHOR RECHECK LITE V1",
            f"status={payload['status']}",
            f"visible_team_period_groups={payload['expected_team_period_group_count']}",
            f"baseline_multi_anchor_pass_groups={payload['baseline_multi_anchor_pass_group_count']}",
            f"recheck_multi_anchor_pass_groups={payload['recheck_multi_anchor_pass_group_count']}",
            f"interception_closed_baseline_gaps={payload['goalkeeper_interception_gap_closure_group_count']}",
            f"primary_anchor_conflicts={payload['primary_anchor_conflict_group_count']}",
            f"progression_metric_recheck_allowed={str(payload['progression_metric_recheck_allowed']).lower()}",
            "safe_meaning=reflection-cleared goalkeeper interception event-action locations may provide an alternate goal-side counter-anchor candidate when they agree with the existing shot direction; this is not tracking, physical goalkeeper-position, provider-definition, tactical, or progression truth.",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]
    ) + "\n"
    (output / OUTPUTS["analyst"]).write_text(analyst, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coordinate-frame", required=True)
    parser.add_argument("--coordinate-attachment", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        frame = load_json(args.coordinate_frame, "coordinate_frame_input_invalid")
        attachment = load_json(args.coordinate_attachment, "coordinate_attachment_input_invalid")
        payload = build_coordinate_frame_anchor_recheck(frame, attachment)
        write_outputs(payload, args.out)
    except ValueError as exc:
        print(f"status=FAIL_CLOSED\nreason={exc}\ncanonical_event_count=UNKNOWN\nproduction_release=False")
        return 2
    print((validate_out(args.out) / OUTPUTS["summary"]).read_text(encoding="utf-8"), end="")
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
