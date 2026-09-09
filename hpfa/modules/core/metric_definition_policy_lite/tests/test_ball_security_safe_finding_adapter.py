from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.ball_security_safe_finding_adapter import (
    build_ball_security_safe_finding_projection,
)


def _payload():
    construct = {
        "construct_candidate_id": "bsc_binding_a",
        "construct_target": "BALL_SECURITY",
        "denominator_set_id": "ball_use_trace_candidates:binding_a",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_BALL_SECURITY_V1",
        "dependency_group": "ball_security:binding_a",
        "provenance_root": "binding_a",
        "eligible_ball_use_trace_candidate_count": 3,
        "evaluable_ball_security_consequence_candidate_count": 2,
        "ball_security_consequence_coverage_rate_candidate": 0.666667,
        "visible_retained_follow_up_candidate_count": 1,
        "visible_adverse_handover_candidate_count": 1,
        "unresolved_or_missing_consequence_candidate_count": 1,
        "support_consequence_candidate_refs": ["consequence_support"],
        "counterevidence_consequence_candidate_refs": ["consequence_adverse"],
        "unresolved_consequence_candidate_refs": ["consequence_unknown"],
        "team_ball_security_profile_candidates": [{"team_identity_candidate_id": "team_a"}],
        "actor_ball_security_profile_candidates": [{"actor_identity_candidate_id": "actor_a"}],
        "explicit_turnover_trace_candidate_count_outside_denominator": 1,
        "explicit_turnover_trace_candidate_refs_outside_denominator": ["trace_turnover_context"],
        "alternative_explanations": [
            "receiver support and opponent response may explain visible retention",
            "provider event-family coverage may omit some ball-control losses",
        ],
        "uncertainty": "MATCH_LOCAL_VISIBLE_BALL_USE_CONSEQUENCE_ONLY",
        "withdrawal_condition": "withdraw if denominator, consequence, identity or dependency controls fail",
        "analyst_action": "inspect denominator, support, adverse, unresolved and turnover-context refs before publication",
        "ball_security_score_emitted": False,
        "same_provider_reflection_adds_independent_vote": False,
        "missing_consequence_is_counterevidence": False,
        "construct_validity_truth": False,
        "player_quality_truth": False,
        "team_control_truth": False,
        "causal_truth": False,
        "explicit_turnover_is_denominator_member": False,
    }
    return {
        "module_id": "ball_security_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate": construct,
        "hard_block_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_ball_security_construct_reuses_safe_finding_gate_without_truth_promotion():
    result = build_ball_security_safe_finding_projection(_payload())
    assert result["module_id"] == "ball_security_safe_finding_projection_v1"
    assert result["engineering_envelope_complete"] is True
    finding = result["finding_candidate"]
    assert finding["construct_target"] == "BALL_SECURITY"
    assert finding["what_visible"]["visible_retained_follow_up_candidate_count"] == 1
    assert finding["what_visible"]["visible_adverse_handover_candidate_count"] == 1
    assert finding["support"]["explicit_turnover_trace_candidate_refs_outside_denominator"] == ["trace_turnover_context"]
    assert finding["support"]["explicit_turnover_context_is_independent_support"] is False
    assert finding["counterevidence"]["explicit_turnover_context_is_denominator_member"] is False
    assert finding["counterevidence"]["explicit_turnover_context_is_independent_counterevidence_vote"] is False
    assert finding["physical_active_match_evidence_present"] is False
    assert finding["professional_finding_emitted"] is False
    assert finding["claim_output_allowed"] is False


def test_turnover_reflection_cannot_be_injected_into_denominator():
    payload = _payload()
    payload["construct_candidate"]["explicit_turnover_is_denominator_member"] = True
    result = build_ball_security_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "explicit_turnover_denominator_inflation_claimed" in result["hard_block_hits"]


def test_truth_or_independence_escalation_fails_closed():
    for field in (
        "ball_security_score_emitted",
        "same_provider_reflection_adds_independent_vote",
        "missing_consequence_is_counterevidence",
        "construct_validity_truth",
        "player_quality_truth",
        "team_control_truth",
        "causal_truth",
    ):
        payload = _payload()
        payload["construct_candidate"][field] = True
        result = build_ball_security_safe_finding_projection(payload)
        assert result["status"] == "FAIL_CLOSED"
        assert result["finding_candidate_count"] == 0


def test_required_professional_finding_envelope_survives_adapter():
    finding = build_ball_security_safe_finding_projection(_payload())["finding_candidate"]
    assert finding["support"]["support_refs"] == ["consequence_support"]
    assert finding["counterevidence"]["refs"] == ["consequence_adverse"]
    assert finding["alternative_explanations"]
    assert finding["uncertainty"]
    assert finding["withdrawal_condition"]
    assert finding["analyst_action"]
    assert finding["same_provider_support_is_independent_vote"] is False
    assert finding["independent_support_vote_count"] == 0


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/metric_definition_policy_lite/src/ball_security_safe_finding_adapter.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "15.08.2026"):
        assert token not in source
