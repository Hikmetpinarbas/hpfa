from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "temporal_episode_signature_lite" / "src"
sys.path.insert(0, str(SRC))

from temporal_episode_signature import build_temporal_episode_signatures, validate_output_root


def _card(
    episode_id: str,
    *,
    period: str,
    start: float,
    duration: float,
    families: dict[str, int],
    team_shares: dict[str, float] | None = None,
    zone_shares: dict[str, float] | None = None,
    channel_shares: dict[str, float] | None = None,
    unresolved: int = 0,
) -> dict:
    eligible = sum(families.values())
    density = None if duration <= 0 else round(eligible * 60.0 / duration, 6)
    family_shares = {key: round(value / eligible, 6) for key, value in families.items()} if eligible else {}
    team_shares = team_shares or {"team_a": 1.0}
    zone_shares = zone_shares or {"MIDDLE_THIRD": 1.0}
    channel_shares = channel_shares or {"CENTRAL_CHANNEL": 1.0}
    return {
        "episode_feature_vector_id": f"efv:{episode_id}",
        "episode_candidate_id": episode_id,
        "feature_readiness": "FEATURE_READY_WITH_REVIEW_DEBT" if unresolved else "FEATURE_READY",
        "period_candidate": period,
        "start_second_candidate": start,
        "end_second_candidate": start + duration,
        "start_minute_candidate": round(start / 60.0, 3),
        "end_minute_candidate": round((start + duration) / 60.0, 3),
        "duration_seconds_candidate": duration,
        "eligible_action_candidate_count": eligible,
        "support_only_context_count": 1,
        "unresolved_semantics_context_count": unresolved,
        "action_family_counts": families,
        "action_family_share_denominator": eligible,
        "action_family_shares": family_shares,
        "team_share_denominator_known_team_eligible_actions": eligible,
        "eligible_action_share_by_team_candidate": team_shares,
        "zone_share_denominator_known_zone_eligible_actions": eligible,
        "eligible_action_zone_shares": zone_shares,
        "channel_share_denominator_known_channel_eligible_actions": eligible,
        "eligible_action_channel_shares": channel_shares,
        "eligible_visible_action_candidate_density_per_minute": density,
        "density_feature_status": "AVAILABLE" if duration > 0 else "NOT_APPLICABLE_ZERO_DURATION",
        "missing_lenses": [],
        "action_volume_basis": "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY",
        "support_rows_add_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
    }


