from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "episode_feature_vector_lite_v1"
EPISODE_MODULE_ID = "analyst_episode_locator_lite_v1"
SEMANTIC_MODULE_ID = "context_action_semantics_rebind_lite_v1"
CLAIM_CEILING = "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY"
OUTPUT_JSON = "episode_feature_vector_lite_v1.json"
OUTPUT_TXT = "episode_feature_vector_lite_v1.txt"
ANALYST_TXT = "episode_feature_vector_analyst_audit_v1.txt"
ACTION_VOLUME_BASIS = "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY"

UNKNOWN_TEAM_VALUES = {"", "unknown", "none", "null"}
UNKNOWN_ZONE_VALUES = {"", "UNKNOWN_ZONE", "unknown", "none", "null"}
UNKNOWN_CHANNEL_VALUES = {"", "UNKNOWN_CHANNEL", "unknown", "none", "null"}
REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _shares(counts: Counter[str], denominator: int) -> dict[str, float]:
    if denominator <= 0:
        return {}
    return {
        key: round(value / denominator, 6)
        for key, value in sorted(counts.items())
    }


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"episode_feature_input_unreadable:{source.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"episode_feature_input_malformed:{source.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"episode_feature_input_not_object:{source.name}")
    return payload


def _validate_inputs(
    episode: dict[str, Any],
    semantics: dict[str, Any],
) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []

    if episode.get("module_id") != EPISODE_MODULE_ID:
        blocks.append("episode_module_id_mismatch")
    if semantics.get("module_id") != SEMANTIC_MODULE_ID:
        blocks.append("semantic_module_id_mismatch")

    for name, payload in (("episode", episode), ("semantics", semantics)):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")

    if episode.get("context_assignment_complete") is not True:
        blocks.append("episode_context_assignment_incomplete")
    if episode.get("reflection_inflation_prevented") is not True:
        blocks.append("episode_reflection_inflation_not_prevented")
    if episode.get("action_volume_basis") != ACTION_VOLUME_BASIS:
        blocks.append("episode_action_volume_basis_mismatch")
    if episode.get("support_rows_add_action_volume") is not False:
        blocks.append("episode_support_rows_add_action_volume")
    if episode.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("episode_same_time_policy_breached")
    if episode.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("episode_source_row_order_policy_breached")
    if episode.get("hard_block_hits"):
        blocks.append("episode_upstream_hard_block_visible")

    if semantics.get("context_semantic_assignment_complete") is not True:
        blocks.append("semantic_context_assignment_incomplete")
    if semantics.get("reflection_inflation_prevented") is not True:
        blocks.append("semantic_reflection_inflation_not_prevented")
    if semantics.get("reference_participation_context_adds_action_volume") is not False:
        blocks.append("semantic_non_action_volume_policy_breached")
    if semantics.get("review_limited_semantics_adds_action_volume") is not False:
        blocks.append("semantic_review_limited_volume_policy_breached")
    if semantics.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("semantic_same_time_policy_breached")
    if semantics.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("semantic_source_row_order_policy_breached")
    if semantics.get("hard_block_hits"):
        blocks.append("semantic_upstream_hard_block_visible")

    episodes = episode.get("episode_candidates")
    records = semantics.get("context_action_semantic_records")
    if not isinstance(episodes, list) or not episodes:
        blocks.append("episode_candidates_empty_or_invalid")
        episodes = []
    if not isinstance(records, list) or not records:
        blocks.append("semantic_records_empty_or_invalid")
        records = []
    if _safe_int(episode.get("episode_candidate_count")) != len(episodes):
        blocks.append("episode_candidate_count_mismatch")
    if _safe_int(semantics.get("context_action_semantic_record_count")) != len(records):
        blocks.append("semantic_record_count_mismatch")

    if episode.get("status") == "FAIL_CLOSED":
        blocks.append("episode_upstream_fail_closed")
    elif episode.get("status") == "REVIEW_REQUIRED":
        reviews.append("episode_upstream_review_required")
    if semantics.get("status") == "FAIL_CLOSED":
        blocks.append("semantic_upstream_fail_closed")
    elif semantics.get("status") == "REVIEW_REQUIRED":
        reviews.append("semantic_upstream_review_required")

    return sorted(set(blocks)), sorted(set(reviews))


