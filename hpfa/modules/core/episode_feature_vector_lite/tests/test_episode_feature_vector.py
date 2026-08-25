from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "episode_feature_vector_lite" / "src"
sys.path.insert(0, str(SRC))

from episode_feature_vector import build_episode_feature_vectors, validate_output_root


def _semantic(
    context_id: str,
    *,
    eligible: bool,
    family: str = "UNKNOWN",
    team: str = "team_a",
    zone: str = "MIDDLE_THIRD",
    channel: str = "CENTRAL_CHANNEL",
    non_action: bool = False,
    reviewed: bool = True,
) -> dict:
    return {
        "context_id": context_id,
        "row_nucleus_candidate_id": f"rn_{context_id}",
        "provider_action_family_candidate": family,
        "provider_semantic_role_candidate": "ACTION_ANCHOR" if eligible else "CONTEXT_INTERVAL",
        "provider_semantics_review_status": "REVIEWED_CANDIDATE" if reviewed else "REVIEW_REQUIRED",
        "provider_semantics_mapping_status": "EXACT_REVIEWED_CANDIDATE" if reviewed else "UNKNOWN_UNREVIEWED",
        "action_occurrence_eligible": eligible,
        "non_action_context_or_reference": non_action,
        "context_team_candidate": team,
        "context_zone_candidate": zone,
        "context_channel_candidate": channel,
    }


