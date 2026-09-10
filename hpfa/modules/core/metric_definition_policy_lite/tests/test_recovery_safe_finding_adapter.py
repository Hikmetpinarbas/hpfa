from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.recovery_safe_finding_adapter import (
    build_recovery_safe_finding_projection,
)


def _payload():
    construct = {
        "construct_candidate_id": "ryc_binding_a",
        "construct_target": "RECOVERY_YIELD",
        "denominator_set_id": "recovery_interception_trace_candidates:binding_a",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_RECOVERY_YIELD_V1",
        "dependency_group": "recovery_yield:binding_a",
        "provenance_root": "binding_a",
        "eligible_recovery_trace_candidate_count": 3,
        "evaluable_recovery_consequence_candidate_count": 2,
        "recovery_consequence_coverage_rate_candidate": 0.666667,
        "visible_same_team_yield_candidate_count": 1,
        "visible_adverse_post_recovery_handover_candidate_count": 1,
        "unresolved_or_missing_consequence_candidate_count": 1,
        "support_consequence_candidate_refs": ["consequence_support"],
        "counterevidence_consequence_candidate_refs": ["consequence_adverse"],
        "unresolved_consequence_candidate_refs": ["consequence_unknown"],
        "team_recovery_yield_profile_candidates": [{"team_identity_candidate_id": "team_a"}],
        "actor_recovery_yield_profile_candidates": [{"actor_identity_candidate_id": "actor_a"}],
        "recovery_progression_conversion_eligible_recovery_trace_candidate_count": 2,
        "visible_recovery_to_progression_candidate_count": 1,
        "visible_recovery_to_progression_rate_candidate": 0.5,
        "visible_recovery_to_progression_candidates": [{
            "recovery_trace_candidate_id": "trace_recovery_a",
            "progression_trace_candidate_id": "trace_progression_a",
            "binding_state": "VISIBLE_RECOVERY_TO_PROGRESSION_CANDIDATE",
            "sequence_truth": False,
            "possession_truth": False,
            "causal_truth": False,
        }],
        "no_visible_progression_followup_candidate_count": 1,
        "alternative_explanations": [
            "teammate support and opponent response may explain visible continuation",
            "provider coverage may be selective",
        ],
        "uncertainty": "MATCH_LOCAL_VISIBLE_RECOVERY_CONSEQUENCE_ONLY",
        "withdrawal_condition": "withdraw if denominator, consequence, identity or dependency controls fail",
        "analyst_action": "inspect support, adverse, unresolved and progression-binding refs before publication",
        "recovery_yield_score_emitted": False,
        "same_provider_reflection_adds_independent_vote": False,
        "missing_consequence_is_counterevidence": False,
        "construct_validity_truth": False,
        "recovery_quality_truth": False,
        "possession_gain_truth": False,
        "team_control_truth": False,
        "causal_truth": False,
        "no_visible_progression_followup_is_failure": False,
        "no_visible_progression_followup_is_counterevidence": False,
        "conversion_candidate_is_sequence_truth": False,
        "conversion_candidate_is_possession_truth": False,
        "conversion_candidate_is_causal_truth": False,
        "source_row_order_is_temporal_truth": False,
        "same_time_is_ordered": False,
    }
    return {
        "module_id": "recovery_yield_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate": construct,
        "hard_block_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_recovery_construct_reuses_safe_finding_gate_without_truth_promotion():
    result = build_recovery_safe_finding_projection(_payload())
    assert result["module_id"] == "recovery_safe_finding_projection_v1"
    assert result["engineering_envelope_complete"] is True
    finding = result["finding_candidate"]
    assert finding["construct_target"] == "RECOVERY_YIELD"
    assert finding["what_visible"]["visible_same_team_yield_candidate_count"] == 1
    assert finding["support"]["visible_recovery_to_progression_recovery_trace_candidate_refs"] == ["trace_recovery_a"]
    assert finding["support"]["visible_recovery_to_progression_progression_trace_candidate_refs"] == ["trace_progression_a"]
    assert finding["support"]["recovery_progression_conversion_is_independent_support"] is False
    assert finding["counterevidence"]["no_visible_progression_followup_is_failure"] is False
    assert finding["physical_active_match_evidence_present"] is False
    assert finding["professional_finding_emitted"] is False
    assert finding["claim_output_allowed"] is False


def test_no_visible_progression_followup_cannot_be_upgraded_to_failure_or_counterevidence():
    payload = _payload()
    payload["construct_candidate"]["no_visible_progression_followup_is_failure"] = True
    result = build_recovery_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "no_visible_progression_followup_failure_lock_missing" in result["hard_block_hits"]

    payload = _payload()
    payload["construct_candidate"]["no_visible_progression_followup_is_counterevidence"] = True
    result = build_recovery_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "no_visible_progression_followup_counterevidence_lock_missing" in result["hard_block_hits"]


def test_conversion_truth_escalation_fails_closed():
    for field in (
        "conversion_candidate_is_sequence_truth",
        "conversion_candidate_is_possession_truth",
        "conversion_candidate_is_causal_truth",
        "source_row_order_is_temporal_truth",
        "same_time_is_ordered",
    ):
        payload = _payload()
        payload["construct_candidate"][field] = True
        result = build_recovery_safe_finding_projection(payload)
        assert result["status"] == "FAIL_CLOSED"
        assert result["finding_candidate_count"] == 0


def test_required_professional_finding_envelope_survives_adapter():
    finding = build_recovery_safe_finding_projection(_payload())["finding_candidate"]
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
        "hpfa/modules/core/metric_definition_policy_lite/src/recovery_safe_finding_adapter.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
