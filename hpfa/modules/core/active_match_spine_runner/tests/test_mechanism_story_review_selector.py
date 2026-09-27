import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mechanism_story_review_selector import build_mechanism_story_review_shortlist


def _row(ref, team, period, grammar, *, process=True, consequence=True, censored=0):
    return {
        "grammar_stable_variant_feature_delta_id": ref,
        "source_process_variant_family_ref": f"family_{ref}",
        "team_identity_candidate_ids": [team],
        "period_candidates": [period],
        "grammar_signature_tokens": grammar,
        "resolved_variant_count": 4,
        "success_resolved_variant_count": 3,
        "failure_resolved_variant_count": 1,
        "right_censored_variant_count": censored,
        "first_supported_context_difference_layer_candidate": 0,
        "first_supported_consequence_difference_layer_candidate": 1,
        "process_context_feature_difference_candidates": [{"feature_token": "process_family_candidate:X"}] if process else [],
        "consequence_feature_difference_candidates": [{"feature_token": "opponent_handover"}] if consequence else [],
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
    }


def test_selector_prefers_rich_candidates_and_preserves_diversity_without_truth_ranking():
    payload = {
        "grammar_stable_variant_feature_delta_records": [
            _row("b", "T1", "1", ["LAYER[PASS]", "LAYER[PASS]"], process=False),
            _row("a", "T1", "1", ["LAYER[RECOVERY]", "LAYER[PASS]"], process=True),
            _row("c", "T1", "1", ["LAYER[RECOVERY]", "LAYER[PASS]"], process=True),
            _row("d", "T2", "2", ["LAYER[DUEL]", "LAYER[PASS]"], process=True),
        ]
    }
    result = build_mechanism_story_review_shortlist(payload, limit=5)

    assert result["status"] == "PASS"
    assert result["shortlist_count"] == 3
    assert [row["source_mechanism_review_ref"] for row in result["shortlist"]] == ["a", "d", "b"]
    assert result["selection_is_truth_ranking"] is False
    assert result["selection_is_confidence_score"] is False
    assert result["selection_can_authorize_emit"] is False
    assert result["analyst_relevance_state"] == "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION"



def test_selector_uses_one_attention_slot_per_grammar_across_team_period_contexts():
    payload = {
        "grammar_stable_variant_feature_delta_records": [
            _row("a", "T1", "1", ["LAYER[PASS]", "LAYER[PASS]"]),
            _row("b", "T2", "2", ["LAYER[PASS]", "LAYER[PASS]"]),
            _row("c", "T1", "2", ["LAYER[RECOVERY]", "LAYER[PASS]"]),
        ]
    }
    result = build_mechanism_story_review_shortlist(payload, limit=5)

    assert result["shortlist_count"] == 2
    assert [row["source_mechanism_review_ref"] for row in result["shortlist"]] == ["a", "c"]
    assert result["diversity_basis"] == "UNIQUE_GRAMMAR_SIGNATURE_ATTENTION_SLOT"
    assert result["same_grammar_contexts_are_separate_comparison_not_extra_mechanism_slots"] is True


def test_selector_blocks_censored_or_single_outcome_candidates():
    blocked = _row("blocked", "T1", "1", ["LAYER[PASS]"], censored=1)
    one_sided = _row("one", "T2", "1", ["LAYER[PASS]"])
    one_sided["failure_resolved_variant_count"] = 0
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [blocked, one_sided]}
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["shortlist_count"] == 0
    assert result["reason"] == "no_eligible_mechanism_review_candidates"


def test_selector_limit_is_attention_limit_not_evidence_threshold():
    payload = {
        "grammar_stable_variant_feature_delta_records": [
            _row("a", "T1", "1", ["LAYER[RECOVERY]", "LAYER[PASS]"]),
            _row("b", "T2", "1", ["LAYER[CARRY]", "LAYER[PASS]"]),
            _row("c", "T1", "2", ["LAYER[DUEL]", "LAYER[PASS]"]),
        ]
    }
    result = build_mechanism_story_review_shortlist(payload, limit=2)

    assert result["shortlist_count"] == 2
    assert all(row["selection_role"] == "ANALYST_REVIEW_ATTENTION_ONLY" for row in result["shortlist"])
    assert all(row["selection_can_authorize_emit"] is False for row in result["shortlist"])


