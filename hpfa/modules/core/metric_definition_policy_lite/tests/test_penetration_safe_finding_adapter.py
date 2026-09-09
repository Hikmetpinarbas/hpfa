from hpfa.modules.core.metric_definition_policy_lite.src.penetration_safe_finding_adapter import (
    build_penetration_safe_finding_projection,
)


def _payload():
    return {
        "module_id": "penetration_construct_v1",
        "status": "PASS_CANDIDATE",
        "construct_candidate": {
            "construct_candidate_id": "pen_demo",
            "construct_target": "PENETRATION",
            "denominator_set_id": "penetration_evaluable_progression:demo",
            "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
            "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
            "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
            "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
            "context_policy_id": "ZFGV_PENETRATION_V1",
            "dependency_group": "penetration:demo",
            "provenance_root": "demo",
            "eligible_progression_trace_candidate_count": 4,
            "penetration_evaluable_progression_candidate_count": 3,
            "penetration_followup_coverage_rate_candidate": 0.75,
            "visible_terminal_penetration_support_candidate_count": 2,
            "visible_shot_followup_candidate_count": 1,
            "visible_terminal_outcome_support_candidate_count": 1,
            "visible_adverse_handover_candidate_count": 1,
            "unresolved_or_missing_followup_candidate_count": 1,
            "support_consequence_candidate_refs": ["c1", "c2"],
            "counterevidence_consequence_candidate_refs": ["c3"],
            "unresolved_consequence_candidate_refs": ["c4"],
            "alternative_explanations": ["teammate/opponent response may shape terminal follow-up"],
            "uncertainty": "MATCH_LOCAL_VISIBLE_TERMINAL_FOLLOWUP_ONLY_BOX_ACCESS_SURFACE_NOT_YET_ADMITTED",
            "withdrawal_condition": "withdraw if denominator or consequence admission fails",
            "analyst_action": "inspect terminal, adverse and unresolved refs without claiming complete box access",
            "penetration_score_emitted": False,
            "same_provider_reflection_adds_independent_vote": False,
            "missing_followup_is_counterevidence": False,
            "penetration_truth": False,
            "territorial_control_truth": False,
            "causal_creation_truth": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
            "box_access_surface_available": False,
            "box_access_rate_candidate": None,
            "box_access_not_inferred_from_shot": True,
        },
        "hard_block_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_penetration_reuses_safe_finding_envelope_without_box_access_truth():
    result = build_penetration_safe_finding_projection(_payload())
    assert result["module_id"] == "penetration_safe_finding_projection_v1"
    assert result["finding_candidate_count"] == 1
    finding = result["finding_candidate"]
    assert finding["construct_target"] == "PENETRATION"
    assert finding["what_visible"]["visible_terminal_penetration_support_candidate_count"] == 2
    assert finding["box_access_surface_available"] is False
    assert finding["box_access_rate_candidate"] is None
    assert finding["box_access_not_inferred_from_shot"] is True
    assert finding["physical_active_match_evidence_present"] is False
    assert finding["professional_finding_emitted"] is False
    assert finding["claim_output_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_missing_followup_stays_unresolved_not_counterevidence():
    result = build_penetration_safe_finding_projection(_payload())
    finding = result["finding_candidate"]
    assert finding["counterevidence"]["refs"] == ["c3"]
    assert finding["counterevidence"]["unresolved_refs"] == ["c4"]
    assert finding["counterevidence"]["missing_follow_up_is_failure"] is False
    assert finding["counterevidence"]["no_box_access_surface_is_counterevidence"] is False


def test_same_provider_reflection_never_becomes_independent_vote():
    result = build_penetration_safe_finding_projection(_payload())
    finding = result["finding_candidate"]
    assert finding["same_provider_support_is_independent_vote"] is False
    assert finding["independent_support_vote_count"] == 0


def test_shot_cannot_be_promoted_to_box_access():
    payload = _payload()
    payload["construct_candidate"]["box_access_surface_available"] = True
    result = build_penetration_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "box_access_surface_unreviewed_or_claimed" in result["hard_block_hits"]

    payload = _payload()
    payload["construct_candidate"]["box_access_rate_candidate"] = 0.5
    result = build_penetration_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "box_access_rate_fabricated" in result["hard_block_hits"]


def test_upstream_truth_escalation_fails_closed():
    for field in ("penetration_truth", "territorial_control_truth", "causal_creation_truth"):
        payload = _payload()
        payload["construct_candidate"][field] = True
        result = build_penetration_safe_finding_projection(payload)
        assert result["status"] == "FAIL_CLOSED"


def test_missingness_cannot_be_counterevidence():
    payload = _payload()
    payload["construct_candidate"]["missing_followup_is_counterevidence"] = True
    result = build_penetration_safe_finding_projection(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "missingness_counterevidence_lock_missing" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    import inspect
    import hpfa.modules.core.metric_definition_policy_lite.src.penetration_safe_finding_adapter as adapter

    source = inspect.getsource(adapter)
    forbidden = [
        "Gencler" + "birligi",
        "Fener" + "bahce",
        "Tur" + "key",
        "Aus" + "tralia",
        "15.08." + "2026",
    ]
    assert all(token not in source for token in forbidden)
