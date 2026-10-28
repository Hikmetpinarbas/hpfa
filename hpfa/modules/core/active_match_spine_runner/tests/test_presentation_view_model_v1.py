from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.presentation_view_model import (
    build_presentation_view_model,
    render_professional_html,
)


def test_view_model_cannot_create_or_strengthen_evidence() -> None:
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED", "active_match_authority": "/runtime/current"},
        analyst_report_tr="Gözlenen rapor.",
        analyst_report_en="Observed report.",
        mechanism_graph_payload={
            "cards": [{
                "card_id": "c1",
                "graphability_state": "GRAPH_READY_WITH_REVIEW",
                "claim_ceiling": "MATCH_LOCAL_VISIBLE_CANDIDATE_ONLY",
                "graph_recommendations": ["VISIBLE_OUTCOME_SPLIT_BAR"],
            }]
        },
    )
    assert view["view_model_creates_new_evidence"] is False
    assert view["view_model_can_strengthen_claim_ceiling"] is False
    assert view["view_model_can_authorize_emit"] is False
    assert view["production_release"] is False
    assert view["canonical_event_count"] == "UNKNOWN"
    assert view["true_action_count"] == "UNKNOWN"
    assert view["mechanism_card_count"] == 1


def test_html_renderer_escapes_content_and_contains_no_active_script() -> None:
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED", "active_match_authority": "A&B"},
        analyst_report_tr="<script>alert(1)</script>",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
    )
    rendered = render_professional_html(view, language="tr")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>" not in rendered
    assert "A&amp;B" in rendered
    assert "production_release=false" in rendered
    assert "presentation cannot strengthen claim ceiling" in rendered


def test_fact_only_review_preserves_denominator_counterevidence_and_withdrawal() -> None:
    payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contract_count": 1,
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_1",
            "professional_emit_allowed": False,
            "safe_finding_admission_decision": "ABSTAIN",
            "rate_bound_eligible_total_n": 3,
            "rate_bound_resolved_success_n": 2,
            "rate_bound_resolved_failure_n": 1,
            "rate_bound_unresolved_eligible_n": 0,
            "rate_bound_estimand_id": "TEST_VISIBLE_OUTCOME_RATE",
            "rate_bound_denominator_basis": "TEST_ELIGIBLE_FAMILY_MEMBERS",
            "rate_bound_state": "PARTIALLY_IDENTIFIED_SAMPLE_DESCRIPTION",
            "rate_bound_lower": 0.66,
            "rate_bound_upper": 0.66,
            "rate_bound_is_confidence_interval": False,
            "rate_bound_is_true_probability": False,
            "rate_bound_is_population_rate": False,
        }],
        "source_bound_render_contracts": [{
            "source_analyst_output_contract_ref": "aoc_1",
            "final_human_sentence_tr": "3 uygun vakanın 2 tanesinde SUCCESS görünür.",
            "render_validation": {
                "render_allowed": True,
                "render_completeness_state": "FACT_ONLY_RENDER",
                "rendered_claim_scope": "NO_CLAIM_OUTPUT",
                "rendered_counterevidence_refs": ["counter_1"],
                "counter_scenarios": ["SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"],
                "withdrawal_conditions": ["WITHDRAW_IF_DENOMINATOR_INVALID"],
                "rendered_required_qualifiers": ["MATCH_LOCAL"],
                "rendered_forbidden_claim_families": ["CAUSALITY"],
            },
            "rendered_sentence_contract": {
                "professional_emit_allowed": False,
                "source_analyst_output_contract_ref": "aoc_1",
                "sentence_type": "FACT_ONLY",
                "claim_scope": "NO_CLAIM_OUTPUT",
                "rendered_sentence_tr": "3 uygun vakanın 2 tanesinde SUCCESS görünür.",
                "counterevidence_refs": ["counter_1"],
                "counter_scenarios": ["SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"],
                "withdrawal_conditions": ["WITHDRAW_IF_DENOMINATOR_INVALID"],
                "required_qualifiers": ["MATCH_LOCAL"],
                "forbidden_claim_families": ["CAUSALITY"],
            },
        }],
    }

    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=payload,
    )

    assert view["claim_admission_summary"]["professional_emit_allowed_count"] == 0
    assert view["claim_admission_summary"]["fact_only_render_count"] == 1
    record = view["fact_review_records"][0]
    assert record["rendered_observation_counts"]["status"] == "UNAVAILABLE_AS_STRUCTURED_FIELDS"
    assert record["rate_bound_context"]["eligible_total_n"] == 3
    assert record["rate_bound_context"]["resolved_success_n"] == 2
    assert record["rate_bound_context"]["resolved_failure_n"] == 1
    assert record["rate_bound_context"]["unresolved_eligible_n"] == 0
    assert record["rate_bound_context"]["is_denominator_for_rendered_sentence"] is False
    assert record["counterevidence_refs"] == ["counter_1"]
    assert record["counter_scenarios"] == ["SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"]
    assert record["withdrawal_conditions"] == ["WITHDRAW_IF_DENOMINATOR_INVALID"]
    assert record["observed_sample_description_only"] is True
    assert record["record_can_authorize_emit"] is False

    rendered = render_professional_html(view)
    assert ">0</strong>Professional claims admitted" in rendered
    assert ">1</strong>Fact-only review records" in rendered
    assert "Observed sample description only" in rendered
    assert "Rendered observation denominator: UNAVAILABLE_AS_STRUCTURED_FIELDS" in rendered
    assert "Separate rate-bound context" in rendered
    assert "eligible=3" in rendered
    assert "not the denominator of the rendered sentence" in rendered
    assert "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE" in rendered