def _bound_contract(family_ref="family_blocked", *, lower=0.5, upper=0.75):
    return {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [
            {
                "analyst_output_contract_id": "aoc_sfh_1",
                "rate_bound_binding_state": "SOURCE_BOUND_NUMERIC",
                "rate_bound_state": "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE",
                "rate_bound_estimand_id": "MATCH_LOCAL_VISIBLE_PROCESS_OUTCOME_RATE",
                "rate_bound_denominator_basis": "UNIQUE_OBSERVABLE_PROCESS_VARIANT_FAMILY_MEMBER_SEQUENCE_REFS",
                "rate_bound_resolved_success_n": 2,
                "rate_bound_resolved_failure_n": 1,
                "rate_bound_unresolved_eligible_n": 1,
                "rate_bound_eligible_total_n": 4,
                "rate_bound_lower": lower,
                "rate_bound_upper": upper,
                "rate_bound_width": upper - lower,
                "rate_bound_assumption_set_id": "BINARY_VISIBLE_OUTCOME_KNOWN_ELIGIBLE_DENOMINATOR_WORST_CASE_UNRESOLVED_V1",
                "rate_bound_matched_process_variant_family_refs": [family_ref],
                "rate_bound_can_authorize_emit": False,
                "rate_bound_can_strengthen_claim_ceiling": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_selector_allows_censored_family_only_as_bound_aware_review():
    censored = _row("blocked", "T1", "1", ["LAYER[PASS]"], censored=1)
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [censored]},
        analyst_output_claim_payload=_bound_contract(),
    )

    assert result["status"] == "PASS"
    assert result["shortlist_count"] == 1
    assert result["bounded_review_only_count"] == 1
    row = result["shortlist"][0]
    assert row["story_eligibility_state"] == "BOUND_AWARE_REVIEW_ONLY"
    assert row["priority_band"] == "BOUND_AWARE_REVIEW_ONLY"
    assert row["rate_bound_lower"] == 0.5
    assert row["rate_bound_upper"] == 0.75
    assert row["selection_can_authorize_emit"] is False
    assert row["selection_is_confidence_score"] is False
    assert result["bound_recomputed_in_selector"] is False
    assert result["bound_width_is_confidence_score"] is False


def test_selector_keeps_censored_family_blocked_without_aligned_bound():
    censored = _row("blocked", "T1", "1", ["LAYER[PASS]"], censored=1)
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [censored]},
        analyst_output_claim_payload=_bound_contract("different_family"),
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["shortlist_count"] == 0


def test_selector_rejects_ambiguous_conflicting_bounds_for_same_family():
    censored = _row("blocked", "T1", "1", ["LAYER[PASS]"], censored=1)
    payload = _bound_contract()
    second = dict(payload["analyst_output_contracts"][0])
    second["analyst_output_contract_id"] = "aoc_sfh_2"
    second["rate_bound_upper"] = 1.0
    second["rate_bound_width"] = 0.5
    payload["analyst_output_contracts"].append(second)

    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [censored]},
        analyst_output_claim_payload=payload,
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["shortlist_count"] == 0


def test_selector_attention_prefers_multi_episode_divergence_without_truth_ranking():
    single = _row("a_single", "T1", "1", ["LAYER[PASS]", "LAYER[PASS]"])
    single.update({
        "visible_episode_spread_count": 1,
        "occurrence_disjoint_support_cluster_count": 1,
        "supported_branch_divergence_binding_count": 2,
        "success_failure_supported_branch_divergence_count": 1,
    })
    multi = _row("z_multi", "T2", "1", ["LAYER[CARRY]", "LAYER[PASS]"])
    multi.update({
        "visible_episode_spread_count": 4,
        "success_visible_episode_spread_count": 4,
        "failure_visible_episode_spread_count": 2,
        "occurrence_disjoint_support_cluster_count": 4,
        "supported_branch_divergence_binding_count": 3,
        "success_failure_supported_branch_divergence_count": 1,
    })
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [single, multi]},
        limit=1,
    )
    assert result["shortlist"][0]["source_mechanism_review_ref"] == "z_multi"
    row = result["shortlist"][0]
    assert row["review_support_state"] == (
        "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    )
    assert row["review_support_state_is_truth_ranking"] is False
    assert row["episode_spread_count_is_independent_support_count"] is False
    assert result["review_support_attention_order_is_truth_ranking"] is False


def test_selector_binds_source_process_context_by_same_episode_team_period_without_promoting_truth():
    row = _row("ctx", "T1", "1", ["LAYER[INTERCEPTION]", "LAYER[PASS]"])
    row["source_process_variant_family_ref"] = "family_ctx"
    variant_payload = {
        "status": "PASS",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_ctx",
                "team_identity_candidate_ids": ["T1"],
                "period_candidates": ["1"],
                "visible_episode_candidate_ids": ["E1", "E2"],
            }
        ],
    }
    process_payload = {
        "status": "PASS",
        "process_participation_candidates": [
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E1",
                "team_identity_candidate_id": "T1",
                "period_candidate": "1",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            },
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E2",
                "team_identity_candidate_id": "T1",
                "period_candidate": "1",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            },
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E2",
                "team_identity_candidate_id": "T2",
                "period_candidate": "1",
                "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            },
        ],
    }

    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [row]},
        process_variant_payload=variant_payload,
        process_participation_payload=process_payload,
    )

    selected = result["shortlist"][0]
    assert selected["process_context_binding_state"] == "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT"
    assert selected["single_process_family_candidate"] == "POSITIONAL_ATTACK_CANDIDATE"
    assert selected["process_family_episode_presence_counts"] == {"POSITIONAL_ATTACK_CANDIDATE": 2}
    assert selected["process_context_visible_episode_count"] == 2
    assert selected["process_context_bound_episode_count"] == 2
    assert selected["process_context_ambiguous_episode_count"] == 0
    assert selected["process_family_episode_presence_count_is_independent_support_count"] is False
    assert selected["process_context_binding_is_process_identity_truth"] is False
    assert selected["process_context_binding_is_tactical_pattern_truth"] is False
    assert selected["process_context_binding_is_causal_mechanism_truth"] is False
    assert selected["process_context_binding_can_authorize_emit"] is False


