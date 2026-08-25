from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "temporal_episode_signature_lite_v1"
FEATURE_MODULE_ID = "episode_feature_vector_lite_v1"
CLAIM_CEILING = "TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY"
OUTPUT_JSON = "temporal_episode_signature_lite_v1.json"
OUTPUT_TXT = "temporal_episode_signature_lite_v1.txt"
ANALYST_TXT = "temporal_episode_signature_analyst_audit_v1.txt"
ACTION_VOLUME_BASIS = "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY"
EPS = 1e-6


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


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _dict_float(payload: Any) -> dict[str, float]:
    if not isinstance(payload, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in payload.items():
        number = _safe_float(value)
        if number is not None:
            out[str(key)] = number
    return dict(sorted(out.items()))


def _dict_int(payload: Any) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    return dict(sorted((str(key), _safe_int(value)) for key, value in payload.items()))


def _rate(count: int, duration_seconds: float) -> float | None:
    if duration_seconds <= 0:
        return None
    return round(count * 60.0 / duration_seconds, 6)


def _rate_map(counts: dict[str, int], duration_seconds: float) -> dict[str, float]:
    if duration_seconds <= 0:
        return {}
    return {key: round(value * 60.0 / duration_seconds, 6) for key, value in sorted(counts.items())}


def _delta_map(current: dict[str, float], previous: dict[str, float]) -> dict[str, float]:
    keys = sorted(set(current) | set(previous))
    return {key: round(current.get(key, 0.0) - previous.get(key, 0.0), 6) for key in keys}


def _total_variation(current: dict[str, float], previous: dict[str, float]) -> float:
    keys = set(current) | set(previous)
    return round(0.5 * sum(abs(current.get(key, 0.0) - previous.get(key, 0.0)) for key in keys), 6)


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
        raise ValueError(f"temporal_episode_input_unreadable:{source.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"temporal_episode_input_malformed:{source.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"temporal_episode_input_not_object:{source.name}")
    return payload


def _fail_payload(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "TEMPORAL_EPISODE_INPUT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "temporal_episode_signatures": [],
        "temporal_episode_signature_count": 0,
        "temporal_assignment_complete": False,
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "temporal_totals_add_action_volume": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "momentum_truth": False,
        "physical_intensity_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def _validate_feature_input(feature: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    blocks: list[str] = []
    reviews: list[str] = []

    if feature.get("module_id") != FEATURE_MODULE_ID:
        blocks.append("episode_feature_module_id_mismatch")
    if feature.get("status") == "FAIL_CLOSED":
        blocks.append("episode_feature_upstream_fail_closed")
    elif feature.get("status") == "REVIEW_REQUIRED":
        reviews.append("episode_feature_upstream_review_required")

    if feature.get("feature_assignment_complete") is not True:
        blocks.append("episode_feature_assignment_incomplete")
    if feature.get("action_volume_basis") != ACTION_VOLUME_BASIS:
        blocks.append("episode_feature_action_volume_basis_mismatch")
    if feature.get("support_rows_add_action_volume") is not False:
        blocks.append("episode_feature_support_volume_policy_breached")
    if feature.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("episode_feature_same_time_policy_breached")
    if feature.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("episode_feature_source_row_order_policy_breached")
    if feature.get("hard_block_hits"):
        blocks.append("episode_feature_upstream_hard_block_visible")
    if feature.get("canonical_event_count") != "UNKNOWN":
        blocks.append("episode_feature_canonical_event_count_claimed")
    if feature.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("episode_feature_true_action_count_claimed")
    if feature.get("production_release") is True:
        blocks.append("episode_feature_production_release_claimed")

    cards = feature.get("episode_feature_vectors")
    if not isinstance(cards, list) or not cards:
        blocks.append("episode_feature_vectors_empty_or_invalid")
        cards = []
    if _safe_int(feature.get("episode_feature_vector_count")) != len(cards):
        blocks.append("episode_feature_vector_count_mismatch")

    seen_ids: set[str] = set()
    total_eligible = 0
    family_totals: Counter[str] = Counter()
    point_count = 0

    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            blocks.append(f"episode_feature_card_invalid:{index}")
            continue
        episode_id = _clean(card.get("episode_candidate_id"))
        if not episode_id:
            blocks.append(f"episode_feature_episode_id_missing:{index}")
        elif episode_id in seen_ids:
            blocks.append(f"episode_feature_duplicate_episode_id:{episode_id}")
        seen_ids.add(episode_id)

        duration = _safe_float(card.get("duration_seconds_candidate"))
        if duration is None or duration < 0:
            blocks.append(f"episode_feature_duration_invalid:{episode_id or index}")
            duration = 0.0
        eligible = _safe_int(card.get("eligible_action_candidate_count"))
        if eligible < 0:
            blocks.append(f"episode_feature_eligible_count_invalid:{episode_id or index}")
        total_eligible += max(eligible, 0)

        family_counts = _dict_int(card.get("action_family_counts"))
        if sum(family_counts.values()) != eligible:
            blocks.append(f"episode_feature_family_denominator_mismatch:{episode_id or index}")
        family_totals.update(family_counts)

        expected_density = _rate(eligible, duration)
        actual_density = _safe_float(card.get("eligible_visible_action_candidate_density_per_minute"))
        density_status = _clean(card.get("density_feature_status"))
        if duration > 0:
            if density_status != "AVAILABLE" or actual_density is None or expected_density is None or abs(actual_density - expected_density) > EPS:
                blocks.append(f"episode_feature_density_reconciliation_mismatch:{episode_id or index}")
        else:
            point_count += 1
            if density_status != "NOT_APPLICABLE_ZERO_DURATION" or actual_density is not None:
                blocks.append(f"episode_feature_zero_duration_density_policy_breached:{episode_id or index}")

        if card.get("same_timestamp_internal_ordering_allowed") is not False:
            blocks.append(f"episode_feature_card_same_time_policy_breached:{episode_id or index}")
        if card.get("source_row_order_is_temporal_truth") is not False:
            blocks.append(f"episode_feature_card_source_row_order_policy_breached:{episode_id or index}")

    if total_eligible != _safe_int(feature.get("total_eligible_action_candidate_count")):
        blocks.append("episode_feature_total_eligible_reconciliation_mismatch")
    if dict(sorted(family_totals.items())) != _dict_int(feature.get("eligible_action_family_candidate_counts")):
        blocks.append("episode_feature_total_family_reconciliation_mismatch")
    if point_count != _safe_int(feature.get("point_episode_count")):
        blocks.append("episode_feature_point_episode_count_mismatch")

    return sorted(set(blocks)), sorted(set(reviews)), cards


def _predecessor_map(cards: list[dict[str, Any]]) -> tuple[dict[str, str | None], set[str], list[str]]:
    groups: dict[str, list[tuple[float, str]]] = defaultdict(list)
    reviews: list[str] = []
    for card in cards:
        episode_id = _clean(card.get("episode_candidate_id"))
        period = _clean(card.get("period_candidate")) or "UNKNOWN_PERIOD"
        start = _safe_float(card.get("start_second_candidate"))
        if start is None:
            start = _safe_float(card.get("start_minute_candidate"))
            start = None if start is None else start * 60.0
        if start is None:
            reviews.append(f"episode_start_time_missing:{episode_id}")
            continue
        groups[period].append((start, episode_id))

    predecessor: dict[str, str | None] = {}
    indeterminate: set[str] = set()
    for period, rows in groups.items():
        buckets: dict[float, list[str]] = defaultdict(list)
        for start, episode_id in rows:
            buckets[start].append(episode_id)
        starts = sorted(buckets)
        previous_singleton: str | None = None
        for start in starts:
            ids = sorted(buckets[start])
            if len(ids) > 1:
                indeterminate.update(ids)
                reviews.append(f"same_start_episode_order_indeterminate:{period}:{start}")
                previous_singleton = None
                for episode_id in ids:
                    predecessor[episode_id] = None
                continue
            episode_id = ids[0]
            predecessor[episode_id] = previous_singleton
            previous_singleton = episode_id
    return predecessor, indeterminate, reviews


def build_temporal_episode_signatures(feature: dict[str, Any]) -> dict[str, Any]:
    blocks, reviews, cards = _validate_feature_input(feature)
    if blocks:
        return _fail_payload(blocks, reviews)

    by_id = {_clean(card.get("episode_candidate_id")): card for card in cards}
    predecessor, indeterminate, order_reviews = _predecessor_map(cards)
    reviews.extend(order_reviews)

    signatures: list[dict[str, Any]] = []
    comparison_available_count = 0
    no_prior_count = 0
    zero_duration_na_count = 0
    order_indeterminate_count = 0

    for card in cards:
        episode_id = _clean(card.get("episode_candidate_id"))
        period = _clean(card.get("period_candidate")) or "UNKNOWN_PERIOD"
        duration = _safe_float(card.get("duration_seconds_candidate")) or 0.0
        eligible = _safe_int(card.get("eligible_action_candidate_count"))
        family_counts = _dict_int(card.get("action_family_counts"))
        family_rates = _rate_map(family_counts, duration)
        action_rate = _rate(eligible, duration)

        upstream_density = _safe_float(card.get("eligible_visible_action_candidate_density_per_minute"))
        if duration > 0 and (upstream_density is None or action_rate is None or abs(upstream_density - action_rate) > EPS):
            blocks.append(f"temporal_upstream_density_drift:{episode_id}")

        previous_id = predecessor.get(episode_id)
        previous = by_id.get(previous_id or "") if previous_id else None
        comparison_status = "AVAILABLE"
        rate_delta: float | None = None
        family_rate_delta: dict[str, float] = {}
        composition_shift: float | None = None
        team_delta: dict[str, float] = {}
        team_shift: float | None = None
        zone_delta: dict[str, float] = {}
        zone_shift: float | None = None
        channel_delta: dict[str, float] = {}
        channel_shift: float | None = None

        if episode_id in indeterminate:
            comparison_status = "ORDER_INDETERMINATE_SAME_START"
            order_indeterminate_count += 1
        elif previous is None:
            comparison_status = "NO_PRIOR_EPISODE_IN_PERIOD"
            no_prior_count += 1
        else:
            previous_period = _clean(previous.get("period_candidate")) or "UNKNOWN_PERIOD"
            if previous_period != period:
                blocks.append(f"cross_period_temporal_comparison_attempt:{episode_id}")
                comparison_status = "CROSS_PERIOD_BLOCKED"
            else:
                previous_duration = _safe_float(previous.get("duration_seconds_candidate")) or 0.0
                previous_eligible = _safe_int(previous.get("eligible_action_candidate_count"))
                previous_family_counts = _dict_int(previous.get("action_family_counts"))
                previous_action_rate = _rate(previous_eligible, previous_duration)
                previous_family_rates = _rate_map(previous_family_counts, previous_duration)

                if duration <= 0:
                    comparison_status = "CURRENT_ZERO_DURATION_RATE_NA"
                    zero_duration_na_count += 1
                elif previous_duration <= 0:
                    comparison_status = "PREVIOUS_ZERO_DURATION_RATE_NA"
                    zero_duration_na_count += 1
                else:
                    comparison_available_count += 1
                    rate_delta = _round((action_rate or 0.0) - (previous_action_rate or 0.0))
                    family_rate_delta = _delta_map(family_rates, previous_family_rates)

                    current_family_shares = _dict_float(card.get("action_family_shares"))
                    previous_family_shares = _dict_float(previous.get("action_family_shares"))
                    if _safe_int(card.get("action_family_share_denominator")) > 0 and _safe_int(previous.get("action_family_share_denominator")) > 0:
                        composition_shift = _total_variation(current_family_shares, previous_family_shares)

                    current_team = _dict_float(card.get("eligible_action_share_by_team_candidate"))
                    previous_team = _dict_float(previous.get("eligible_action_share_by_team_candidate"))
                    if _safe_int(card.get("team_share_denominator_known_team_eligible_actions")) > 0 and _safe_int(previous.get("team_share_denominator_known_team_eligible_actions")) > 0:
                        team_delta = _delta_map(current_team, previous_team)
                        team_shift = _total_variation(current_team, previous_team)

                    current_zone = _dict_float(card.get("eligible_action_zone_shares"))
                    previous_zone = _dict_float(previous.get("eligible_action_zone_shares"))
                    if _safe_int(card.get("zone_share_denominator_known_zone_eligible_actions")) > 0 and _safe_int(previous.get("zone_share_denominator_known_zone_eligible_actions")) > 0:
                        zone_delta = _delta_map(current_zone, previous_zone)
                        zone_shift = _total_variation(current_zone, previous_zone)

                    current_channel = _dict_float(card.get("eligible_action_channel_shares"))
                    previous_channel = _dict_float(previous.get("eligible_action_channel_shares"))
                    if _safe_int(card.get("channel_share_denominator_known_channel_eligible_actions")) > 0 and _safe_int(previous.get("channel_share_denominator_known_channel_eligible_actions")) > 0:
                        channel_delta = _delta_map(current_channel, previous_channel)
                        channel_shift = _total_variation(current_channel, previous_channel)

        current_unresolved = _safe_int(card.get("unresolved_semantics_context_count"))
        missing_lenses = sorted({_clean(value) for value in (card.get("missing_lenses") or []) if _clean(value)})
        card_reviews: list[str] = []
        if current_unresolved:
            card_reviews.append("unresolved_semantics_visible")
        if missing_lenses:
            card_reviews.append("missing_lenses_visible")
        if comparison_status != "AVAILABLE":
            card_reviews.append(f"comparison_status:{comparison_status}")

        signatures.append({
            "temporal_episode_signature_id": f"tes:{episode_id}",
            "episode_feature_vector_id": card.get("episode_feature_vector_id"),
            "episode_candidate_id": episode_id,
            "period_candidate": card.get("period_candidate"),
            "start_second_candidate": card.get("start_second_candidate"),
            "end_second_candidate": card.get("end_second_candidate"),
            "start_minute_candidate": card.get("start_minute_candidate"),
            "end_minute_candidate": card.get("end_minute_candidate"),
            "duration_seconds_candidate": duration,
            "eligible_action_candidate_count": eligible,
            "eligible_action_candidate_rate_per_minute": action_rate,
            "action_family_candidate_rates_per_minute": family_rates,
            "comparison_episode_candidate_id": previous_id,
            "comparison_status": comparison_status,
            "same_period_required": True,
            "eligible_action_rate_delta_per_minute": rate_delta,
            "action_family_rate_delta_per_minute": family_rate_delta,
            "shot_rate_delta_per_minute": family_rate_delta.get("SHOT") if family_rate_delta else None,
            "turnover_rate_delta_per_minute": family_rate_delta.get("TURNOVER") if family_rate_delta else None,
            "recovery_rate_delta_per_minute": family_rate_delta.get("RECOVERY") if family_rate_delta else None,
            "restart_rate_delta_per_minute": family_rate_delta.get("RESTART") if family_rate_delta else None,
            "action_family_composition_shift_candidate": composition_shift,
            "eligible_action_share_by_team_candidate_delta": team_delta,
            "team_visible_share_shift_candidate": team_shift,
            "zone_share_delta_candidate": zone_delta,
            "zone_share_shift_candidate": zone_shift,
            "channel_share_delta_candidate": channel_delta,
            "channel_share_shift_candidate": channel_shift,
            "current_unresolved_semantics_context_count": current_unresolved,
            "missing_lenses": missing_lenses,
            "threshold_sensitivity_state": "NOT_TESTED_V1",
            "lineage_integrity_state": "UPSTREAM_EPISODE_FEATURE_RECONCILED",
            "falsifier_readiness": ["SEGMENT", "THRESHOLD", "LINEAGE", "EVIDENCE", "ALTERNATIVE", "CONTRADICTION"],
            "review_hits": card_reviews,
            "zero_duration_guard": True,
            "action_volume_basis": ACTION_VOLUME_BASIS,
            "temporal_totals_add_action_volume": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "rate_is_physical_intensity_truth": False,
            "rate_is_tempo_truth": False,
            "composition_shift_is_phase_or_regime_truth": False,
            "team_share_change_is_possession_control_or_dominance_truth": False,
            "space_shift_is_pitch_control_or_occupation_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        return _fail_payload(sorted(set(blocks)), reviews)

    if len(signatures) != len(cards):
        blocks.append("temporal_episode_signature_assignment_count_mismatch")
    signature_total_eligible = sum(_safe_int(row.get("eligible_action_candidate_count")) for row in signatures)
    if signature_total_eligible != _safe_int(feature.get("total_eligible_action_candidate_count")):
        blocks.append("temporal_signature_action_volume_reconciliation_mismatch")
    if blocks:
        return _fail_payload(sorted(set(blocks)), reviews)

    unresolved_total = sum(_safe_int(row.get("current_unresolved_semantics_context_count")) for row in signatures)
    if unresolved_total:
        reviews.append("unresolved_semantics_propagated")
    if zero_duration_na_count:
        reviews.append("zero_duration_temporal_rate_na_visible")
    if order_indeterminate_count:
        reviews.append("same_start_episode_order_indeterminate_visible")
    reviews = sorted(set(reviews))

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "TEMPORAL_EPISODE_SIGNATURES_BUILT",
        "claim_ceiling": CLAIM_CEILING,
        "temporal_episode_signatures": signatures,
        "temporal_episode_signature_count": len(signatures),
        "temporal_assignment_complete": len(signatures) == len(cards),
        "input_episode_feature_vector_count": len(cards),
        "input_total_eligible_action_candidate_count": _safe_int(feature.get("total_eligible_action_candidate_count")),
        "input_eligible_action_family_candidate_counts": _dict_int(feature.get("eligible_action_family_candidate_counts")),
        "comparison_available_count": comparison_available_count,
        "no_prior_episode_in_period_count": no_prior_count,
        "zero_duration_temporal_rate_na_count": zero_duration_na_count,
        "same_start_order_indeterminate_count": order_indeterminate_count,
        "unresolved_semantics_context_count": unresolved_total,
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "temporal_totals_add_action_volume": False,
        "spectral_methods_applied": False,
        "recurrence_truth_applied": False,
        "hard_block_hits": [],
        "review_hits": reviews,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "momentum_truth": False,
        "physical_intensity_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def _summary_text(report: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA TEMPORAL EPISODE SIGNATURE LITE V1",
        "========================================",
        f"status={report.get('status')}",
        f"temporal_episode_signature_count={report.get('temporal_episode_signature_count')}",
        f"comparison_available_count={report.get('comparison_available_count')}",
        f"zero_duration_temporal_rate_na_count={report.get('zero_duration_temporal_rate_na_count')}",
        f"same_start_order_indeterminate_count={report.get('same_start_order_indeterminate_count')}",
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
    rows = [row for row in (report.get("temporal_episode_signatures") or []) if row.get("comparison_status") == "AVAILABLE"]
    rows.sort(key=lambda row: (
        -float(row.get("action_family_composition_shift_candidate") or 0.0),
        -abs(float(row.get("eligible_action_rate_delta_per_minute") or 0.0)),
        float(row.get("start_second_candidate") or 0.0),
    ))
    lines = [
        "HPFA ANALYST AUDIT — TEMPORAL EPISODE CHANGE CANDIDATES",
        f"Episode signatures: {report.get('temporal_episode_signature_count', 0)}",
        f"Safe adjacent comparisons: {report.get('comparison_available_count', 0)}",
        "",
        "Largest visible composition changes (candidate only):",
    ]
    for row in rows[:12]:
        lines.append(
            "- "
            f"{row.get('start_minute_candidate')}–{row.get('end_minute_candidate')} min | "
            f"vs={row.get('comparison_episode_candidate_id')} | "
            f"action_rate_delta={row.get('eligible_action_rate_delta_per_minute')} | "
            f"composition_shift={row.get('action_family_composition_shift_candidate')} | "
            f"shot_delta={row.get('shot_rate_delta_per_minute')} | "
            f"turnover_delta={row.get('turnover_rate_delta_per_minute')} | "
            f"recovery_delta={row.get('recovery_rate_delta_per_minute')}"
        )
    lines.extend([
        "",
        "Safe meaning: these are reversible episode-to-episode visible-action change candidates built from reviewed action-occurrence-eligible evidence.",
        "They are not tempo, momentum, physical intensity, possession, phase, dominance or tactical truth. Spectral and recurrence methods are not applied in V1.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    feature = _load_json(source / "episode_feature_vector_lite_v1.json")
    report = build_temporal_episode_signatures(feature)
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
    parser = argparse.ArgumentParser(description="HPFA Temporal Episode Signature Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "temporal_episode_signature_count": report.get("temporal_episode_signature_count"),
        "comparison_available_count": report.get("comparison_available_count"),
        "zero_duration_temporal_rate_na_count": report.get("zero_duration_temporal_rate_na_count"),
        "same_start_order_indeterminate_count": report.get("same_start_order_indeterminate_count"),
        "hard_block_hits": report.get("hard_block_hits"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "production_release": report.get("production_release"),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
