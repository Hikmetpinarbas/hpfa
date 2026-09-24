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
