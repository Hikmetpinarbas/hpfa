from hpfa.modules.core.professional_finding_candidate_lite.src.alternative_explanation import (
    attach_alternative_explanation_evaluation,
)


def _payload(*, full_trace=True, with_signals=True):
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [{
            "professional_finding_candidate_id": "p1",
            "finding_challenge_packet": {
                "evaluated_falsifier_families": [],
                "pending_falsifier_families": ["DUPLICATE_REFLECTION_RISK", "ALTERNATIVE_EXPLANATION"],
                "different_visible_outcome_analogue_present": with_signals,
                "player_concentration": {
                    "state": "PLAYER_OUTLIER_RISK_PRESENT" if with_signals else "NO_PLAYER_OUTLIER_RISK_VISIBLE",
                },
                "segment_only": {
                    "state": "SEGMENT_ONLY_RISK_PRESENT" if with_signals else "MULTI_EPISODE_SCOPE_VISIBLE",
                },
                "opponent_symmetry": {"state": "NO_OPPONENT_SYMMETRY_VISIBLE"},
                "trace_dependency": {
                    "state": "MEASURED_NOT_INDEPENDENCE_TRUTH",
                    "trace_membership_uniqueness_ratio_candidate": 0.5 if with_signals else 1.0,
                },
                "visible_episode_context_contrast": {
                    "state_candidate": (
                        "VISIBLE_EPISODE_CONTEXT_VARIATION_ACROSS_OUTCOMES_CANDIDATE"
                        if with_signals
                        else "NO_VISIBLE_EPISODE_CONTEXT_DIFFERENCE_AT_CURRENT_RESOLUTION"
                    ),
                },
                "threshold_sensitivity": {
                    "state_candidate": (
                        "SENSITIVE_TO_STRICTER_REPEAT_THRESHOLD"
                        if with_signals
                        else "SURVIVES_ALL_TESTED_REPEAT_THRESHOLDS"
                    ),
                },
                "failed_trace_support": {
                    "state_candidate": (
                        "INCOMPLETE_OCCURRENCE_TRACE_EVIDENCE_REVIEW_REQUIRED"
                        if with_signals
                        else "COMPLETE_VISIBLE_PARTICIPANT_TRACE_SUPPORT_CURRENT_SCOPE"
                    ),
                    "full_occurrence_binding_scope_evaluated": full_trace,
                },
            },
            "alternative_explanations": [],
            "uncertainty": {},
            "claim_output_allowed": False,
            "professional_finding_emitted": False,
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_visible_challenge_signals_become_alternative_explanation_candidates_not_causal_truth():
    result = attach_alternative_explanation_evaluation(_payload())
    row = result["professional_finding_candidates"][0]
    evaluation = row["finding_challenge_packet"]["alternative_explanation_evaluation"]
    types = {item["type"] for item in evaluation["visible_alternative_explanation_candidates"]}
    assert "PLAYER_CONCENTRATION" in types
    assert "SEGMENT_CONCENTRATION" in types
    assert "TRACE_DEPENDENCY" in types
    assert "CONTEXT_DEPENDENCE" in types
    assert "THRESHOLD_SENSITIVITY" in types
    assert "TRACE_COVERAGE_LIMITATION" in types
    assert "DIFFERENT_VISIBLE_OUTCOME_ANALOGUE" in types
    assert evaluation["alternative_explanation_is_causal_truth"] is False
    assert evaluation["absence_of_visible_alternative_proves_primary_explanation"] is False
    assert evaluation["video_tracking_alternative_remains_unresolved"] is True


def test_complete_current_event_only_scope_can_close_only_alternative_explanation_family():
    result = attach_alternative_explanation_evaluation(_payload(full_trace=True, with_signals=False))
    row = result["professional_finding_candidates"][0]
    challenge = row["finding_challenge_packet"]
    evaluation = challenge["alternative_explanation_evaluation"]
    assert evaluation["state_candidate"] == "NO_VISIBLE_ALTERNATIVE_SIGNAL_CURRENT_SCOPE"
    assert challenge["alternative_explanation_search_complete_for_current_event_only_visible_scope"] is True
    assert "ALTERNATIVE_EXPLANATION" not in challenge["pending_falsifier_families"]
    assert "DUPLICATE_REFLECTION_RISK" in challenge["pending_falsifier_families"]
    assert challenge["alternative_explanation_search_complete_for_final_finding"] is False
    assert evaluation["absence_of_visible_alternative_proves_primary_explanation"] is False


def test_chain_only_trace_scope_keeps_alternative_explanation_debt_partial():
    result = attach_alternative_explanation_evaluation(_payload(full_trace=False))
    row = result["professional_finding_candidates"][0]
    challenge = row["finding_challenge_packet"]
    evaluation = challenge["alternative_explanation_evaluation"]
    assert evaluation["state_candidate"] == "PARTIAL_ALTERNATIVE_EXPLANATION_COVERAGE"
    assert challenge["alternative_explanation_search_complete_for_current_event_only_visible_scope"] is False
    assert "ALTERNATIVE_EXPLANATION" in challenge["pending_falsifier_families"]


def test_claim_locks_remain_closed_after_alternative_explanation_evaluation():
    result = attach_alternative_explanation_evaluation(_payload())
    row = result["professional_finding_candidates"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["claim_output_allowed_count"] == 0
    assert result["professional_finding_emitted_count"] == 0
    assert row["claim_output_allowed"] is False
    assert row["professional_finding_emitted"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