def _payload() -> dict:
    cards = [
        _card(
            "ep_1",
            period="1",
            start=10.0,
            duration=60.0,
            families={"PASS": 1, "SHOT": 1},
            team_shares={"team_a": 1.0},
            zone_shares={"MIDDLE_THIRD": 1.0},
            channel_shares={"CENTRAL_CHANNEL": 1.0},
        ),
        _card(
            "ep_2",
            period="1",
            start=80.0,
            duration=60.0,
            families={"PASS": 1, "TURNOVER": 1},
            team_shares={"team_b": 1.0},
            zone_shares={"FINAL_THIRD": 1.0},
            channel_shares={"LEFT_CHANNEL": 1.0},
            unresolved=1,
        ),
    ]
    return {
        "module_id": "episode_feature_vector_lite_v1",
        "status": "REVIEW_REQUIRED",
        "episode_feature_vectors": cards,
        "episode_feature_vector_count": len(cards),
        "feature_assignment_complete": True,
        "total_eligible_action_candidate_count": 4,
        "eligible_action_family_candidate_counts": {"PASS": 2, "SHOT": 1, "TURNOVER": 1},
        "point_episode_count": 0,
        "action_volume_basis": "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY",
        "support_rows_add_action_volume": False,
        "hard_block_hits": [],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_builds_one_temporal_signature_per_episode_without_new_action_volume() -> None:
    result = build_temporal_episode_signatures(_payload())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["temporal_episode_signature_count"] == 2
    assert result["temporal_assignment_complete"] is True
    assert result["input_total_eligible_action_candidate_count"] == 4
    assert result["temporal_totals_add_action_volume"] is False
    assert result["hard_block_hits"] == []


def test_rate_and_delta_use_only_upstream_episode_feature_denominators() -> None:
    result = build_temporal_episode_signatures(_payload())
    first, second = result["temporal_episode_signatures"]
    assert first["eligible_action_candidate_rate_per_minute"] == 2.0
    assert first["comparison_status"] == "NO_PRIOR_EPISODE_IN_PERIOD"
    assert second["eligible_action_candidate_rate_per_minute"] == 2.0
    assert second["comparison_status"] == "AVAILABLE"
    assert second["eligible_action_rate_delta_per_minute"] == 0.0
    assert second["shot_rate_delta_per_minute"] == -1.0
    assert second["turnover_rate_delta_per_minute"] == 1.0


def test_composition_team_zone_and_channel_shift_are_transparent_candidates() -> None:
    result = build_temporal_episode_signatures(_payload())
    second = result["temporal_episode_signatures"][1]
    assert second["action_family_composition_shift_candidate"] == 0.5
    assert second["eligible_action_share_by_team_candidate_delta"] == {"team_a": -1.0, "team_b": 1.0}
    assert second["team_visible_share_shift_candidate"] == 1.0
    assert second["zone_share_delta_candidate"] == {"FINAL_THIRD": 1.0, "MIDDLE_THIRD": -1.0}
    assert second["zone_share_shift_candidate"] == 1.0
    assert second["channel_share_delta_candidate"] == {"CENTRAL_CHANNEL": -1.0, "LEFT_CHANNEL": 1.0}
    assert second["channel_share_shift_candidate"] == 1.0
    assert second["team_share_change_is_possession_control_or_dominance_truth"] is False
    assert second["space_shift_is_pitch_control_or_occupation_truth"] is False


def test_period_boundary_never_creates_cross_period_comparison() -> None:
    payload = _payload()
    third = _card("ep_3", period="2", start=2800.0, duration=60.0, families={"PASS": 1})
    payload["episode_feature_vectors"].append(third)
    payload["episode_feature_vector_count"] = 3
    payload["total_eligible_action_candidate_count"] = 5
    payload["eligible_action_family_candidate_counts"] = {"PASS": 3, "SHOT": 1, "TURNOVER": 1}
    result = build_temporal_episode_signatures(payload)
    third_out = result["temporal_episode_signatures"][2]
    assert third_out["comparison_episode_candidate_id"] is None
    assert third_out["comparison_status"] == "NO_PRIOR_EPISODE_IN_PERIOD"


def test_zero_duration_rate_and_adjacent_delta_are_not_applicable() -> None:
    payload = _payload()
    payload["episode_feature_vectors"][1] = _card(
        "ep_2", period="1", start=80.0, duration=0.0, families={"TURNOVER": 1}, unresolved=1
    )
    payload["total_eligible_action_candidate_count"] = 3
    payload["eligible_action_family_candidate_counts"] = {"PASS": 1, "SHOT": 1, "TURNOVER": 1}
    payload["point_episode_count"] = 1
    result = build_temporal_episode_signatures(payload)
    second = result["temporal_episode_signatures"][1]
    assert second["eligible_action_candidate_rate_per_minute"] is None
    assert second["comparison_status"] == "CURRENT_ZERO_DURATION_RATE_NA"
    assert second["eligible_action_rate_delta_per_minute"] is None
    assert result["zero_duration_temporal_rate_na_count"] == 1


def test_same_start_episode_candidates_are_not_artificially_ordered() -> None:
    payload = _payload()
    payload["episode_feature_vectors"][1]["start_second_candidate"] = 10.0
    payload["episode_feature_vectors"][1]["start_minute_candidate"] = round(10.0 / 60.0, 3)
    result = build_temporal_episode_signatures(payload)
    assert result["same_start_order_indeterminate_count"] == 2
    assert all(row["comparison_status"] == "ORDER_INDETERMINATE_SAME_START" for row in result["temporal_episode_signatures"])
    assert "same_start_episode_order_indeterminate_visible" in result["review_hits"]


def test_upstream_density_drift_fails_closed() -> None:
    payload = _payload()
    payload["episode_feature_vectors"][0]["eligible_visible_action_candidate_density_per_minute"] = 99.0
    result = build_temporal_episode_signatures(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert any("density_reconciliation_mismatch" in hit for hit in result["hard_block_hits"])


def test_upstream_action_family_total_drift_fails_closed() -> None:
    payload = _payload()
    payload["eligible_action_family_candidate_counts"] = {"PASS": 99}
    result = build_temporal_episode_signatures(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "episode_feature_total_family_reconciliation_mismatch" in result["hard_block_hits"]


def test_claim_and_method_locks_remain_closed() -> None:
    result = build_temporal_episode_signatures(_payload())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["phase_truth"] is False
    assert result["rhythm_truth"] is False
    assert result["momentum_truth"] is False
    assert result["physical_intensity_truth"] is False
    assert result["tactical_truth"] is False
    assert result["dominance_truth"] is False
    assert result["fatigue_truth"] is False
    assert result["spectral_methods_applied"] is False
    assert result["recurrence_truth_applied"] is False
    assert result["production_release"] is False


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/temporal")


def test_no_sample_match_identity_or_context_ordinal_leak() -> None:
    text = (SRC / "temporal_episode_signature.py").read_text(encoding="utf-8")
    forbidden = ["Fenerbahce", "Galatasaray", "Genclerbirligi", "15.08.2026", "Turkey", "World Cup"]
    assert not any(token in text for token in forbidden)
    assert "context_ordinal" not in text
