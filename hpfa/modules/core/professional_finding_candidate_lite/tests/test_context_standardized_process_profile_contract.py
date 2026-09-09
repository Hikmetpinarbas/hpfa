from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
CONTRACT = ROOT / "hpfa" / "modules" / "core" / "professional_finding_candidate_lite" / "contract" / "context_standardized_process_profile_lite_v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_is_spec_only_and_cannot_emit_adjusted_truth() -> None:
    c = _contract()
    state = c["current_execution_state"]
    assert c["status"] == "SPEC_ONLY"
    assert c["claim_ceiling"] == "CONTEXT_STANDARDIZATION_PREREQUISITE_CONTRACT_ONLY"
    assert state["runtime_context_standardization_evaluated"] is False
    assert state["model_implementation_present"] is False
    assert state["model_execution_allowed"] is False
    assert state["standardized_rate_output_allowed"] is False
    assert state["expected_context_rate_output_allowed"] is False
    assert c["production_release"] is False


def test_required_game_context_cannot_be_fabricated_from_missingness() -> None:
    c = _contract()
    policy = c["field_admission_policy"]
    required = set(c["required_context_fields_for_standardization"])
    assert {"minute_state", "score_state", "manpower_state", "venue_state", "eligible_exposure"} <= required
    assert policy["missing_required_context_is_zero"] is False
    assert policy["missing_required_context_is_neutral_state"] is False
    assert policy["provider_label_is_context_truth"] is False
    assert policy["opponent_strength_prior_missing_does_not_imply_average_opponent"] is True


def test_reflections_cannot_create_cross_match_independence() -> None:
    c = _contract()
    deps = c["required_dependency_controls"]
    assert deps["same_match_reflections_are_independent_observations"] is False
    assert deps["independence_group_required"] is True
    assert deps["provenance_root_required"] is True
    assert deps["duplicate_reflection_suppression_required"] is True


def test_validation_leakage_and_claim_shortcuts_are_closed() -> None:
    c = _contract()
    validation = c["required_validation_controls_before_model_execution"]
    state = c["current_execution_state"]
    forbidden = set(c["forbidden_inference"])
    assert validation["train_evaluation_overlap_allowed"] is False
    assert validation["future_match_leakage_allowed"] is False
    assert validation["out_of_sample_validation_required"] is True
    assert validation["leave_one_match_or_season_out_state_visible"] is True
    assert state["cross_match_team_tendency_claim_allowed"] is False
    assert state["tactical_adaptation_claim_allowed"] is False
    assert state["coach_intention_claim_allowed"] is False
    assert state["causal_score_effect_claim_allowed"] is False
    assert "context_adjusted_metric_equals_intrinsic_quality" in forbidden
    assert "out_of_sample_stability_equals_causal_validity" in forbidden


def test_current_truth_locks_remain_closed() -> None:
    c = _contract()
    assert c["canonical_event_count"] == "UNKNOWN"
    assert c["true_action_count"] == "UNKNOWN"
    assert c["production_release"] is False