def test_selector_preserves_multi_process_context_ambiguity_instead_of_forcing_one_family():
    row = _row("amb", "T1", "2", ["LAYER[PASS]", "LAYER[PASS]"])
    row["source_process_variant_family_ref"] = "family_amb"
    variant_payload = {
        "status": "PASS",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_amb",
                "team_identity_candidate_ids": ["T1"],
                "period_candidates": ["2"],
                "visible_episode_candidate_ids": ["E1", "E2"],
            }
        ],
    }
    process_payload = {
        "status": "PASS",
        "process_participation_candidates": [
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E1",
                "team_identity_candidate_id": "T1",
                "period_candidate": "2",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            },
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E2",
                "team_identity_candidate_id": "T1",
                "period_candidate": "2",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            },
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "episode_candidate_id": "E2",
                "team_identity_candidate_id": "T1",
                "period_candidate": "2",
                "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            },
        ],
    }

    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [row]},
        process_variant_payload=variant_payload,
        process_participation_payload=process_payload,
    )
    selected = result["shortlist"][0]
    assert selected["process_context_binding_state"] == "AMBIGUOUS_MULTI_PROCESS_FAMILY_CONTEXT"
    assert selected["single_process_family_candidate"] is None
    assert selected["process_context_ambiguous_episode_count"] == 1
    assert selected["process_family_episode_presence_counts"] == {
        "COUNTERATTACK_CANDIDATE": 1,
        "POSITIONAL_ATTACK_CANDIDATE": 2,
    }


