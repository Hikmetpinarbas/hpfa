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
