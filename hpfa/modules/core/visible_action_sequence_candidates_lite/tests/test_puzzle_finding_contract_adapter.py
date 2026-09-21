from hpfa.modules.core.visible_action_sequence_candidates_lite.src.puzzle_finding_contract_adapter import (
    build_puzzle_finding_contract,
)


def _handoff() -> dict:
    return {
        "safe_finding_handoff_candidate_id": "sfh_test",
        "source_first_supported_branch_divergence_ref": "fsbd_test",
        "finding_status": "DOWNGRADE",
        "professional_finding_emit_allowed": False,
        "what_visible": {
            "state": "SHARED_VISIBLE_ANCHOR_WITH_SUCCESS_FAILURE_SEMANTIC_VARIATION",
            "success_branch_count": 2,
            "failure_branch_count": 1,
            "eligible_outcome_branch_count": 3,
            "raw_success_rate": 0.666667,
        },
        "where_when": {
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "shared_anchor_time_layer_ref": "layer_1",
            "shared_anchor_time_candidate": 123.0,
            "anchor_centered_sequence_branch_map_ref": "branch_map_1",
        },
        "support": {
            "visible_success_sequence_refs": ["seq_s1", "seq_s2"],
            "visible_success_numerator": 2,
            "eligible_denominator": 3,
            "raw_success_rate": 0.666667,
            "support_state": "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED",
            "admitted_independent_support_count": 0,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
        },
        "counterevidence": {
            "visible_failure_sequence_refs": ["seq_f1"],
            "comparable_counterexample_refs": ["coc_1"],
            "comparable_counterexample_pair_count": 1,
            "same_visible_outcome_pair_refs": [],
            "counterexample_pair_count_is_independent_evidence_count": False,
            "independent_counterevidence_support_count": 0,
            "absence_used_as_counterevidence": False,
        },
        "evidence_sufficiency": {
            "state": "INSUFFICIENT_FOR_PROFESSIONAL_EMIT",
            "blocking_dimensions": ["INDEPENDENT_SUPPORT_NOT_ADMITTED"],
        },
        "alternative_explanations": [
            {
                "code": "SHARED_ANCHOR_DEPENDENCY",
                "meaning": "Visible branches share one admitted anchor.",
            }
        ],
        "safe_meaning": "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
        "forbidden_inference": ["TACTICAL_PATTERN_TRUTH", "CAUSALITY"],
        "uncertainty": {
            "independent_support_count": 0,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
        },
        "withdrawal_conditions": ["WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED"],
        "analyst_action": "REVIEW_BRANCH_EXAMPLES",
        "analyst_summary_tr": "Bu maçta görünür varyasyon gözlendi.",
        "safe_finding_handoff_is_professional_finding_truth": False,
        "safe_finding_handoff_is_tactical_truth": False,
        "safe_finding_handoff_is_causal_truth": False,
        "safe_finding_handoff_is_coach_intention_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _sequence_payload() -> dict:
    return {
        "safe_finding_handoff_candidates": [_handoff()],
        "safe_finding_handoff_professional_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_projects_existing_safe_finding_without_new_evidence_or_mechanism() -> None:
    result = build_puzzle_finding_contract(_sequence_payload())

    assert result["status"] == "PASS"
    assert result["puzzle_finding_count"] == 1
    assert result["creates_new_evidence"] is False
    assert result["creates_new_finding"] is False
    assert result["cross_mechanism_fusion_performed"] is False
    assert result["mechanism_candidate_emitted"] is False
    assert result["game_state_conditioning_ready"] is False

    finding = result["puzzle_findings"][0]
    assert finding["puzzle_id"] == "P6_PROCESS_VARIANT_DIVERGENCE"
    assert finding["puzzle_family"] == "PROCESS_VARIANT_AND_DIVERGENCE"
    assert finding["finding_status"] == "NOT_EVALUATED"
    assert finding["discovery_surface"]["visible_success_sequence_refs"] == ["seq_s1", "seq_s2"]
    assert finding["comparison_surface"]["eligible_denominator"] == 3
    assert finding["falsification_surface"]["comparable_counterexample_refs"] == ["coc_1"]
    assert finding["falsification_surface"]["absence_used_as_counterevidence"] is False
    assert finding["evolution_surface"]["score_state"] == "NOT_AVAILABLE"
    assert finding["fusion_surface"]["dependency_state"] == "INDEPENDENCE_UNKNOWN"
    assert finding["fusion_surface"]["same_process_truth"] is False
    assert finding["fusion_surface"]["mechanism_candidate_truth"] is False
    assert finding["canonical_event_count"] == "UNKNOWN"
    assert finding["true_action_count"] == "UNKNOWN"
    assert finding["production_release"] is False


def test_consumes_downward_safe_finding_admission_without_promoting_claim() -> None:
    admission = {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_test",
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
                "claim_ceiling": "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = build_puzzle_finding_contract(_sequence_payload(), admission)

    assert result["status"] == "PASS"
    finding = result["puzzle_findings"][0]
    assert finding["finding_status"] == "DOWNGRADE"
    assert finding["claim_output_allowed"] is False
    assert finding["admission_claim_ceiling"] == "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
    assert result["puzzle_finding_status_counts"] == {"DOWNGRADE": 1}


def test_fail_closed_on_sequence_truth_lock_breach() -> None:
    sequence = _sequence_payload()
    sequence["production_release"] = True

    result = build_puzzle_finding_contract(sequence)

    assert result["status"] == "FAIL_CLOSED"
    assert result["puzzle_findings"] == []
    assert result["puzzle_finding_count"] == 0
    assert "sequence_production_release_claimed" in result["hard_block_hits"]
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_optional_game_state_context_enriches_evolution_without_changing_claim_gate():
    sequence = _sequence_payload()
    admission = {
        "status": "PASS",
        "production_release": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_test",
            "decision": "DOWNGRADE",
            "claim_output_allowed": False,
            "claim_ceiling": "NO_CLAIM_OUTPUT",
        }],
    }
    context = {
        "game_state_process_mix_context": {
            "status": "PASS",
            "profiles": [{
                "team_identity_candidate_id": "team_a",
                "score_state_candidate": {"Alpha": 1, "Beta": 0},
                "segment_start_second_candidate": 0.0,
                "segment_end_second_candidate": 1000.0,
                "segment_duration_second_candidate": 1000.0,
                "process_family_counts": {"POSITIONAL_ATTACK_CANDIDATE": 10},
                "process_family_rate_per_10_minutes": {"POSITIONAL_ATTACK_CANDIDATE": 6.0},
            }],
        }
    }
    # align source fixture team/time if fixture uses different values
    handoff = sequence["safe_finding_handoff_candidates"][0]
    handoff.setdefault("where_when", {})["team_identity_candidate_id"] = "team_a"
    handoff["where_when"]["shared_anchor_time_candidate"] = 500.0
    result = build_puzzle_finding_contract(sequence, admission, context)
    finding = result["puzzle_findings"][0]
    assert finding["finding_status"] == "DOWNGRADE"
    assert finding["claim_output_allowed"] is False
    evo = finding["evolution_surface"]
    assert evo["game_state_conditioning_ready"] is True
    assert evo["score_state"] == {"Alpha": 1, "Beta": 0}
    assert evo["score_state_is_causal_explanation"] is False
    assert evo["creates_independent_support"] is False
    assert result["game_state_conditioning_ready"] is True