def test_zero_professional_claim_report_is_explicitly_review_narrative_not_admitted_finding() -> None:
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED", "active_match_authority": "/runtime/current"},
        analyst_report_tr="Maç okuma sentezi.",
        analyst_report_en="Match-reading synthesis.",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload={
            "status": "REVIEW_REQUIRED",
            "analyst_output_contract_count": 2,
            "analyst_output_contracts": [],
            "source_bound_render_contracts": [],
        },
    )
    rendered = render_professional_html(view, language="tr")
    assert "Analist inceleme anlatısı" in rendered
    assert "profesyonel bulgu olarak kabul edilmemiştir" in rendered
    assert "Maç okuma sentezi." in rendered


def test_non_render_allowed_contract_is_not_promoted_to_fact_review() -> None:
    payload = {
        "analyst_output_contracts": [{"analyst_output_contract_id": "aoc_1"}],
        "source_bound_render_contracts": [{
            "source_analyst_output_contract_ref": "aoc_1",
            "render_validation": {
                "render_allowed": False,
                "render_completeness_state": "REVIEW_REQUIRED",
            },
            "rendered_sentence_contract": {
                "professional_emit_allowed": False,
                "source_analyst_output_contract_ref": "aoc_1",
            },
        }],
    }
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=payload,
    )
    assert view["fact_review_records"] == []
    assert view["claim_admission_summary"]["fact_only_render_count"] == 0


def test_match_local_descriptive_findings_are_deduplicated_and_rendered_without_claim_inflation():
    safe = {
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "match_local_descriptive_finding_admitted": True,
                "variant_feature_challenge_family_refs": ["family_1"],
                "variant_support_episode_spread_max_visible_count": 11,
                "actor_spread_count": 2,
                "decision": "DOWNGRADE",
                "branch_preoutcome_context_enrichment": {
                    "team_identity_candidate_id": "team_a",
                    "period_candidate": "1",
                    "score_state_candidate": {"Galatasaray (29205)": 0, "Trabzonspor (77018)": 1},
                    "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                    "anchor_action_family_counts": {"PASS": 1},
                    "shared_anchor_time_candidate": 100.0,
                },
            },
            {
                "source_safe_finding_handoff_ref": "sfh_2",
                "match_local_descriptive_finding_admitted": True,
                "variant_feature_challenge_family_refs": ["family_1"],
                "variant_support_episode_spread_max_visible_count": 11,
                "actor_spread_count": 2,
                "decision": "DOWNGRADE",
                "branch_preoutcome_context_enrichment": {
                    "team_identity_candidate_id": "team_a",
                    "period_candidate": "1",
                    "score_state_candidate": {"Galatasaray (29205)": 0, "Trabzonspor (77018)": 1},
                    "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                    "anchor_action_family_counts": {"PASS": 1},
                    "shared_anchor_time_candidate": 120.0,
                },
            },
        ]
    }
    identity = {
        "team_identity_candidates": [{
            "team_identity_candidate_id": "team_a",
            "team_aliases_raw": ["trabzonspor (77018)"],
            "team_normalized_key": "trabzonspor",
        }]
    }
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload={"status": "REVIEW_REQUIRED", "analyst_output_contracts": []},
        safe_finding_payload=safe,
        identity_payload=identity,
    )
    assert view["match_local_descriptive_finding_count"] == 1
    row = view["match_local_descriptive_findings"][0]
    assert row["source_handoff_count"] == 2
    assert row["team_name"] == "Trabzonspor"
    assert row["professional_emit_allowed"] is False
    rendered = render_professional_html(view, language="tr")
    assert "Maç-içi görünür mekanizma bulguları" in rendered
    assert "Trabzonspor" in rendered
    assert "taktik gerçek" in rendered

