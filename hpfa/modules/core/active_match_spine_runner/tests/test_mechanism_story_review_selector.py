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
