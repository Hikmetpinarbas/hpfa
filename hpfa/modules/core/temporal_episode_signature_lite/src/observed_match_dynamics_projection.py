from __future__ import annotations

from statistics import pstdev
from typing import Any

MODULE_ID = "observed_match_dynamics_projection_v1"
FEATURE_MODULE_ID = "episode_feature_vector_lite_v1"
TEMPORAL_MODULE_ID = "temporal_episode_signature_lite_v1"
CLAIM_CEILING = "OBSERVED_MATCH_DYNAMICS_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def build_observed_match_dynamics(
    feature_payload: dict[str, Any],
    temporal_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if feature_payload.get("module_id") != FEATURE_MODULE_ID:
        blocks.append("feature_module_id_mismatch")
    if temporal_payload.get("module_id") != TEMPORAL_MODULE_ID:
        blocks.append("temporal_module_id_mismatch")

    for name, payload in (("feature", feature_payload), ("temporal", temporal_payload)):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")

    cards = feature_payload.get("episode_feature_vectors") or []
    signatures = temporal_payload.get("temporal_episode_signatures") or []
    if not isinstance(cards, list) or not isinstance(signatures, list):
        blocks.append("dynamics_inputs_invalid")
        cards = []
        signatures = []

    sig_by_episode = {
        _clean(row.get("episode_candidate_id")): row
        for row in signatures
        if isinstance(row, dict) and _clean(row.get("episode_candidate_id"))
    }

    base_rows: list[dict[str, Any]] = []
    rates: list[float] = []
    for position, card in enumerate(cards):
        if not isinstance(card, dict):
            blocks.append(f"feature_card_invalid:{position}")
            continue
        episode_id = _clean(card.get("episode_candidate_id"))
        if not episode_id:
            blocks.append(f"feature_episode_id_missing:{position}")
            continue
        duration = _float(card.get("duration_seconds_candidate"))
        eligible = _int(card.get("eligible_action_candidate_count"))
        rate = None
        if duration is not None and duration > 0:
            rate = eligible * 60.0 / duration
            rates.append(rate)
        else:
            reviews.append(f"activity_rate_not_available:{episode_id}")

        base_rows.append({
            "episode_candidate_id": episode_id,
            "period_candidate": card.get("period_candidate"),
            "start_second_candidate": card.get("start_second_candidate"),
            "end_second_candidate": card.get("end_second_candidate"),
            "duration_seconds_candidate": duration,
            "eligible_action_candidate_count": eligible,
            "activity_rate_per_minute_candidate": None if rate is None else round(rate, 6),
            "shot_candidate_count": _int(card.get("shot_candidate_count")),
            "turnover_candidate_count": _int(card.get("turnover_candidate_count")),
            "recovery_candidate_count": _int(card.get("recovery_candidate_count")),
            "temporal_signature": sig_by_episode.get(episode_id),
        })

    p33 = _quantile(rates, 0.33)
    p66 = _quantile(rates, 0.66)
    p90 = _quantile(rates, 0.90)

    records: list[dict[str, Any]] = []
    prior_rate_by_period: dict[str, float] = {}
    deltas_for_volatility: list[float] = []

    for row in base_rows:
        rate = row["activity_rate_per_minute_candidate"]
        period = _clean(row.get("period_candidate")) or "UNKNOWN_PERIOD"
        temporal = row.get("temporal_signature") or {}
        comparison_status = _clean(temporal.get("comparison_status"))
        activity_regime = "RATE_NOT_AVAILABLE"
        if rate is not None and p33 is not None and p66 is not None:
            if rate < p33:
                activity_regime = "LOW_ACTIVITY_CANDIDATE"
            elif rate < p66:
                activity_regime = "MID_ACTIVITY_CANDIDATE"
            else:
                activity_regime = "HIGH_ACTIVITY_CANDIDATE"

        delta = None
        if comparison_status == "AVAILABLE" and rate is not None and period in prior_rate_by_period:
            delta = round(rate - prior_rate_by_period[period], 6)
            deltas_for_volatility.append(abs(delta))
        elif comparison_status not in {"", "NO_PRIOR_EPISODE_IN_PERIOD", "CURRENT_ZERO_DURATION_RATE_NA", "PREVIOUS_ZERO_DURATION_RATE_NA", "ORDER_INDETERMINATE_SAME_START"}:
            reviews.append(f"unhandled_temporal_comparison_state:{row['episode_candidate_id']}:{comparison_status}")

        if rate is not None and comparison_status != "ORDER_INDETERMINATE_SAME_START":
            prior_rate_by_period[period] = rate

        terminal_density_candidate = (
            row["shot_candidate_count"] + row["turnover_candidate_count"] + row["recovery_candidate_count"]
        )
        records.append({
            **row,
            "activity_regime_candidate": activity_regime,
            "episode_activity_rate_delta_candidate": delta,
            "terminal_turnover_recovery_activity_count_candidate": terminal_density_candidate,
            "high_activity_threshold_candidate": None if p66 is None else round(p66, 6),
            "extreme_activity_threshold_candidate": None if p90 is None else round(p90, 6),
            "tempo_truth": False,
            "momentum_truth": False,
            "control_truth": False,
            "rhythm_truth": False,
            "phase_rupture_truth": False,
            "physical_intensity_truth": False,
            "causal_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    volatility_scale = round(pstdev(deltas_for_volatility), 6) if len(deltas_for_volatility) >= 2 else None
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "observed_match_dynamics_candidates": records if not blocks else [],
        "observed_match_dynamics_candidate_count": 0 if blocks else len(records),
        "match_local_activity_thresholds": {
            "p33": None if p33 is None else round(p33, 6),
            "p66": None if p66 is None else round(p66, 6),
            "p90": None if p90 is None else round(p90, 6),
            "episode_rate_delta_volatility_scale_candidate": volatility_scale,
        },
        "donor_adaptation": {
            "hp_motor_step13_tempo_moments": "ADAPTED_AS_EPISODE_ACTIVITY_RATE_AND_MATCH_LOCAL_REGIME_CANDIDATES",
            "hp_engine_temporal_tempo_momentum": "REHABILITATED_WITHOUT_TEMPO_MOMENTUM_CONTROL_TRUTH",
            "source_row_order_used_as_chronology": False,
            "fixed_window_required": False,
            "episode_defined_windows_preferred": True,
        },
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "activity_regime_is_tempo_truth": False,
        "activity_delta_is_momentum_truth": False,
        "volatility_is_chaos_truth": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