def test_unanswered_question_explains_why_without_strengthening_claim():
    claim_payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contract_count": 1,
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_sfh_1",
            "source_safe_finding_handoff_ref": "sfh_1",
            "professional_emit_allowed": False,
            "safe_finding_admission_decision": "DOWNGRADE",
            "evidence_sufficiency_state": "PARTIAL",
            "blocking_dimensions": ["FOLLOWUP_OBSERVATION_UNRESOLVED_BURDEN"],
            "safe_output_meaning": "MATCH_LOCAL_OBSERVED_VISIBLE_VARIATION_ONLY",
            "forbidden_claim_families": ["CAUSALITY"],
        }],
        "source_bound_render_contracts": [],
    }
    safe_payload = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_1",
            "decision": "DOWNGRADE",
            "decision_reasons": ["FOLLOWUP_OBSERVATION_UNRESOLVED_BURDEN"],
            "claim_output_allowed": False,
        }]
    }

    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload=safe_payload,
    )

    assert view["unanswered_question_explanation_count"] == 1
    row = view["unanswered_question_explanations"][0]
    assert row["question_id"] == "aoc_sfh_1"
    assert row["epistemic_state"] == "DOWNGRADE"
    assert "takip" in row["why_tr"].casefold()
    assert "takip" in row["required_observation_tr"].casefold()
    assert row["weaker_safe_statement_tr"]
    assert row["creates_new_evidence"] is False
    assert row["can_authorize_emit"] is False


def test_unknown_reason_is_not_invented_into_human_explanation():
    claim_payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_sfh_2",
            "source_safe_finding_handoff_ref": "sfh_2",
            "professional_emit_allowed": False,
            "safe_finding_admission_decision": "ABSTAIN",
            "evidence_sufficiency_state": "UNKNOWN",
            "blocking_dimensions": [],
            "safe_output_meaning": None,
        }],
        "source_bound_render_contracts": [],
    }
    safe_payload = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_2",
            "decision": "ABSTAIN",
            "decision_reasons": [],
            "claim_output_allowed": False,
        }]
    }

    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload=safe_payload,
    )

    row = view["unanswered_question_explanations"][0]
    assert row["why_tr"] == "Neden daha güçlü bir sonuca gidilemediği mevcut kanıttan güvenle çözülemiyor."
    assert row["required_observation_tr"] == "Gerekli ek gözlem mevcut kanıttan güvenle belirlenemiyor."
    assert row["weaker_safe_statement_tr"] == "Daha zayıf güvenli ifade mevcut kanıttan üretilemiyor."


def test_professional_emit_contract_does_not_create_unanswered_question_explanation():
    claim_payload = {
        "status": "PASS",
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_emit",
            "source_safe_finding_handoff_ref": "sfh_emit",
            "professional_emit_allowed": True,
            "safe_finding_admission_decision": "EMIT",
            "evidence_sufficiency_state": "SUFFICIENT",
        }],
        "source_bound_render_contracts": [],
    }

    view = build_presentation_view_model(
        {"status": "PASS"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload={"safe_finding_admission_decisions": []},
    )

    assert view["unanswered_question_explanations"] == []
    assert view["unanswered_question_explanation_count"] == 0


def test_html_renders_football_first_why_section():
    claim_payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_sfh_3",
            "source_safe_finding_handoff_ref": "sfh_3",
            "professional_emit_allowed": False,
            "safe_finding_admission_decision": "DOWNGRADE",
            "evidence_sufficiency_state": "PARTIAL",
            "blocking_dimensions": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
            "safe_output_meaning": "MATCH_LOCAL_OBSERVED_VISIBLE_VARIATION_ONLY",
        }],
        "source_bound_render_contracts": [],
    }
    safe_payload = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_3",
            "decision": "DOWNGRADE",
            "decision_reasons": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
            "claim_output_allowed": False,
        }]
    }
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload=safe_payload,
    )
    rendered = render_professional_html(view, language="tr")

    assert "HPFA neden daha fazlasını söylemiyor?" in rendered
    assert "Ne eksik?" in rendered
    assert "Güvenli olarak ne söyleyebiliriz?" in rendered
    assert "Analist ne yapmalı?" in rendered