def _fail_payload(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "EPISODE_FEATURE_INPUT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "episode_feature_vectors": [],
        "episode_feature_vector_count": 0,
        "feature_assignment_complete": False,
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "support_rows_add_action_volume": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "physical_action_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def build_episode_feature_vectors(
    episode: dict[str, Any],
    semantics: dict[str, Any],
) -> dict[str, Any]:
    blocks, reviews = _validate_inputs(episode, semantics)
    episodes = episode.get("episode_candidates") if isinstance(episode.get("episode_candidates"), list) else []
    semantic_rows = semantics.get("context_action_semantic_records") if isinstance(semantics.get("context_action_semantic_records"), list) else []

    semantic_by_context: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(semantic_rows):
        if not isinstance(row, dict):
            blocks.append(f"semantic_record_invalid:{index}")
            continue
        context_id = _clean(row.get("context_id"))
        if not context_id:
            blocks.append(f"semantic_context_id_missing:{index}")
            continue
        if context_id in semantic_by_context:
            blocks.append(f"duplicate_semantic_context_id:{context_id}")
        semantic_by_context[context_id] = row

    seen_episode_ids: set[str] = set()
    seen_episode_contexts: set[str] = set()
    cards: list[dict[str, Any]] = []

    for index, ep in enumerate(episodes):
        if not isinstance(ep, dict):
            blocks.append(f"episode_record_invalid:{index}")
            continue
        episode_id = _clean(ep.get("episode_candidate_id"))
        if not episode_id:
            blocks.append(f"episode_id_missing:{index}")
            continue
        if episode_id in seen_episode_ids:
            blocks.append(f"duplicate_episode_id:{episode_id}")
        seen_episode_ids.add(episode_id)

        context_refs = ep.get("context_refs")
        if not isinstance(context_refs, list) or not context_refs:
            blocks.append(f"episode_context_refs_empty:{episode_id}")
            continue

        rows: list[dict[str, Any]] = []
        for raw_context_id in context_refs:
            context_id = _clean(raw_context_id)
            if context_id in seen_episode_contexts:
                blocks.append(f"context_assigned_to_multiple_episode_features:{context_id}")
            seen_episode_contexts.add(context_id)
            row = semantic_by_context.get(context_id)
            if row is None:
                blocks.append(f"episode_semantic_context_missing:{episode_id}:{context_id}")
                continue
            rows.append(row)

        eligible = [row for row in rows if row.get("action_occurrence_eligible") is True]
        support = [row for row in rows if row.get("action_occurrence_eligible") is not True]
        recognized_support = [row for row in support if row.get("non_action_context_or_reference") is True]
        review_limited_or_other = [row for row in support if row.get("non_action_context_or_reference") is not True]
        unresolved = [
            row
            for row in support
            if row.get("provider_semantics_review_status") != "REVIEWED_CANDIDATE"
            or row.get("provider_semantics_mapping_status") in REVIEW_MAPPING_STATUSES
        ]

        family_counts = Counter(_clean(row.get("provider_action_family_candidate")) or "UNKNOWN" for row in eligible)

        known_team_rows = [
            row for row in eligible
            if _clean(row.get("context_team_candidate")).casefold() not in UNKNOWN_TEAM_VALUES
        ]
        team_counts = Counter(_clean(row.get("context_team_candidate")) for row in known_team_rows)
        unknown_team_count = len(eligible) - len(known_team_rows)

        known_zone_rows = [
            row for row in eligible
            if _clean(row.get("context_zone_candidate")) not in UNKNOWN_ZONE_VALUES
        ]
        zone_counts = Counter(_clean(row.get("context_zone_candidate")) for row in known_zone_rows)
        unknown_zone_count = len(eligible) - len(known_zone_rows)

        known_channel_rows = [
            row for row in eligible
            if _clean(row.get("context_channel_candidate")) not in UNKNOWN_CHANNEL_VALUES
        ]
        channel_counts = Counter(_clean(row.get("context_channel_candidate")) for row in known_channel_rows)
        unknown_channel_count = len(eligible) - len(known_channel_rows)

        duration = _safe_float(ep.get("duration_candidate_seconds"))
        duration = duration if duration is not None and duration >= 0 else 0.0
        if duration > 0:
            density_status = "AVAILABLE"
            density = round(len(eligible) * 60.0 / duration, 6)
            density_not_applicable_reason = None
        else:
            density_status = "NOT_APPLICABLE_ZERO_DURATION"
            density = None
            density_not_applicable_reason = "POINT_EPISODE_HAS_NO_POSITIVE_DURATION"

        expected_family_counts = {
            str(key): _safe_int(value)
            for key, value in (ep.get("action_family_distribution") or {}).items()
        }
        actual_family_counts = dict(sorted(family_counts.items()))
        if _safe_int(ep.get("action_occurrence_eligible_count")) != len(eligible):
            blocks.append(f"episode_eligible_action_count_mismatch:{episode_id}")
        if _safe_int(ep.get("support_only_context_count")) != len(support):
            blocks.append(f"episode_support_context_count_mismatch:{episode_id}")
        if expected_family_counts != actual_family_counts:
            blocks.append(f"episode_action_family_distribution_mismatch:{episode_id}")

        review_debt_count = _safe_int(ep.get("review_debt_count"))
        missing_lenses = sorted({_clean(value) for value in (ep.get("missing_lenses") or []) if _clean(value)})
        not_applicable_features = []
        if duration <= 0:
            not_applicable_features.append("eligible_visible_action_candidate_density_per_minute")

        has_review = bool(review_debt_count or unresolved or missing_lenses)
        if duration <= 0 and has_review:
            readiness = "FEATURE_READY_POINT_EPISODE_WITH_REVIEW_DEBT"
        elif duration <= 0:
            readiness = "FEATURE_READY_POINT_EPISODE"
        elif has_review:
            readiness = "FEATURE_READY_WITH_REVIEW_DEBT"
        else:
            readiness = "FEATURE_READY"

        cards.append({
            "episode_feature_vector_id": f"efv:{episode_id}",
            "episode_candidate_id": episode_id,
            "feature_readiness": readiness,
            "period_candidate": ep.get("period_candidate"),
            "start_second_candidate": ep.get("start_second_candidate"),
            "end_second_candidate": ep.get("end_second_candidate"),
            "start_minute_candidate": ep.get("start_minute_candidate"),
            "end_minute_candidate": ep.get("end_minute_candidate"),
            "duration_seconds_candidate": duration,
            "time_layer_count": len(ep.get("time_layer_refs") or []),
            "same_time_unordered_layer_count": len(ep.get("same_time_unordered_refs") or []),
            "eligible_action_candidate_count": len(eligible),
            "support_only_context_count": len(support),
            "recognized_non_action_support_count": len(recognized_support),
            "review_limited_or_other_noneligible_count": len(review_limited_or_other),
            "unresolved_semantics_context_count": len(unresolved),
            "action_family_counts": actual_family_counts,
            "action_family_share_denominator": len(eligible),
            "action_family_shares": _shares(family_counts, len(eligible)),
            "visible_action_family_diversity_count": len(family_counts),
            "eligible_action_count_by_team_candidate": dict(sorted(team_counts.items())),
            "team_share_denominator_known_team_eligible_actions": len(known_team_rows),
            "unknown_team_eligible_action_count": unknown_team_count,
            "eligible_action_share_by_team_candidate": _shares(team_counts, len(known_team_rows)),
            "eligible_action_zone_counts": dict(sorted(zone_counts.items())),
            "zone_share_denominator_known_zone_eligible_actions": len(known_zone_rows),
            "unknown_zone_eligible_action_count": unknown_zone_count,
            "eligible_action_zone_shares": _shares(zone_counts, len(known_zone_rows)),
            "eligible_action_channel_counts": dict(sorted(channel_counts.items())),
            "channel_share_denominator_known_channel_eligible_actions": len(known_channel_rows),
            "unknown_channel_eligible_action_count": unknown_channel_count,
            "eligible_action_channel_shares": _shares(channel_counts, len(known_channel_rows)),
            "shot_candidate_count": family_counts.get("SHOT", 0),
            "restart_candidate_count": family_counts.get("RESTART", 0),
            "turnover_candidate_count": family_counts.get("TURNOVER", 0),
            "recovery_candidate_count": family_counts.get("RECOVERY", 0),
            "goalkeeper_action_candidate_count": family_counts.get("GOALKEEPER_ACTION", 0),
            "eligible_visible_action_candidate_density_per_minute": density,
            "density_feature_status": density_status,
            "density_not_applicable_reason": density_not_applicable_reason,
            "review_debt_count": review_debt_count,
            "missing_lenses": missing_lenses,
            "not_applicable_features": not_applicable_features,
            "context_refs": list(context_refs),
            "action_volume_basis": ACTION_VOLUME_BASIS,
            "support_rows_add_action_volume": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "density_is_physical_intensity_truth": False,
            "density_is_tempo_truth": False,
            "team_share_is_possession_or_control_truth": False,
            "space_share_is_territorial_control_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        return _fail_payload(blocks, reviews)

    total_eligible = sum(card["eligible_action_candidate_count"] for card in cards)
    total_family_counts: Counter[str] = Counter()
    for card in cards:
        total_family_counts.update(card["action_family_counts"])

    expected_total_eligible = _safe_int(semantics.get("action_occurrence_eligible_count"))
    expected_total_family_counts = {
        str(key): _safe_int(value)
        for key, value in (semantics.get("eligible_action_family_candidate_counts") or {}).items()
    }
    actual_total_family_counts = dict(sorted(total_family_counts.items()))

    if len(cards) != len(episodes):
        blocks.append("episode_feature_vector_assignment_count_mismatch")
    if total_eligible != expected_total_eligible:
        blocks.append("episode_feature_eligible_action_reconciliation_mismatch")
    if actual_total_family_counts != expected_total_family_counts:
        blocks.append("episode_feature_action_family_reconciliation_mismatch")

    blocks = sorted(set(blocks))
    if blocks:
        return _fail_payload(blocks, reviews)

    point_count = sum(card["duration_seconds_candidate"] == 0 for card in cards)
    review_card_count = sum("REVIEW_DEBT" in card["feature_readiness"] for card in cards)
    density_available_count = sum(card["density_feature_status"] == "AVAILABLE" for card in cards)
    density_na_count = sum(card["density_feature_status"] == "NOT_APPLICABLE_ZERO_DURATION" for card in cards)

    if review_card_count:
        reviews.append("episode_feature_review_debt_visible")
    if point_count:
        reviews.append("point_episode_density_not_applicable_visible")
    reviews = sorted(set(reviews))

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "EPISODE_FEATURE_VECTORS_BUILT",
        "claim_ceiling": CLAIM_CEILING,
        "episode_feature_vectors": cards,
        "episode_feature_vector_count": len(cards),
        "feature_assignment_complete": len(cards) == len(episodes),
        "episode_candidate_count": len(episodes),
        "total_eligible_action_candidate_count": total_eligible,
        "total_support_only_context_count": sum(card["support_only_context_count"] for card in cards),
        "total_recognized_non_action_support_count": sum(card["recognized_non_action_support_count"] for card in cards),
        "total_review_limited_or_other_noneligible_count": sum(card["review_limited_or_other_noneligible_count"] for card in cards),
        "total_unresolved_semantics_context_count": sum(card["unresolved_semantics_context_count"] for card in cards),
        "eligible_action_family_candidate_counts": actual_total_family_counts,
        "point_episode_count": point_count,
        "density_available_episode_count": density_available_count,
        "density_not_applicable_zero_duration_count": density_na_count,
        "review_debt_feature_vector_count": review_card_count,
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "support_rows_add_action_volume": False,
        "feature_values_are_episode_descriptive_candidates_only": True,
        "hard_block_hits": [],
        "review_hits": reviews,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "physical_action_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def _summary_text(report: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA EPISODE FEATURE VECTOR LITE V1",
        "===================================",
        f"status={report.get('status')}",
        f"episode_feature_vector_count={report.get('episode_feature_vector_count')}",
        f"total_eligible_action_candidate_count={report.get('total_eligible_action_candidate_count')}",
        f"point_episode_count={report.get('point_episode_count')}",
        f"density_not_applicable_zero_duration_count={report.get('density_not_applicable_zero_duration_count')}",
        f"hard_block_hits={report.get('hard_block_hits')}",
        f"review_hits={report.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "rhythm_truth=false",
        "production_release=false",
        "",
    ])


