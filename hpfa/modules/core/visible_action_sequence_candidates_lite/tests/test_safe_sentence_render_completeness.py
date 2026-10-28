from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_sentence_render_completeness import (
    COMPLETE_BOUNDED_RENDER,
    FACT_ONLY_RENDER,
    INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED,
    build_source_bound_render_contract,
    validate_safe_sentence_render,
)


def _source(decision="DOWNGRADE", scope="MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY"):
    return {
        "analyst_output_contract_id": "aoc_test",
        "source_safe_finding_handoff_ref": "sfh_test",
        "claim_scope": scope,
        "safe_finding_admission_decision": decision,
        "professional_emit_allowed": decision == "EMIT",
        "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
        "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
        "variant_feature_challenge_counter_scenario_candidates": ["counter_1"],
        "variant_feature_challenge_withdrawal_condition_candidates": ["withdraw_1"],
        "counter_scenario_candidates": ["core_counter"],
        "withdrawal_condition_candidates": ["core_withdraw"],
        "render_what_visible_text_tr": "Bu maçta aynı görünür başlangıçtan 5 uygun vaka gözlendi.",
        "render_safe_meaning": "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
        "render_analyst_action": "REVIEW_BRANCH_EXAMPLES",
        "render_evidence_refs": ["e1"],
        "render_counterevidence_refs": ["ce1"],
        "analyst_or_llm_text_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _render(**overrides):
    payload = {
        "source_analyst_output_contract_ref": "aoc_test",
        "sentence_type": "INTERPRETIVE",
        "what_visible": "Bu maçta admitted görünür örneklerde X farkı görüldü.",
        "safe_meaning": "Bu match-local observed variation candidate olarak okunabilir.",
        "claim_limiter": "Tactical-pattern truth veya causality değildir.",
        "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
        "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
        "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
        "counter_scenarios": ["core_counter", "counter_1"],
        "withdrawal_conditions": ["core_withdraw", "withdraw_1"],
        "evidence_refs": ["e1"],
        "counterevidence_refs": ["ce1"],
        "render_creates_new_evidence": False,
        "render_authorizes_emit": False,
        "professional_emit_allowed": False,
        "analyst_or_llm_text_is_evidence": False,
        "absence_is_counterevidence": False,
    }
    payload.update(overrides)
    return payload


def test_complete_bounded_sentence_passes():
    result = validate_safe_sentence_render(_source(), _render())
    assert result["render_completeness_state"] == COMPLETE_BOUNDED_RENDER
    assert result["render_allowed"] is True


def test_missing_claim_limiter_blocks_interpretive_render():
    result = validate_safe_sentence_render(_source(), _render(claim_limiter=""))
    assert result["render_completeness_state"] == INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED
    assert "interpretive_claim_limiter_missing" in result["blocking_reasons"]


def test_missing_required_counter_scenario_blocks():
    result = validate_safe_sentence_render(_source(), _render(counter_scenarios=[]))
    assert "required_counter_scenario_missing" in result["blocking_reasons"]
    assert result["render_allowed"] is False


def test_missing_required_withdrawal_condition_blocks():
    result = validate_safe_sentence_render(_source(), _render(withdrawal_conditions=[]))
    assert "required_withdrawal_condition_missing" in result["blocking_reasons"]


def test_fact_only_visible_observation_can_render_without_interpretation():
    render = _render(
        sentence_type="FACT_ONLY",
        safe_meaning="",
        claim_limiter="",
        counter_scenarios=[],
        withdrawal_conditions=[],
        required_qualifiers=[],
        forbidden_claim_families=[],
        evidence_refs=["e1"],
    )
    result = validate_safe_sentence_render(_source(), render)
    assert result["render_completeness_state"] == FACT_ONLY_RENDER
    assert result["render_allowed"] is True


def test_abstain_cannot_produce_interpretive_prose():
    result = validate_safe_sentence_render(_source(decision="ABSTAIN", scope="NO_CLAIM_OUTPUT"), _render(claim_scope="NO_CLAIM_OUTPUT"))
    assert "source_abstain_blocks_interpretive_render" in result["blocking_reasons"]
    assert result["render_allowed"] is False


def test_downgrade_cannot_render_stronger_scope():
    result = validate_safe_sentence_render(
        _source(decision="DOWNGRADE"),
        _render(claim_scope="DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"),
    )
    assert "render_claim_scope_stronger_than_source" in result["blocking_reasons"]


def test_emit_still_requires_qualifiers_and_forbidden_families():
    source = _source(decision="EMIT", scope="DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY")
    result = validate_safe_sentence_render(
        source,
        _render(
            claim_scope="DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY",
            required_qualifiers=[],
            forbidden_claim_families=[],
        ),
    )
    assert "required_qualifiers_not_preserved" in result["blocking_reasons"]
    assert "forbidden_claim_families_not_preserved" in result["blocking_reasons"]


def test_renderer_cannot_invent_evidence_or_safety_components():
    result = validate_safe_sentence_render(
        _source(),
        _render(
            evidence_refs=["e1", "invented_evidence"],
            counterevidence_refs=["ce1", "invented_counterevidence"],
            counter_scenarios=["core_counter", "counter_1", "invented_counter"],
            withdrawal_conditions=["core_withdraw", "withdraw_1", "invented_withdrawal"],
        ),
    )
    assert "render_invented_evidence_ref" in result["blocking_reasons"]
    assert "render_invented_counterevidence_ref" in result["blocking_reasons"]
    assert "render_invented_counter_scenario" in result["blocking_reasons"]
    assert "render_invented_withdrawal_condition" in result["blocking_reasons"]


def test_render_pass_never_increases_independent_support_or_authorizes_emit():
    result = validate_safe_sentence_render(_source(), _render())
    assert result["render_pass_increases_independent_support"] is False
    assert result["render_pass_authorizes_emit"] is False
    assert result["render_can_authorize_emit"] is False


def test_text_never_becomes_evidence():
    result = validate_safe_sentence_render(_source(), _render())
    assert result["analyst_or_llm_text_is_evidence"] is False
    assert result["render_creates_new_evidence"] is False


def test_fact_only_fallback_is_available_when_interpretive_render_is_incomplete():
    result = validate_safe_sentence_render(_source(), _render(claim_limiter=""))
    assert result["render_allowed"] is False
    assert result["fallback_allowed"] is True
    assert result["fallback_mode"] == FACT_ONLY_RENDER


def test_source_bound_builder_preserves_core_and_challenge_safety_terms():
    source = _source()
    rendered = build_source_bound_render_contract(source)
    result = validate_safe_sentence_render(source, rendered)

    assert rendered["counter_scenarios"] == ["core_counter", "counter_1"]
    assert rendered["withdrawal_conditions"] == ["core_withdraw", "withdraw_1"]
    assert rendered["evidence_refs"] == ["e1"]
    assert rendered["counterevidence_refs"] == ["ce1"]
    assert rendered["render_creates_new_evidence"] is False
    assert rendered["render_authorizes_emit"] is False
    assert result["render_completeness_state"] == COMPLETE_BOUNDED_RENDER
    assert result["render_allowed"] is True
    assert "Alternatif açıklamalar:" in rendered["rendered_sentence_tr"]
    assert "Geri çekme koşulları:" in rendered["rendered_sentence_tr"]


def test_source_bound_builder_abstain_downgrades_to_fact_only():
    source = _source(decision="ABSTAIN", scope="NO_CLAIM_OUTPUT")
    rendered = build_source_bound_render_contract(source)
    result = validate_safe_sentence_render(source, rendered)

    assert rendered["sentence_type"] == "FACT_ONLY"
    assert rendered["safe_meaning"] is None
    assert result["render_completeness_state"] == FACT_ONLY_RENDER
    assert result["render_allowed"] is True


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "safe_sentence_render_completeness.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Fenerbahçe", "Roma", "09.09.2026", "10.09.2026"):
        assert token not in source