def test_degraded_package_without_claim_contracts_explains_fail_closed_reason():
    view = build_presentation_view_model(
        {
            "status": "REVIEW_REQUIRED",
            "review_hits": ["variant_feature_challenge_runtime_binding_fail_closed"],
        },
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload={
            "status": "PASS",
            "analyst_output_contracts": [],
            "source_bound_render_contracts": [],
        },
        safe_finding_payload={
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["process_context_counterevidence_recompute_fail_closed"],
            "safe_finding_admission_decisions": [],
        },
    )

    assert view["unanswered_question_explanation_count"] == 1
    row = view["unanswered_question_explanations"][0]
    assert row["epistemic_state"] == "FAIL_CLOSED"
    assert "karşı" in row["why_tr"].casefold() or "bağlam" in row["why_tr"].casefold()
    assert row["creates_new_evidence"] is False
    assert row["can_authorize_emit"] is False


def test_review_required_without_claim_contracts_still_explains_zero_output_without_inventing_reason():
    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload={
            "status": "REVIEW_REQUIRED",
            "analyst_output_contracts": [],
            "source_bound_render_contracts": [],
        },
        safe_finding_payload={"safe_finding_admission_decisions": []},
    )

    assert view["unanswered_question_explanation_count"] == 1
    row = view["unanswered_question_explanations"][0]
    assert row["question_id"] == "report_level_zero_output"
    assert row["epistemic_state"] == "REVIEW_REQUIRED"
    assert row["why_tr"] == "Profesyonel bulgu üretilememesinin daha özel nedeni mevcut kanıttan güvenle çözülemiyor."
    assert row["creates_new_evidence"] is False
    assert row["can_authorize_emit"] is False


def test_source_analyst_action_code_is_preserved_but_humanized_for_analyst():
    claim_payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [{
            "analyst_output_contract_id": "aoc_action_human",
            "source_safe_finding_handoff_ref": "sfh_action_human",
            "professional_emit_allowed": False,
            "safe_finding_admission_decision": "DOWNGRADE",
            "evidence_sufficiency_state": "PARTIAL",
            "blocking_dimensions": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
            "safe_output_meaning": "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
            "render_analyst_action": "REVIEW_BRANCH_EXAMPLES_AND_USE_ONLY_AS_MATCH_LOCAL_VARIATION_CUE",
        }],
        "source_bound_render_contracts": [],
    }
    safe_payload = {
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_action_human",
            "decision": "DOWNGRADE",
            "decision_reasons": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
            "claim_output_allowed": False,
        }]
    }

    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload=safe_payload,
    )

    row = view["unanswered_question_explanations"][0]
    assert row["source_analyst_action_ref"] == "REVIEW_BRANCH_EXAMPLES_AND_USE_ONLY_AS_MATCH_LOCAL_VARIATION_CUE"
    assert row["analyst_action_tr"] == (
        "Şube örneklerini incele; bunları yalnız bu maça ait görünür varyasyon ipucu olarak kullan."
    )
    assert "_" not in row["analyst_action_tr"]


def test_analyst_facing_explanations_group_identical_limits_without_losing_raw_records():
    claim_payload = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [
            {
                "analyst_output_contract_id": f"aoc_group_{idx}",
                "source_safe_finding_handoff_ref": f"sfh_group_{idx}",
                "professional_emit_allowed": False,
                "safe_finding_admission_decision": "DOWNGRADE",
                "evidence_sufficiency_state": "PARTIAL",
                "blocking_dimensions": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
                "safe_output_meaning": "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
                "render_analyst_action": "REVIEW_BRANCH_EXAMPLES_AND_USE_ONLY_AS_MATCH_LOCAL_VARIATION_CUE",
                "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            }
            for idx in range(2)
        ],
        "source_bound_render_contracts": [],
    }
    safe_payload = {
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": f"sfh_group_{idx}",
                "decision": "DOWNGRADE",
                "decision_reasons": ["DEPENDENCY_INDEPENDENCE_NOT_PROVEN"],
                "claim_output_allowed": False,
            }
            for idx in range(2)
        ]
    }

    view = build_presentation_view_model(
        {"status": "REVIEW_REQUIRED"},
        analyst_report_tr="",
        analyst_report_en="",
        mechanism_graph_payload={"cards": []},
        analyst_output_claim_payload=claim_payload,
        safe_finding_payload=safe_payload,
    )

    assert view["unanswered_question_explanation_count"] == 2
    assert view["analyst_unanswered_question_explanation_count"] == 1
    grouped = view["analyst_unanswered_question_explanations"][0]
    assert grouped["affected_question_count"] == 2
    assert grouped["affected_question_ids"] == ["aoc_group_0", "aoc_group_1"]
    assert grouped["creates_new_evidence"] is False
    assert grouped["can_authorize_emit"] is False

    rendered = render_professional_html(view, language="tr")
    assert "2 adayı etkiliyor" in rendered
    assert rendered.count(
        "Görülen örneklerin birbirinden bağımsız olduğu kanıtlanmadığı için tekrar gücü yükseltilemiyor."
    ) == 1
