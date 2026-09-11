from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "occurrence_state_transition_projection_v1"
SPATIAL_MODULE_ID = "spatial_transition_candidate_lite_v1"
OCCURRENCE_CONSEQUENCE_MODULE_ID = "occurrence_consequence_projection_v1"
OUTPUT_JSON = "occurrence_state_transition_projection_v1.json"
OUTPUT_TXT = "occurrence_state_transition_projection_v1.txt"

DIRECTIONAL_CONSEQUENCES = {
    "SHOT_FOLLOW_UP_CANDIDATE",
    "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
    "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
    "RESTART_OR_RESET_CANDIDATE",
    "SAME_TEAM_CONTINUATION_CANDIDATE",
    "OPPONENT_HANDOVER_CANDIDATE",
}
ADVERSE_CONSEQUENCES = {
    "OPPONENT_HANDOVER_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sorted_text(values: Any) -> list[str]:
    return sorted({_text(value) for value in _values(values) if _text(value)})


def _union(rows: list[dict[str, Any]], key: str) -> list[str]:
    out: set[str] = set()
    for row in rows:
        out.update(_sorted_text(row.get(key)))
    return sorted(out)


def _candidate_id(occurrence_id: str) -> str:
    digest = hashlib.sha1(occurrence_id.encode("utf-8")).hexdigest()[:24]
    return f"ostp_{digest}"


def _class_candidates(
    progression: list[str],
    zones: list[str],
    consequence_classes: list[str],
) -> list[str]:
    classes: set[str] = set()
    for consequence_class in consequence_classes:
        if progression and consequence_class == "SHOT_FOLLOW_UP_CANDIDATE":
            classes.add("PROGRESSIVE_TO_SHOT_FOLLOW_UP_CANDIDATE")
        elif progression and consequence_class in {
            "SAME_TEAM_CONTINUATION_CANDIDATE",
            "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
        }:
            classes.add("PROGRESSIVE_TO_SAME_TEAM_CONTINUATION_CANDIDATE")
        elif progression and consequence_class in ADVERSE_CONSEQUENCES:
            classes.add("PROGRESSIVE_TO_ADVERSE_HANDOVER_CANDIDATE")
        elif "OPPONENT_HALF" in zones and consequence_class == "SAME_TEAM_CONTINUATION_CANDIDATE":
            classes.add("OPPONENT_HALF_ACTION_TO_SAME_TEAM_CONTINUATION_CANDIDATE")
        elif "FINAL_THIRD" in zones and consequence_class == "SHOT_FOLLOW_UP_CANDIDATE":
            classes.add("FINAL_THIRD_ACTION_TO_SHOT_FOLLOW_UP_CANDIDATE")
        elif consequence_class in DIRECTIONAL_CONSEQUENCES:
            classes.add("VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE")
        elif consequence_class == "TERMINAL_OUTCOME_SUPPORT_CANDIDATE":
            classes.add("TERMINAL_SUPPORT_ASSOCIATION_CANDIDATE")
        elif consequence_class == "NO_VISIBLE_FOLLOW_UP_CANDIDATE":
            classes.add("NO_VISIBLE_FOLLOW_UP_ASSOCIATION_CANDIDATE")
        else:
            classes.add("REVIEW_REQUIRED_TRANSITION_CANDIDATE")
    if not classes:
        classes.add("REVIEW_REQUIRED_TRANSITION_CANDIDATE")
    return sorted(classes)


def build_occurrence_state_transition_projection(
    spatial_payload: dict[str, Any],
    occurrence_consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if spatial_payload.get("module_id") != SPATIAL_MODULE_ID:
        hard_blocks.append("spatial_input_module_id_mismatch")
    if occurrence_consequence_payload.get("module_id") != OCCURRENCE_CONSEQUENCE_MODULE_ID:
        hard_blocks.append("occurrence_consequence_input_module_id_mismatch")
    for prefix, payload in (
        ("spatial", spatial_payload),
        ("occurrence_consequence", occurrence_consequence_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            hard_blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            hard_blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            hard_blocks.append(f"{prefix}_hard_blocks_present")

    spatial_rows = [
        row
        for row in _values(spatial_payload.get("spatial_transition_candidates"))
        if isinstance(row, dict)
    ]
    occurrence_rows = [
        row
        for row in _values(occurrence_consequence_payload.get("occurrence_consequence_projections"))
        if isinstance(row, dict)
    ]
    if spatial_payload.get("spatial_transition_candidate_count") != len(spatial_rows):
        hard_blocks.append("spatial_candidate_count_mismatch")
    expected_occurrence_count = int(
        occurrence_consequence_payload.get("occurrence_consequence_projection_count") or 0
    )
    if expected_occurrence_count != len(occurrence_rows):
        hard_blocks.append("occurrence_consequence_projection_count_mismatch")

    spatial_by_trace: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(spatial_rows):
        trace_id = _text(row.get("trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in spatial_by_trace:
            hard_blocks.append(f"spatial_trace_id_invalid_or_duplicate:{index}")
            continue
        spatial_by_trace[trace_id] = row

    records: list[dict[str, Any]] = []
    if not hard_blocks:
        for index, occurrence in enumerate(occurrence_rows):
            occurrence_id = _text(occurrence.get("action_occurrence_candidate_id"))
            if not occurrence_id:
                hard_blocks.append(f"occurrence_id_missing:{index}")
                continue
            trace_ids = _sorted_text(
                occurrence.get("supporting_trackable_action_trace_candidate_ids")
            )
            supporting_spatial = [spatial_by_trace[trace_id] for trace_id in trace_ids if trace_id in spatial_by_trace]
            missing_spatial_trace_ids = sorted(set(trace_ids) - set(spatial_by_trace))

            progression = _union(supporting_spatial, "provider_progression_candidates")
            zones = _union(supporting_spatial, "provider_zone_candidates")
            contexts = _union(supporting_spatial, "provider_context_candidates")
            directions = _union(supporting_spatial, "provider_direction_candidates")
            outcomes = _union(supporting_spatial, "provider_outcome_candidates")
            semantic_rule_ids = _union(supporting_spatial, "provider_semantic_rule_ids")
            spatial_candidate_ids = sorted(
                {
                    _text(row.get("spatial_transition_candidate_id"))
                    for row in supporting_spatial
                    if _text(row.get("spatial_transition_candidate_id"))
                }
            )
            consequence_classes = _sorted_text(
                occurrence.get("primary_consequence_candidates")
            )
            admitted_after = _sorted_text(
                occurrence.get("admitted_after_follow_up_trace_ids")
            )
            transition_classes = _class_candidates(
                progression,
                zones,
                consequence_classes,
            )
            directional_visible = any(
                value in DIRECTIONAL_CONSEQUENCES for value in consequence_classes
            )
            record_reviews: list[str] = []
            if occurrence.get("record_status") == "REVIEW_REQUIRED":
                record_reviews.append("occurrence_consequence_review_required")
            if missing_spatial_trace_ids:
                record_reviews.append("supporting_spatial_trace_missing")
            if any(
                row.get("spatial_admission_state") == "REVIEW_REQUIRED"
                for row in supporting_spatial
            ):
                record_reviews.append("spatial_review_required")
            if "REVIEW_REQUIRED_TRANSITION_CANDIDATE" in transition_classes:
                record_reviews.append("transition_class_review_required")
            if directional_visible and not admitted_after:
                record_reviews.append("directional_consequence_without_after_admission")

            support_candidates: list[str] = []
            if progression:
                support_candidates.append("PROVIDER_PROGRESSION_SEMANTIC_VISIBLE")
            if zones:
                support_candidates.append("PROVIDER_ZONE_SEMANTIC_VISIBLE")
            if contexts:
                support_candidates.append("PROVIDER_CONTEXT_SEMANTIC_VISIBLE")
            if directions:
                support_candidates.append("PROVIDER_DIRECTION_SEMANTIC_VISIBLE")
            if consequence_classes:
                support_candidates.append("VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT")
            if admitted_after:
                support_candidates.append("AFTER_CONFIRMED_FOLLOW_UP_PRESENT")

            records.append(
                {
                    "occurrence_state_transition_projection_id": _candidate_id(occurrence_id),
                    "action_occurrence_candidate_id": occurrence_id,
                    "occurrence_consequence_projection_id": occurrence.get(
                        "occurrence_consequence_projection_id"
                    ),
                    "occurrence_topology": occurrence.get("occurrence_topology"),
                    "supporting_trackable_action_trace_candidate_ids": trace_ids,
                    "supporting_spatial_transition_candidate_ids": spatial_candidate_ids,
                    "supporting_consequence_candidate_ids": occurrence.get(
                        "supporting_consequence_candidate_ids"
                    )
                    or [],
                    "missing_spatial_trace_ids": missing_spatial_trace_ids,
                    "actor_identity_candidate_ids": occurrence.get("actor_identity_candidate_ids") or [],
                    "team_identity_candidate_ids": occurrence.get("team_identity_candidate_ids") or [],
                    "action_family_candidates": occurrence.get("action_family_candidates") or [],
                    "provider_progression_candidates": progression,
                    "provider_zone_candidates": zones,
                    "provider_context_candidates": contexts,
                    "provider_direction_candidates": directions,
                    "provider_outcome_candidates": outcomes,
                    "provider_semantic_rule_ids": semantic_rule_ids,
                    "primary_consequence_candidates": consequence_classes,
                    "admitted_after_follow_up_trace_ids": admitted_after,
                    "transition_class_candidates": transition_classes,
                    "support_candidates": support_candidates,
                    "adverse_consequence_candidates": sorted(
                        set(consequence_classes) & ADVERSE_CONSEQUENCES
                    ),
                    "record_status": "REVIEW_REQUIRED" if record_reviews else "PASS_CANDIDATE_CLASSIFICATION",
                    "review_hits": sorted(set(record_reviews)),
                    "legacy_trace_records_are_support_evidence_not_action_universe": True,
                    "occurrence_projection_is_primary_action_member_candidate_surface": True,
                    "provider_semantic_progression_is_measured_displacement_truth": False,
                    "same_timestamp_is_total_order": False,
                    "source_row_order_is_temporal_truth": False,
                    "transition_is_possession_truth": False,
                    "transition_is_sequence_truth": False,
                    "transition_is_tactical_pattern_truth": False,
                    "transition_is_causal_truth": False,
                    "coach_intention_truth": False,
                    "canonical_event_count": "UNKNOWN",
                    "true_action_count": "UNKNOWN",
                    "production_release": False,
                }
            )

    if hard_blocks:
        records = []
    if len(records) != expected_occurrence_count and not hard_blocks:
        hard_blocks.append("occurrence_state_projection_count_mismatch")
        records = []
    review_count = sum(row.get("record_status") == "REVIEW_REQUIRED" for row in records)
    if review_count:
        review_hits.append("occurrence_state_transition_projection_review_required")
    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "source_spatial_status": spatial_payload.get("status"),
        "source_occurrence_consequence_status": occurrence_consequence_payload.get("status"),
        "source_legacy_spatial_candidate_count": len(spatial_rows),
        "source_action_occurrence_candidate_count": expected_occurrence_count,
        "occurrence_state_transition_projection_count": len(records),
        "review_required_occurrence_state_transition_count": review_count,
        "occurrence_state_transition_projections": records,
        "legacy_trace_records_are_support_evidence_not_action_universe": True,
        "occurrence_projection_is_primary_action_member_candidate_surface": True,
        "state_transition_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_pattern_truth": False,
        "causality_truth": False,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(
        "\n".join(
            [
                "HPFA OCCURRENCE STATE TRANSITION PROJECTION V1",
                f"status={payload.get('status')}",
                f"source_action_occurrence_candidate_count={payload.get('source_action_occurrence_candidate_count', 0)}",
                f"occurrence_state_transition_projection_count={payload.get('occurrence_state_transition_projection_count', 0)}",
                f"review_required_occurrence_state_transition_count={payload.get('review_required_occurrence_state_transition_count', 0)}",
                f"source_legacy_spatial_candidate_count={payload.get('source_legacy_spatial_candidate_count', 0)}",
                "legacy_trace_records_are_support_evidence_not_action_universe=true",
                "occurrence_projection_is_primary_action_member_candidate_surface=true",
                "state_transition_truth=false",
                "sequence_truth=false",
                "canonical_event_count=UNKNOWN",
                "true_action_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "txt": txt_path}
