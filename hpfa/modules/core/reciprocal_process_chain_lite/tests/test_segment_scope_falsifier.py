from __future__ import annotations

from hpfa.modules.core.reciprocal_process_chain_lite.src.segment_scope_falsifier import (
    evaluate_segment_only_falsifier,
)


def _finding(signature):
    return {
        "defeasible_process_finding_input_id": "dfi_test",
        "process_family_signature_candidate": {
            "anchor_action_families": list(signature[0]),
            "response_action_families": list(signature[1]),
        },
        "counter_search_evaluated_families": ["DIRECT_VISIBLE_OUTCOME_CONTRAST"],
        "counter_search_pending_families": [
            "ALTERNATIVE_EXPLANATION",
            "CONTEXT_DEPENDENCE",
            "DUPLICATE_REFLECTION_RISK",
            "FAILED_TRACE_SUPPORT",
            "OPPONENT_SYMMETRY",
            "PLAYER_OUTLIER",
            "SEGMENT_ONLY",
            "THRESHOLD_SENSITIVITY",
        ],
        "falsifier_families_evaluated": ["DIRECT_VISIBLE_OUTCOME_CONTRAST"],
        "falsifier_families_pending": [
            "ALTERNATIVE_EXPLANATION",
            "CONTEXT_DEPENDENCE",
            "DUPLICATE_REFLECTION_RISK",
            "FAILED_TRACE_SUPPORT",
            "OPPONENT_SYMMETRY",
            "PLAYER_OUTLIER",
            "SEGMENT_ONLY",
            "THRESHOLD_SENSITIVITY",
        ],
    }


def _profile(signature, repeat, episodes, incomplete=0):
    return {
        "process_family_signature_candidate": {
            "anchor_action_families": list(signature[0]),
            "response_action_families": list(signature[1]),
        },
        "visible_repeat_count_candidate": repeat,
        "unique_episode_scope_count_candidate": episodes,
        "incomplete_episode_binding_count": incomplete,
    }


def _run(profile):
    signature = (("PASS", "TURNOVER"), ("PASS",))
    finding = _finding(signature)
    original_pending = list(finding["counter_search_pending_families"])
    original_evaluated = list(finding["counter_search_evaluated_families"])
    result = evaluate_segment_only_falsifier(
        {"defeasible_process_finding_inputs": [finding]},
        {"process_variant_profiles": [profile(signature)]},
    )
    return result, finding, original_pending, original_evaluated


def test_multi_episode_repeat_is_evaluable_without_stable_tendency_promotion():
    result, finding, pending, evaluated = _run(lambda sig: _profile(sig, 5, 3, 0))
    row = result["segment_only_evaluations"][0]
    assert row["segment_only_evaluation_state"] == "MULTI_EPISODE_SCOPE_VISIBLE_CANDIDATE"
    assert row["segment_only_falsifier_evaluable_from_current_episode_scope"] is True
    assert row["segment_only_risk_candidate"] is False
    assert row["multi_episode_spread_is_stable_tendency_truth"] is False
    assert result["segment_only_falsifier_evaluated_count"] == 1
    assert result["segment_only_multi_episode_not_observed_count"] == 1
    assert finding["counter_search_pending_families"] == pending
    assert finding["counter_search_evaluated_families"] == evaluated


def test_single_episode_repeat_is_segment_only_risk_candidate():
    result, finding, pending, evaluated = _run(lambda sig: _profile(sig, 3, 1, 0))
    row = result["segment_only_evaluations"][0]
    assert row["segment_only_evaluation_state"] == "SINGLE_EPISODE_SCOPE_ONLY_CANDIDATE"
    assert row["segment_only_falsifier_evaluable_from_current_episode_scope"] is True
    assert row["segment_only_risk_candidate"] is True
    assert result["segment_only_risk_candidate_count"] == 1
    assert row["segment_only_absence_confirms_recurrence"] is False
    assert finding["counter_search_pending_families"] == pending
    assert finding["counter_search_evaluated_families"] == evaluated


def test_incomplete_episode_binding_keeps_segment_only_pending():
    result, finding, pending, evaluated = _run(lambda sig: _profile(sig, 5, 3, 1))
    row = result["segment_only_evaluations"][0]
    assert row["segment_only_evaluation_state"] == "SEGMENT_SCOPE_NOT_EVALUATED_INCOMPLETE_EPISODE_BINDING"
    assert row["segment_only_falsifier_evaluable_from_current_episode_scope"] is False
    assert result["segment_only_pending_count"] == 1
    assert result["segment_only_safety_envelope_propagated"] is False
    assert finding["counter_search_pending_families"] == pending
    assert finding["counter_search_evaluated_families"] == evaluated


def test_singleton_has_no_repeat_analogue_and_does_not_close_falsifier():
    result, finding, pending, evaluated = _run(lambda sig: _profile(sig, 1, 1, 0))
    row = result["segment_only_evaluations"][0]
    assert row["segment_only_evaluation_state"] == "SEGMENT_SCOPE_NOT_EVALUATED_NO_REPEAT_ANALOGUE"
    assert row["segment_only_falsifier_evaluable_from_current_episode_scope"] is False
    assert result["segment_only_pending_count"] == 1
    assert finding["counter_search_pending_families"] == pending
    assert finding["counter_search_evaluated_families"] == evaluated


def test_no_profile_is_not_silently_interpreted_as_counterevidence():
    signature = (("PASS",), ("PASS",))
    finding = _finding(signature)
    result = evaluate_segment_only_falsifier(
        {"defeasible_process_finding_inputs": [finding]},
        {"process_variant_profiles": []},
    )
    row = result["segment_only_evaluations"][0]
    assert row["segment_only_evaluation_state"] == "SEGMENT_SCOPE_NOT_EVALUATED_NO_PROFILE"
    assert row["segment_only_falsifier_evaluable_from_current_episode_scope"] is False
    assert result["segment_only_risk_candidate_count"] == 0
    assert result["counter_search_complete_for_final_finding"] is False
    assert result["falsifier_coverage_state"] == "PARTIAL"


def test_claim_locks_and_match_agnostic_surface():
    signature = (("DUEL", "PASS"), ("PASS", "TURNOVER"))
    result = evaluate_segment_only_falsifier(
        {"defeasible_process_finding_inputs": [_finding(signature)]},
        {"process_variant_profiles": [_profile(signature, 2, 2, 0)]},
    )
    text = repr(result)
    assert "Genclerbirligi" not in text
    assert "Fenerbahce" not in text
    assert "15.08.2026" not in text
    assert result["segment_only_evaluation_is_recurrence_truth"] is False
    assert result["segment_only_evaluation_is_stable_tendency_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
