from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "provider_coordinate_attachment_semantics_lite_v1"
FIELD_MODULE_ID = "provider_alias_field_semantics_lite_v1"
LABEL_MODULE_ID = "provider_label_value_semantics_lite_v1"
NUCLEUS_MODULE_ID = "row_nucleus_inventory_lite_v1"
BUNDLE_MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
FRAME_MODULE_ID = "coordinate_frame_precondition_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
GK_ROLE = "GOALKEEPER_SURFACE_CANDIDATE"
INTERCEPTION_LABELS = {
    "successful cross and pass interception attempts": "SUCCESS",
    "unsuccessful cross and pass interception attempts": "FAILURE",
}
SAVE_LABEL = "shots saved"
OBJECT_FAMILIES = {"PASS", "CROSS"}
OUT = {
    "json": "provider_coordinate_attachment_semantics_lite_v1.json",
    "summary": "provider_coordinate_attachment_semantics_lite_v1.txt",
    "analyst": "provider_coordinate_attachment_semantics_analyst_audit_v1.txt",
}


def clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def norm(value: Any) -> str:
    return clean(value).casefold()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def _guard(name: str, payload: dict[str, Any], module_id: str) -> list[str]:
    blocks: list[str] = []
    if payload.get("module_id") != module_id:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    return blocks


def _field_basis(field_payload: dict[str, Any]) -> tuple[str, list[str]]:
    required = {
        "pos_x": "event.start_x_candidate",
        "pos_y": "event.start_y_candidate",
    }
    found = {key: False for key in required}
    for row in field_payload.get("field_semantic_records") or []:
        if row.get("format") != "csv" or row.get("source_role") != GK_ROLE:
            continue
        key = clean(row.get("normalized_field"))
        if key not in required:
            continue
        if (
            row.get("canonical_key_candidate") == required[key]
            and row.get("mapping_status") == "EXACT_RULE_CANDIDATE"
            and row.get("alias_reliability") == "HIGH"
        ):
            found[key] = True
    missing = [key for key, present in found.items() if not present]
    if missing:
        return (
            "FIELD_ATTACHMENT_BASIS_UNRESOLVED",
            [f"goalkeeper_{key}_event_location_candidate_missing" for key in missing],
        )
    return "EVENT_START_LOCATION_CANDIDATE_SUPPORTED", []


def _label_semantics(
    label_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    rows: dict[str, dict[str, Any]] = {}
    needed = set(INTERCEPTION_LABELS) | {SAVE_LABEL}
    for row in label_payload.get("provider_label_records") or []:
        label = norm(row.get("normalized_label"))
        if (
            label not in needed
            or row.get("source_role") != GK_ROLE
            or row.get("source_format") != "csv"
        ):
            continue
        if row.get("mapping_status") != "EXACT_REVIEWED_CANDIDATE":
            continue
        rows[label] = row

    reviews: list[str] = []
    for label in needed:
        if label not in rows:
            reviews.append(f"exact_label_semantics_missing:{label}")

    for label, outcome in INTERCEPTION_LABELS.items():
        row = rows.get(label) or {}
        if not (
            row.get("semantic_role_candidate") == "ACTION_ANCHOR"
            and row.get("action_family_candidate") == "INTERCEPTION"
            and row.get("action_subtype_candidate")
            == "CROSS_OR_PASS_INTERCEPTION"
            and row.get("object_action_family_candidate") == "PASS_OR_CROSS"
            and row.get("outcome_candidate") == outcome
            and row.get("downstream_eligibility") == "ACTION_CANDIDATE_ELIGIBLE"
        ):
            reviews.append(f"interception_semantics_contract_mismatch:{label}")

    save = rows.get(SAVE_LABEL) or {}
    if save and not (
        save.get("semantic_role_candidate") == "ACTION_ANCHOR"
        and save.get("action_family_candidate") == "GOALKEEPER_ACTION"
        and save.get("action_subtype_candidate") == "SAVE"
        and save.get("object_action_family_candidate") == "SHOT"
    ):
        reviews.append("save_semantics_control_mismatch")
    return rows, sorted(set(reviews))


def _nucleus_support(
    nucleus_payload: dict[str, Any],
) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in nucleus_payload.get("row_nuclei") or []:
        if row.get("source_role") != GK_ROLE:
            continue
        label = norm(row.get("action_raw"))
        if label not in set(INTERCEPTION_LABELS) | {SAVE_LABEL}:
            continue
        key = (
            label,
            clean(row.get("period_candidate")),
            clean(row.get("start_candidate")),
            clean(row.get("pos_x_candidate")),
            clean(row.get("pos_y_candidate")),
        )
        result[key] = row
    return result


def _surface_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        clean(row.get("period_candidate")),
        clean(row.get("start_candidate")),
        clean(row.get("end_candidate")),
        clean(row.get("pos_x_candidate")),
        clean(row.get("pos_y_candidate")),
    )


