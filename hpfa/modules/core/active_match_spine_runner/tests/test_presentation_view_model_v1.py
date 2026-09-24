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