def _payloads() -> tuple[dict, dict]:
    records = [
        _semantic("c1", eligible=True, family="PASS"),
        _semantic("c2", eligible=True, family="SHOT"),
        _semantic("c3", eligible=False, family="PASS", non_action=True),
        _semantic("c4", eligible=True, family="TURNOVER", team="team_b", zone="UNKNOWN_ZONE", channel="UNKNOWN_CHANNEL"),
        _semantic("c5", eligible=False, non_action=False, reviewed=False),
    ]
    semantics = {
        "module_id": "context_action_semantics_rebind_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_action_semantic_records": records,
        "context_action_semantic_record_count": len(records),
        "context_semantic_assignment_complete": True,
        "reflection_inflation_prevented": True,
        "reference_participation_context_adds_action_volume": False,
        "review_limited_semantics_adds_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "action_occurrence_eligible_count": 3,
        "eligible_action_family_candidate_counts": {"PASS": 1, "SHOT": 1, "TURNOVER": 1},
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    episodes = [
        {
            "episode_candidate_id": "ep_1",
            "period_candidate": "1",
            "start_second_candidate": 10.0,
            "end_second_candidate": 70.0,
            "start_minute_candidate": 0.167,
            "end_minute_candidate": 1.167,
            "duration_candidate_seconds": 60.0,
            "time_layer_refs": ["l1", "l2"],
            "same_time_unordered_refs": ["l2"],
            "context_refs": ["c1", "c2", "c3"],
            "action_occurrence_eligible_count": 2,
            "support_only_context_count": 1,
            "action_family_distribution": {"PASS": 1, "SHOT": 1},
            "review_debt_count": 0,
            "missing_lenses": [],
        },
        {
            "episode_candidate_id": "ep_2",
            "period_candidate": "1",
            "start_second_candidate": 80.0,
            "end_second_candidate": 80.0,
            "start_minute_candidate": 1.333,
            "end_minute_candidate": 1.333,
            "duration_candidate_seconds": 0.0,
            "time_layer_refs": ["l3"],
            "same_time_unordered_refs": [],
            "context_refs": ["c4", "c5"],
            "action_occurrence_eligible_count": 1,
            "support_only_context_count": 1,
            "action_family_distribution": {"TURNOVER": 1},
            "review_debt_count": 0,
            "missing_lenses": [],
        },
    ]
    episode = {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "REVIEW_REQUIRED",
        "episode_candidates": episodes,
        "episode_candidate_count": len(episodes),
        "context_assignment_complete": True,
        "reflection_inflation_prevented": True,
        "action_volume_basis": "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY",
        "support_rows_add_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return episode, semantics


def test_builds_one_feature_card_per_episode_and_reconciles_action_volume() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["episode_feature_vector_count"] == 2
    assert result["feature_assignment_complete"] is True
    assert result["total_eligible_action_candidate_count"] == 3
    assert result["eligible_action_family_candidate_counts"] == {"PASS": 1, "SHOT": 1, "TURNOVER": 1}
    assert result["hard_block_hits"] == []


def test_support_context_never_adds_action_volume() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    first = result["episode_feature_vectors"][0]
    assert first["eligible_action_candidate_count"] == 2
    assert first["support_only_context_count"] == 1
    assert first["recognized_non_action_support_count"] == 1
    assert first["action_family_counts"] == {"PASS": 1, "SHOT": 1}
    assert first["support_rows_add_action_volume"] is False


def test_zero_duration_episode_keeps_card_but_density_is_not_applicable() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    second = result["episode_feature_vectors"][1]
    assert second["duration_seconds_candidate"] == 0.0
    assert second["density_feature_status"] == "NOT_APPLICABLE_ZERO_DURATION"
    assert second["eligible_visible_action_candidate_density_per_minute"] is None
    assert "eligible_visible_action_candidate_density_per_minute" in second["not_applicable_features"]
    assert result["density_not_applicable_zero_duration_count"] == 1


def test_density_uses_only_eligible_candidates_and_positive_duration() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    first = result["episode_feature_vectors"][0]
    assert first["eligible_visible_action_candidate_density_per_minute"] == 2.0
    assert first["density_feature_status"] == "AVAILABLE"
    assert first["density_is_physical_intensity_truth"] is False
    assert first["density_is_tempo_truth"] is False


def test_team_and_space_denominators_expose_unknowns_instead_of_hiding_them() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    second = result["episode_feature_vectors"][1]
    assert second["team_share_denominator_known_team_eligible_actions"] == 1
    assert second["eligible_action_share_by_team_candidate"] == {"team_b": 1.0}
    assert second["zone_share_denominator_known_zone_eligible_actions"] == 0
    assert second["unknown_zone_eligible_action_count"] == 1
    assert second["eligible_action_zone_shares"] == {}
    assert second["channel_share_denominator_known_channel_eligible_actions"] == 0
    assert second["unknown_channel_eligible_action_count"] == 1


def test_unresolved_noneligible_context_stays_visible_as_review_support() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    second = result["episode_feature_vectors"][1]
    assert second["review_limited_or_other_noneligible_count"] == 1
    assert second["unresolved_semantics_context_count"] == 1
    assert "REVIEW_DEBT" in second["feature_readiness"]


def test_episode_family_drift_fails_closed() -> None:
    episode, semantics = _payloads()
    episode = copy.deepcopy(episode)
    episode["episode_candidates"][0]["action_family_distribution"] = {"PASS": 2}
    result = build_episode_feature_vectors(episode, semantics)
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("episode_action_family_distribution_mismatch") for hit in result["hard_block_hits"])


def test_global_semantic_reconciliation_drift_fails_closed() -> None:
    episode, semantics = _payloads()
    semantics = copy.deepcopy(semantics)
    semantics["eligible_action_family_candidate_counts"] = {"PASS": 2, "SHOT": 1, "TURNOVER": 1}
    result = build_episode_feature_vectors(episode, semantics)
    assert result["status"] == "FAIL_CLOSED"
    assert "episode_feature_action_family_reconciliation_mismatch" in result["hard_block_hits"]


def test_claim_locks_and_ordering_locks_remain_closed() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["physical_action_truth"] is False
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["phase_truth"] is False
    assert result["rhythm_truth"] is False
    assert result["tactical_truth"] is False
    assert result["dominance_truth"] is False
    assert result["fatigue_truth"] is False
    assert result["production_release"] is False
    assert result["same_timestamp_internal_ordering_allowed"] is False
    assert result["source_row_order_is_temporal_truth"] is False


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/episode-features")


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "episode_feature_vector.py").read_text(encoding="utf-8")
    forbidden = ["Fenerbahce", "Galatasaray", "Genclerbirligi", "15.08.2026", "Turkey", "World Cup"]
    assert not any(token in text for token in forbidden)
    assert "context_ordinal" not in text