def _analyst_text(report: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — EPISODE FEATURE CARDS",
        f"Match review segments with feature cards: {report.get('episode_feature_vector_count', 0)}",
        f"Eligible action candidates distributed across cards: {report.get('total_eligible_action_candidate_count', 0)}",
        f"Point-like episodes with density N/A: {report.get('density_not_applicable_zero_duration_count', 0)}",
        "",
        "Feature card sample:",
    ]
    for card in (report.get("episode_feature_vectors") or [])[:12]:
        lines.append(
            "- "
            f"{card.get('start_minute_candidate')}–{card.get('end_minute_candidate')} min | "
            f"eligible={card.get('eligible_action_candidate_count')} | "
            f"families={card.get('action_family_counts')} | "
            f"density={card.get('eligible_visible_action_candidate_density_per_minute')} | "
            f"readiness={card.get('feature_readiness')}"
        )
    lines.extend([
        "",
        "Safe meaning: each card describes the visible eligible-action composition of one analyst navigation episode.",
        "Team shares are not possession/control truth; spatial shares are not territorial-control truth; density is not physical intensity, momentum or tempo truth.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    episode = _load_json(source / "analyst_episode_locator_lite_v1.json")
    semantics = _load_json(source / "context_action_semantics_rebind_lite_v1.json")
    report = build_episode_feature_vectors(episode, semantics)
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
    }
    (output / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / OUTPUT_TXT).write_text(_summary_text(report), encoding="utf-8")
    (output / ANALYST_TXT).write_text(_analyst_text(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Episode Feature Vector Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "episode_feature_vector_count": report.get("episode_feature_vector_count"),
        "total_eligible_action_candidate_count": report.get("total_eligible_action_candidate_count"),
        "density_not_applicable_zero_duration_count": report.get("density_not_applicable_zero_duration_count"),
        "hard_block_hits": report.get("hard_block_hits"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "production_release": report.get("production_release"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