def _intervals_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    l0 = number(left.get("start_candidate"))
    l1 = number(left.get("end_candidate"))
    r0 = number(right.get("start_candidate"))
    r1 = number(right.get("end_candidate"))
    if None in {l0, l1, r0, r1}:
        return False
    assert l0 is not None and l1 is not None and r0 is not None and r1 is not None
    return max(l0, r0) <= min(l1, r1)


def _same_coordinate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    lx = number(left.get("pos_x_candidate"))
    ly = number(left.get("pos_y_candidate"))
    rx = number(right.get("pos_x_candidate"))
    ry = number(right.get("pos_y_candidate"))
    if None in {lx, ly, rx, ry}:
        return False
    return lx == rx and ly == ry


def build_provider_coordinate_attachment_semantics(
    field_payload: dict[str, Any],
    label_payload: dict[str, Any],
    nucleus_payload: dict[str, Any],
    bundle_payload: dict[str, Any],
    frame_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload, module_id in (
        ("field", field_payload, FIELD_MODULE_ID),
        ("label", label_payload, LABEL_MODULE_ID),
        ("nucleus", nucleus_payload, NUCLEUS_MODULE_ID),
        ("bundle", bundle_payload, BUNDLE_MODULE_ID),
        ("frame", frame_payload, FRAME_MODULE_ID),
    ):
        blocks.extend(_guard(name, payload, module_id))

    bindings = {
        clean(nucleus_payload.get("match_surface_binding_id")),
        clean(bundle_payload.get("match_surface_binding_id")),
        clean(frame_payload.get("match_surface_binding_id")),
    }
    bindings.discard("")
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch_or_missing")
    binding = next(iter(bindings), "")

    field_status, field_reviews = _field_basis(field_payload)
    reviews.extend(field_reviews)
    semantic_rows, semantic_reviews = _label_semantics(label_payload)
    reviews.extend(semantic_reviews)
    nucleus_index = _nucleus_support(nucleus_payload)

    all_bundles = bundle_payload.get("action_bundle_candidates") or []
    if not isinstance(all_bundles, list):
        blocks.append("action_bundle_inventory_invalid")
        all_bundles = []

    object_bundles = [
        row
        for row in all_bundles
        if row.get("action_family_candidate") in OBJECT_FAMILIES
        and row.get("coordinate_evidence_status") == "COORDINATE_PRESENT"
    ]
    shot_bundles = [
        row
        for row in all_bundles
        if row.get("action_family_candidate") == "SHOT"
        and row.get("coordinate_evidence_status") == "COORDINATE_PRESENT"
    ]

    selected: list[dict[str, Any]] = []
    excluded_review_count = 0
    for row in all_bundles:
        labels = {norm(value) for value in row.get("normalized_labels") or []}
        hits = labels & set(INTERCEPTION_LABELS)
        if (
            not hits
            or row.get("source_role") != GK_ROLE
            or row.get("action_family_candidate") != "INTERCEPTION"
        ):
            continue
        if row.get("bundle_status") != "PASS":
            excluded_review_count += 1
            continue
        if row.get("coordinate_evidence_status") != "COORDINATE_PRESENT":
            continue
        selected.append(row)

    exact_reflections = 0
    overlap_same_coordinate_reflections = 0
    row_support_missing = 0
    attachment_records: list[dict[str, Any]] = []
    group_counts: Counter[tuple[str, str]] = Counter()
    outcome_counts: Counter[str] = Counter()
    seen_bundle_ids: set[str] = set()

    for row in selected:
        bundle_id = clean(row.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in seen_bundle_ids:
            blocks.append("duplicate_or_missing_interception_bundle_id")
            continue
        seen_bundle_ids.add(bundle_id)

        label_hits = sorted(
            {norm(value) for value in row.get("normalized_labels") or []}
            & set(INTERCEPTION_LABELS)
        )
        if len(label_hits) != 1:
            reviews.append(f"interception_bundle_label_not_single:{bundle_id}")
            continue
        label = label_hits[0]
        outcome = INTERCEPTION_LABELS[label]

        nucleus_key = (
            label,
            clean(row.get("period_candidate")),
            clean(row.get("start_candidate")),
            clean(row.get("pos_x_candidate")),
            clean(row.get("pos_y_candidate")),
        )
        nucleus = nucleus_index.get(nucleus_key)
        cross_format = clean((nucleus or {}).get("cross_format_support_status"))
        if cross_format != "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT":
            row_support_missing += 1

        exact = 0
        overlap_same = 0
        for object_row in object_bundles:
            if _surface_key(object_row) == _surface_key(row):
                exact += 1
            elif (
                clean(object_row.get("period_candidate"))
                == clean(row.get("period_candidate"))
                and _same_coordinate(object_row, row)
                and _intervals_overlap(object_row, row)
            ):
                overlap_same += 1

        exact_reflections += exact
        overlap_same_coordinate_reflections += overlap_same
        team = clean(row.get("team_identity_candidate_id"))
        period = clean(row.get("period_candidate"))
        group_counts[(team, period)] += 1
        outcome_counts[outcome] += 1

        record_attachment_supported = bool(
            field_status == "EVENT_START_LOCATION_CANDIDATE_SUPPORTED"
            and exact == 0
            and overlap_same == 0
            and cross_format == "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT"
        )
        attachment_records.append(
            {
                "action_bundle_candidate_id": bundle_id,
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "normalized_label": label,
                "outcome_candidate": outcome,
                "pos_x_candidate": row.get("pos_x_candidate"),
                "pos_y_candidate": row.get("pos_y_candidate"),
                "cross_format_support_status": cross_format or "MISSING",
                "exact_object_action_surface_overlap_count": exact,
                "overlapping_same_coordinate_object_action_count": overlap_same,
                "coordinate_attachment_candidate": (
                    "EVENT_ACTION_LOCATION_CANDIDATE"
                    if record_attachment_supported
                    else "ATTACHMENT_REVIEW_REQUIRED"
                ),
                "validated_provider_semantics": False,
            }
        )

    save_rows: list[dict[str, Any]] = []
    save_exact = 0
    for row in all_bundles:
        labels = {norm(value) for value in row.get("normalized_labels") or []}
        if (
            SAVE_LABEL not in labels
            or row.get("source_role") != GK_ROLE
            or row.get("bundle_status") != "PASS"
        ):
            continue
        exact = sum(
            1 for shot_row in shot_bundles if _surface_key(shot_row) == _surface_key(row)
        )
        save_exact += exact
        save_rows.append(
            {
                "action_bundle_candidate_id": row.get("action_bundle_candidate_id"),
                "exact_shot_surface_overlap_count": exact,
            }
        )

    interception_attachment_supported = bool(
        not blocks
        and field_status == "EVENT_START_LOCATION_CANDIDATE_SUPPORTED"
        and not semantic_reviews
        and selected
        and row_support_missing == 0
        and exact_reflections == 0
        and overlap_same_coordinate_reflections == 0
        and all(
            record.get("coordinate_attachment_candidate")
            == "EVENT_ACTION_LOCATION_CANDIDATE"
            for record in attachment_records
        )
    )

    outcome_pooling_allowed = bool(
        interception_attachment_supported
        and outcome_counts.get("SUCCESS", 0) > 0
        and outcome_counts.get("FAILURE", 0) > 0
        and semantic_rows.get(
            "successful cross and pass interception attempts", {}
        ).get("action_subtype_candidate")
        == "CROSS_OR_PASS_INTERCEPTION"
        and semantic_rows.get(
            "unsuccessful cross and pass interception attempts", {}
        ).get("action_subtype_candidate")
        == "CROSS_OR_PASS_INTERCEPTION"
    )

    pooled_groups = [
        {
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "unique_interception_action_bundle_count": count,
        }
        for (team, period), count in sorted(group_counts.items())
    ]

    if not interception_attachment_supported:
        reviews.append("goalkeeper_interception_attachment_candidate_not_closed")
    if save_rows and save_exact == 0:
        reviews.append("save_reflection_control_not_observed")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = (
        "FAIL_CLOSED"
        if blocks
        else ("REVIEW_REQUIRED" if not interception_attachment_supported else "PASS")
    )

    return {
        "module_id": MODULE_ID,
        "version": "1.0.0",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "field_attachment_basis_status": field_status,
        "goalkeeper_interception_attachment_status": (
            "EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED"
            if interception_attachment_supported
            else "ATTACHMENT_REVIEW_REQUIRED"
        ),
        "goalkeeper_interception_primary_direction_anchor_candidate_allowed": (
            interception_attachment_supported
        ),
        "outcome_stratified_support_pooling_allowed": outcome_pooling_allowed,
        "event_fusion_allowed": False,
        "interception_pass_bundle_count": len(selected),
        "interception_review_bundle_excluded_count": excluded_review_count,
        "interception_outcome_counts": dict(sorted(outcome_counts.items())),
        "interception_team_period_support": pooled_groups,
        "interception_attachment_records": attachment_records,
        "exact_object_action_surface_overlap_count": exact_reflections,
        "overlapping_same_coordinate_object_action_count": (
            overlap_same_coordinate_reflections
        ),
        "row_cross_format_support_missing_count": row_support_missing,
        "save_control_bundle_count": len(save_rows),
        "save_control_exact_shot_surface_overlap_count": save_exact,
        "save_control_status": (
            "OBJECT_ACTION_REFLECTION_CONTROL_CONFIRMED"
            if save_rows and save_exact > 0
            else "CONTROL_REVIEW_REQUIRED"
        ),
        "coordinate_attachment_is_validated_provider_truth": False,
        "coordinate_is_goalkeeper_physical_position_truth": False,
        "coordinate_frame_contract_change_allowed": interception_attachment_supported,
        "attack_direction_is_validated_truth": False,
        "progression_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "hard_block_hits": blocks,
        "review_hits": reviews,
    }


def render_summary(payload: dict[str, Any]) -> str:
    keys = [
        "module_id",
        "status",
        "field_attachment_basis_status",
        "goalkeeper_interception_attachment_status",
        "goalkeeper_interception_primary_direction_anchor_candidate_allowed",
        "outcome_stratified_support_pooling_allowed",
        "interception_pass_bundle_count",
        "interception_review_bundle_excluded_count",
        "exact_object_action_surface_overlap_count",
        "overlapping_same_coordinate_object_action_count",
        "save_control_exact_shot_surface_overlap_count",
        "hard_block_hits",
        "review_hits",
        "canonical_event_count",
        "production_release",
    ]
    return "\n".join(f"{key}={payload.get(key)}" for key in keys) + "\n"


def render_analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — PROVIDER COORDINATE ATTACHMENT SEMANTICS LITE V1",
        f"status={payload.get('status')}",
        (
            "goalkeeper_interception_attachment="
            f"{payload.get('goalkeeper_interception_attachment_status')}"
        ),
        f"eligible_interception_rows={payload.get('interception_pass_bundle_count')}",
        (
            "excluded_review_rows="
            f"{payload.get('interception_review_bundle_excluded_count')}"
        ),
        (
            "exact_pass_cross_reflections="
            f"{payload.get('exact_object_action_surface_overlap_count')}"
        ),
        (
            "overlapping_same_coordinate_pass_cross_reflections="
            f"{payload.get('overlapping_same_coordinate_object_action_count')}"
        ),
        (
            "save_control_shot_reflections="
            f"{payload.get('save_control_exact_shot_surface_overlap_count')}"
        ),
        (
            "safe_meaning=visible goalkeeper interception rows support an event-action "
            "location candidate; this is not tracking or goalkeeper physical-position truth."
        ),
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(
    field_path: str,
    label_path: str,
    nucleus_path: str,
    bundle_path: str,
    frame_path: str,
    out_dir: str,
) -> dict[str, Any]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = build_provider_coordinate_attachment_semantics(
        load_json(field_path, "field_input_invalid"),
        load_json(label_path, "label_input_invalid"),
        load_json(nucleus_path, "nucleus_input_invalid"),
        load_json(bundle_path, "bundle_input_invalid"),
        load_json(frame_path, "frame_input_invalid"),
    )
    (output / OUT["json"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / OUT["summary"]).write_text(render_summary(payload), encoding="utf-8")
    (output / OUT["analyst"]).write_text(render_analyst(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field-semantics", required=True)
    parser.add_argument("--label-semantics", required=True)
    parser.add_argument("--row-nuclei", required=True)
    parser.add_argument("--action-bundles", required=True)
    parser.add_argument("--coordinate-frame", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        payload = write_outputs(
            args.field_semantics,
            args.label_semantics,
            args.row_nuclei,
            args.action_bundles,
            args.coordinate_frame,
            args.out,
        )
    except ValueError as exc:
        print(f"status=FAIL_CLOSED\nreason={exc}")
        return 2
    print(render_summary(payload), end="")
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
