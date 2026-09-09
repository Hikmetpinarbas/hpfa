from hpfa.modules.core.metric_definition_policy_lite.src.progression_safe_finding_projection import (
    build_progression_safe_finding_projection,
)


def _payload(*, status="PASS_CANDIDATE", denominator=3, evaluable=2):
    construct = {
        "construct_candidate_id": "pec_test",
        "construct_target": "PROGRESSION_EFFECTIVENESS",
        "eligible_progression_trace_candidate_count": denominator,
        "evaluable_progression_consequence_candidate_count": evaluable,
        "progression_consequence_coverage_rate_candidate": (evaluable / denominator) if denominator else None,
        "visible_positive_follow_up_candidate_count": 1 if evaluable else 0,
        "visible_adverse_handover_candidate_count": 1 if evaluable > 1 else 0,
        "unresolved_or_missing_consequence_candidate_count": max(0, denominator - evaluable),
        "support_consequence_candidate_refs": ["c1"] if evaluable else [],
        "counterevidence_consequence_candidate_refs": ["c2"] if evaluable > 1 else [],
        "unresolved_consequence_candidate_refs": ["c3"] if denominator > evaluable else [],
        "alternative_explanations": [
            "visible consequence may reflect teammate/opponent response rather than anchor quality alone"
        ],
        "uncertainty": "MATCH_LOCAL_VISIBLE_CONSEQUENCE_COVERAGE_ONLY",
        "withdrawal_condition": "withdraw if denominator or consequence admission fails",
        "analyst_action": "inspect support, counterevidence and unresolved refs before reporting",
        "team_progression_effectiveness_profile_candidates": [],
        "actor_progression_effectiveness_profile_candidates": [],
        "effectiveness_score_emitted": False,
        "same_provider_reflection_adds_independent_vote": False,
        "missing_consequence_is_counterevidence": False,
        "construct_validity_truth": False,
        "player_quality_truth": False,
        "team_control_truth": False,
    }
    return {
        "module_id": "progression_effectiveness_construct_v1",
        "status": status,
        "construct_candidate": construct,
        "construct_candidate_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
    }


def test_builds_defeasible_finding_envelope_without_opening_claim_gate():
    result = build_progression_safe_finding_projection(_payload())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["engineering_envelope_complete"] is True
    finding = result["finding_candidate"]
    assert finding["finding_state"] == "ENGINEERING_ENVELOPE_READY_PHYSICAL_ACTIVE_MATCH_REQUIRED"
    assert finding["support_refs"] == ["c1"]
    assert finding["counterevidence_refs"] == ["c2"]
    assert finding["unresolved_refs"] == ["c3"]
    assert finding["counterevidence_absence_is_confirmation"] is False
    assert finding["physical_active_match_evidence_required"] is True
    assert finding["physical_active_match_evidence_present"] is False
    assert result["professional_finding_emitted"] is False
    assert result["claim_output_allowed"] is False


def test_no_visible_counterevidence_is_allowed_but_never_confirmation():
    payload = _payload(denominator=1, evaluable=1)
    payload["construct_candidate"]["counterevidence_consequence_candidate_refs"] = []
    result = build_progression_safe_finding_projection(payload)
    assert result["status"] == "PASS_CANDIDATE"
    assert result["finding_candidate"]["counterevidence_refs"] == []
    assert result["finding_candidate"]["counterevidence_absence_is_confirmation"] is False


def test_missing_alternative_explanation_fails_closed():
    payload = _payload()
    payload["construct_candidate"]["alternative_explanations"] = []
    result = build_progression_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "finding_envelope_alternative_explanation_missing" in result["hard_block_hits"]


def test_upstream_claim_escalation_fails_closed():
    payload = _payload()
    payload["claim_output_allowed"] = True
    result = build_progression_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_claim_output_allowed" in result["hard_block_hits"]


def test_zero_evaluable_population_stays_review_required():
    result = build_progression_safe_finding_projection(_payload(denominator=2, evaluable=0))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["engineering_envelope_complete"] is False
    assert result["finding_candidate"]["finding_state"] == "REVIEW_REQUIRED_INSUFFICIENT_EVALUABLE_POPULATION"


def test_same_provider_never_becomes_independent_vote():
    result = build_progression_safe_finding_projection(_payload(denominator=1, evaluable=1))
    finding = result["finding_candidate"]
    assert finding["same_provider_support_is_independent_vote"] is False
    assert finding["independent_support_vote_count"] == 0


def test_no_sample_match_identity_leak():
    result = build_progression_safe_finding_projection(_payload())
    rendered = str(result)
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in rendered