def test_selector_binds_source_challenge_summary_without_creating_evidence_or_emit_authority():
    row = _row("challenge", "T1", "1", ["LAYER[PASS]", "LAYER[PASS]"])
    challenge_payload = {
        "status": "PASS",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "vfc_1",
                "source_feature_delta_record_ref": "challenge",
                "feature_surface": "CONTEXT",
                "challenge_reasons": ["DEPENDENCY_INDEPENDENCE_UNPROVEN"],
                "counter_scenario_candidates": ["SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"],
                "withdrawal_conditions": ["WITHDRAW_IF_CONTEXT_DIFFERENCE_DISAPPEARS"],
                "context_scope_state": "SINGLE_TEAM_SINGLE_PERIOD_SCOPE",
                "partition_visibility_state": "VISIBLE_IN_BOTH_OUTCOME_PARTITIONS",
                "professional_finding_emit_allowed": False,
                "hypothesis_candidate_is_truth": False,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            },
            {
                "variant_feature_challenge_id": "vfc_2",
                "source_feature_delta_record_ref": "challenge",
                "feature_surface": "CONSEQUENCE",
                "challenge_reasons": ["CONTEXT_ROBUSTNESS_NOT_TESTED"],
                "counter_scenario_candidates": ["OPPONENT_BEHAVIOUR_OR_SCORE_STATE_MAY_EXPLAIN_DIFFERENCE"],
                "withdrawal_conditions": ["WITHDRAW_IF_HORIZON_CHANGES_DIFFERENCE"],
                "context_scope_state": "SINGLE_TEAM_SINGLE_PERIOD_SCOPE",
                "partition_visibility_state": "VISIBLE_IN_ONE_OUTCOME_PARTITION_ONLY",
                "professional_finding_emit_allowed": False,
                "hypothesis_candidate_is_truth": False,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            },
            {
                "variant_feature_challenge_id": "vfc_other",
                "source_feature_delta_record_ref": "other",
                "feature_surface": "CONTEXT",
                "challenge_reasons": ["SHOULD_NOT_BIND"],
                "counter_scenario_candidates": ["SHOULD_NOT_BIND"],
                "withdrawal_conditions": ["SHOULD_NOT_BIND"],
                "professional_finding_emit_allowed": False,
                "hypothesis_candidate_is_truth": False,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            },
        ],
    }

    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [row]},
        variant_feature_challenge_payload=challenge_payload,
    )

    selected = result["shortlist"][0]
    assert selected["mechanism_challenge_binding_state"] == "SOURCE_BOUND_VARIANT_FEATURE_CHALLENGE_AVAILABLE"
    assert selected["mechanism_challenge_record_count"] == 2
    assert selected["mechanism_challenge_feature_surface_counts"] == {"CONSEQUENCE": 1, "CONTEXT": 1}
    assert selected["mechanism_challenge_reason_codes"] == [
        "CONTEXT_ROBUSTNESS_NOT_TESTED",
        "DEPENDENCY_INDEPENDENCE_UNPROVEN",
    ]
    assert selected["mechanism_counter_scenario_candidates"] == [
        "OPPONENT_BEHAVIOUR_OR_SCORE_STATE_MAY_EXPLAIN_DIFFERENCE",
        "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE",
    ]
    assert selected["mechanism_withdrawal_conditions"] == [
        "WITHDRAW_IF_CONTEXT_DIFFERENCE_DISAPPEARS",
        "WITHDRAW_IF_HORIZON_CHANGES_DIFFERENCE",
    ]
    assert selected["mechanism_challenge_all_professional_finding_emit_disallowed"] is True
    assert selected["mechanism_challenge_all_hypothesis_candidate_truth_false"] is True
    assert selected["mechanism_challenge_dependency_independence_proven"] is False
    assert selected["mechanism_challenge_statistical_independence_proven"] is False
    assert selected["mechanism_challenge_records_are_independent_evidence_votes"] is False
    assert selected["mechanism_challenge_summary_is_counterfactual_truth"] is False
    assert selected["mechanism_challenge_summary_is_causal_explanation"] is False
    assert selected["mechanism_challenge_can_authorize_emit"] is False



def _safe_review_contract(family_ref, *, spread, challenge, bound, outcome_debt=False, ref_suffix="1"):
    blocking = ["CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN", "DEPENDENCY_INDEPENDENCE_NOT_PROVEN", "INDEPENDENT_SUPPORT_NOT_ADMITTED", "STATISTICAL_INDEPENDENCE_NOT_PROVEN"]
    if outcome_debt:
        blocking.extend(["OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN", "UNRESOLVED_OUTCOME_BURDEN"])
    return {
        "analyst_output_contract_id": f"aoc_{ref_suffix}",
        "safe_finding_admission_decision": "DOWNGRADE",
        "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
        "blocking_dimensions": blocking,
        "variant_support_episode_spread_observed": spread,
        "variant_support_spread_profiles": [{"family_ref": family_ref}] if spread else [],
        "variant_feature_challenge_binding_state": "MATCHED_CHALLENGE_VISIBLE" if challenge else "NO_MATCHED_CHALLENGE",
        "variant_feature_challenge_refs": [f"vfc_{ref_suffix}"] if challenge else [],
        "variant_feature_challenge_family_refs": [family_ref] if challenge else [],
        "rate_bound_binding_state": "SOURCE_BOUND_NUMERIC" if bound else "NOT_AVAILABLE",
        "rate_bound_state": "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE" if bound else None,
        "rate_bound_estimand_id": "MATCH_LOCAL_VISIBLE_PROCESS_OUTCOME_RATE" if bound else None,
        "rate_bound_denominator_basis": "UNIQUE_OBSERVABLE_PROCESS_VARIANT_FAMILY_MEMBER_SEQUENCE_REFS" if bound else None,
        "rate_bound_resolved_success_n": 3 if bound else None,
        "rate_bound_resolved_failure_n": 1 if bound else None,
        "rate_bound_unresolved_eligible_n": 0 if bound else None,
        "rate_bound_eligible_total_n": 4 if bound else None,
        "rate_bound_lower": 0.75 if bound else None,
        "rate_bound_upper": 0.75 if bound else None,
        "rate_bound_width": 0.0 if bound else None,
        "rate_bound_assumption_set_id": "BINARY_VISIBLE_OUTCOME_KNOWN_ELIGIBLE_DENOMINATOR_WORST_CASE_UNRESOLVED_V1" if bound else None,
        "rate_bound_matched_process_variant_family_refs": [family_ref] if bound else [],
        "rate_bound_can_authorize_emit": False,
        "rate_bound_can_strengthen_claim_ceiling": False,
    }


