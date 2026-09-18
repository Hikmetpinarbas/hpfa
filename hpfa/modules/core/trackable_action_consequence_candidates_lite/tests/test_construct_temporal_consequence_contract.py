from __future__ import annotations

from hpfa.modules.core.trackable_action_consequence_candidates_lite.src.construct_temporal_consequence_contract import (
    apply_construct_temporal_contract,
)


def _record(source_role: str, *families: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"tacc_{source_role}_{'_'.join(families)}",
        "source_role": source_role,
        "anchor_action_family_candidates": list(families),
        "consequence_candidate_is_causal_truth": False,
        "team_response_is_tactical_truth": False,
    }


def test_global_grid_is_diagnostic_only_and_cannot_authorize_claim() -> None:
    payload = {
        "status": "PASS",
        "module_status": "PASS",
        "trackable_action_consequence_candidates": [_record("PLAYER_SURFACE_CANDIDATE", "PASS")],
        "window_seconds": [5.0, 8.0, 12.0],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = apply_construct_temporal_contract(payload)
    row = result["trackable_action_consequence_candidates"][0]

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["global_window_is_production_temporal_contract"] is False
    assert result["production_temporal_window_thresholds_admitted"] is False
    assert result["diagnostic_window_can_authorize_claim"] is False
    assert result["single_match_observed_latency_can_set_production_threshold"] is False
    assert row["diagnostic_window_seconds"] == [5.0, 8.0, 12.0]
    assert row["production_temporal_window_seconds"] is None
    assert row["temporal_consequence_contract_state"] == "CALIBRATION_REQUIRED"
    assert row["diagnostic_window_can_authorize_professional_finding"] is False


def test_role_aware_contract_key_separates_goalkeeper_and_outfield_pass_surfaces() -> None:
    payload = {
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidates": [
            _record("PLAYER_SURFACE_CANDIDATE", "PASS"),
            _record("GOALKEEPER_SURFACE_CANDIDATE", "PASS"),
        ],
        "window_seconds": [5.0, 8.0, 12.0],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = apply_construct_temporal_contract(payload)
    keys = result["construct_temporal_contract_keys"]

    assert keys == [
        "GOALKEEPER_SURFACE_CANDIDATE|PASS",
        "PLAYER_SURFACE_CANDIDATE|PASS",
    ]
    assert result["construct_temporal_contract_key_count"] == 2
    assert result["construct_temporal_contract_calibration_required_candidate_count"] == 2
    assert result["construct_temporal_contract_unresolved_key_count"] == 0


def test_missing_family_stays_reviewable_without_inventing_threshold() -> None:
    payload = {
        "status": "PASS",
        "module_status": "PASS",
        "trackable_action_consequence_candidates": [_record("PLAYER_SURFACE_CANDIDATE")],
        "window_seconds": [5.0, 8.0, 12.0],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = apply_construct_temporal_contract(payload)
    row = result["trackable_action_consequence_candidates"][0]

    assert row["temporal_consequence_contract_key"] == "UNRESOLVED_CONSTRUCT_CONTRACT_KEY"
    assert row["production_temporal_window_seconds"] is None
    assert result["construct_temporal_contract_unresolved_key_count"] == 1
    assert "construct_temporal_contract_key_unresolved" in result["review_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_fail_closed_payload_is_not_laundered_into_review_required() -> None:
    payload = {
        "status": "FAIL_CLOSED",
        "module_status": "FAIL_CLOSED",
        "hard_block_hits": ["upstream_fail_closed"],
        "trackable_action_consequence_candidates": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = apply_construct_temporal_contract(payload)

    assert result == payload
    assert result["status"] == "FAIL_CLOSED"


def test_truth_and_release_locks_remain_closed() -> None:
    payload = {
        "status": "PASS",
        "module_status": "PASS",
        "trackable_action_consequence_candidates": [_record("PLAYER_SURFACE_CANDIDATE", "RECOVERY")],
        "window_seconds": [5.0, 8.0, 12.0],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = apply_construct_temporal_contract(payload)
    row = result["trackable_action_consequence_candidates"][0]

    assert row["construct_contract_is_causal_truth"] is False
    assert row["construct_contract_is_tactical_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
