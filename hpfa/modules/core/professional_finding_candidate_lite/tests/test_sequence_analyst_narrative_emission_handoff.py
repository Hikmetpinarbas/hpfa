from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_analyst_narrative import compose_sequence_analyst_narrative


def _row(*, status="EMIT", emitted=True, allowed=True):
    alternatives = [{"code": "CONTEXT_DEPENDENCE", "detail": "Visible recurrence may depend on the admitted match-local context."}]
    return {
        "analyst_report_block_id": "sfb_emit",
        "entity_scope": "team_scope_candidate",
        "context_scope": [],
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B", "TRACE_C"],
        "recurrence_summary": {"observed_support": 3, "eligible_trace_count": 3, "independent_support_count": 3, "admission_state": "ROBUST_RECURRENT_VISIBLE_TRACE"},
        "robustness_summary": {"robustness_state": "ROBUST"},
        "success_support": 3,
        "failure_support": 0,
        "divergence_support": 0,
        "no_visible_followup_support": 0,
        "counterevidence": {"refs": []},
        "alternative_explanations": alternatives,
        "ALTERNATIVE_EXPLANATIONS": "CONTEXT_DEPENDENCE: visible recurrence may depend on the admitted match-local context",
        "SAFE_MEANING": "A robust recurrent visible process candidate exists in the admitted match-local scope.",
        "FORBIDDEN_INFERENCE": ["causality", "coach intention", "tactical plan truth"],
        "dependency_summary": {"independence_proven": True, "dependency_group_refs": []},
        "uncertainty": {"recurrence_is_tactical_intention_truth": False},
        "withdrawal_condition": "Withdraw if admitted recurrence, independence or challenge evidence changes.",
        "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY",
        "finding_status": status,
        "professional_finding_emitted": emitted,
        "claim_output_allowed": allowed,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _payload(row):
    return {"module_id": "sequence_safe_finding_binding_lite_v1", "status": "PASS", "analyst_report_blocks": [row], "hard_block_hits": [], "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False}


def test_valid_safe_finding_emit_is_accepted_as_input_not_re_emitted():
    result = compose_sequence_analyst_narrative(_payload(_row()))
    assert result["status"] == "PASS"
    block = result["narrative_blocks"][0]
    assert block["source_finding_status"] == "EMIT"
    assert block["source_professional_finding_emitted"] is True
    assert block["source_claim_output_allowed"] is True
    assert block["source_emission_is_input_eligibility_only"] is True
    assert block["claim_output_allowed"] is False
    assert block["production_release"] is False
    assert block["canonical_event_count"] == "UNKNOWN"
    assert block["true_action_count"] == "UNKNOWN"
    assert result["numeric_evidence_counts_are_strict_nonnegative_integers"] is True
    assert result["boolean_numeric_evidence_rejected"] is True


def test_alternative_explanation_only_challenge_survives_structured_and_story_projection():
    row = _row()
    result = compose_sequence_analyst_narrative(_payload(row))
    block = result["narrative_blocks"][0]
    assert block["counterevidence_refs"] == []
    assert block["alternative_explanations"] == row["alternative_explanations"]
    assert block["alternative_explanation_count"] == 1
    assert "CONTEXT_DEPENDENCE" in block["alternative_explanations_tr"]
    assert "Alternatif açıklamalar" in block["story_tr"]
    assert block["challenge_surface_preserved"] is True


def test_emission_gate_mismatch_fails_closed():
    result = compose_sequence_analyst_narrative(_payload(_row(status="EMIT", emitted=True, allowed=False)))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_finding_emission_gate_mismatch" in result["hard_block_hits"]


def test_emitted_row_without_emit_status_fails_closed():
    result = compose_sequence_analyst_narrative(_payload(_row(status="", emitted=True, allowed=True)))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_emitted_finding_status_missing" in result["hard_block_hits"]


def test_boolean_observed_support_cannot_become_one_visible_example():
    row = _row()
    row["trace_variant_refs"] = ["TRACE_A"]
    row["recurrence_summary"]["observed_support"] = True
    result = compose_sequence_analyst_narrative(_payload(row))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_numeric_evidence_invalid:observed_support" in result["hard_block_hits"]
    assert result["narrative_blocks"] == []


def test_boolean_challenge_support_cannot_inflate_counterweight():
    row = _row()
    row["failure_support"] = True
    result = compose_sequence_analyst_narrative(_payload(row))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_numeric_evidence_invalid:failure_support" in result["hard_block_hits"]
    assert result["narrative_blocks"] == []


def test_negative_support_count_fails_closed_before_story_projection():
    row = _row()
    row["divergence_support"] = -1
    result = compose_sequence_analyst_narrative(_payload(row))
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_numeric_evidence_invalid:divergence_support" in result["hard_block_hits"]
    assert result["narrative_blocks"] == []