def test_safe_finding_review_readiness_prioritizes_attention_inside_same_mechanism_band_only():
    low = _row("a_low", "T1", "1", ["LAYER[PASS]", "LAYER[PASS]"])
    high = _row("z_high", "T2", "1", ["LAYER[CARRY]", "LAYER[PASS]"])
    for row in (low, high):
        row.update({
            "visible_episode_spread_count": 3,
            "occurrence_disjoint_support_cluster_count": 3,
            "supported_branch_divergence_binding_count": 2,
            "success_failure_supported_branch_divergence_count": 1,
        })
    analyst = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [
            _safe_review_contract("family_a_low", spread=False, challenge=False, bound=False, ref_suffix="low"),
            _safe_review_contract("family_z_high", spread=True, challenge=True, bound=True, ref_suffix="high"),
        ],
        "production_release": False,
    }
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [low, high]},
        analyst_output_claim_payload=analyst,
        limit=1,
    )

    row = result["shortlist"][0]
    assert row["source_mechanism_review_ref"] == "z_high"
    assert row["safe_finding_review_readiness_band"] == "SF_R0_REVIEW_RICH_MATCH_LOCAL_DESCRIPTION"
    assert row["safe_finding_review_has_observed_episode_spread"] is True
    assert row["safe_finding_review_has_challenge_surface"] is True
    assert row["safe_finding_review_has_source_bound_rate"] is True
    assert row["safe_finding_review_has_outcome_debt"] is False
    assert row["safe_finding_review_readiness_is_truth_ranking"] is False
    assert row["safe_finding_review_readiness_is_confidence_score"] is False
    assert row["safe_finding_review_readiness_can_authorize_emit"] is False
    assert row["safe_finding_review_readiness_can_increase_support"] is False
    assert result["safe_finding_review_readiness_applied"] is True
    assert result["safe_finding_review_readiness_is_truth_ranking"] is False


def test_outcome_debt_prevents_review_rich_tier_without_blocking_match_local_attention():
    row = _row("debt", "T1", "1", ["LAYER[RECOVERY]", "LAYER[PASS]"])
    row.update({
        "visible_episode_spread_count": 4,
        "occurrence_disjoint_support_cluster_count": 4,
        "supported_branch_divergence_binding_count": 2,
        "success_failure_supported_branch_divergence_count": 1,
    })
    analyst = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [
            _safe_review_contract("family_debt", spread=True, challenge=True, bound=True, outcome_debt=True, ref_suffix="debt")
        ],
        "production_release": False,
    }
    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [row]},
        analyst_output_claim_payload=analyst,
    )

    selected = result["shortlist"][0]
    assert selected["safe_finding_review_readiness_band"] == "SF_R2_SUPPORTING_MATCH_LOCAL_CONTEXT"
    assert selected["safe_finding_review_has_outcome_debt"] is True
    assert selected["selection_can_authorize_emit"] is False
    assert selected["safe_finding_review_readiness_can_authorize_emit"] is False


def test_selector_exposes_dimensioned_evidence_maturity_without_composite_confidence_score():
    row = _row("mature", "T1", "1", ["LAYER[PASS]", "LAYER[CARRY]"])
    row.update({
        "resolved_variant_count": 8,
        "success_resolved_variant_count": 5,
        "failure_resolved_variant_count": 3,
        "right_censored_variant_count": 0,
        "visible_episode_spread_count": 4,
        "occurrence_disjoint_support_cluster_count": 3,
        "supported_branch_divergence_binding_count": 2,
        "success_failure_supported_branch_divergence_count": 1,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
    })

    result = build_mechanism_story_review_shortlist(
        {"grammar_stable_variant_feature_delta_records": [row]},
        limit=1,
    )

    profile = result["shortlist"][0]["evidence_maturity_profile"]
    assert profile["resolved_variant_denominator_n"] == 8
    assert profile["positive_visible_variant_n"] == 5
    assert profile["negative_visible_variant_n"] == 3
    assert profile["episode_spread_n"] == 4
    assert profile["occurrence_disjoint_support_cluster_n"] == 3
    assert profile["right_censored_variant_n"] == 0
    assert profile["success_failure_divergence_n"] == 1
    assert profile["dependency_independence_proven"] is False
    assert profile["counterevidence_present"] is True
    assert profile["maturity_is_confidence_score"] is False
    assert profile["maturity_can_authorize_emit"] is False
    assert "score" not in profile
    assert "confidence" not in profile
