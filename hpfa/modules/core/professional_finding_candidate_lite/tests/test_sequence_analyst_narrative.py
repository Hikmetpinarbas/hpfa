from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_analyst_narrative import (
    compose_sequence_analyst_narrative,
)


def _row(state="RECURRENT_VISIBLE_TRACE", support=5, success=2, failure=1, divergence=1, no_followup=1):
    return {
        "analyst_report_block_id": "sfb_a",
        "entity_scope": "team_a",
        "context_scope": [{"period_candidate": "1"}],
        "recurrence_summary": {"observed_support": support, "independent_support_count": "UNKNOWN", "admission_state": state},
        "success_support": success,
        "failure_support": failure,
        "divergence_support": divergence,
        "no_visible_followup_support": no_followup,
        "counterevidence": {"refs": ["v2"] if failure or divergence else []},
        "SAFE_MEANING": "A recurrent visible process candidate exists in the observed scope.",
        "FORBIDDEN_INFERENCE": ["coach intention", "causality"],
        "uncertainty": {"independence": "UNKNOWN"},
        "withdrawal_condition": "Downgrade if evidence changes.",
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _payload(rows):
    return {
        "module_id": "sequence_safe_finding_binding_lite_v1",
        "status": "PASS",
        "analyst_report_blocks": rows,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_narrative_explains_repeat_success_failure_divergence_in_plain_turkish():
    result = compose_sequence_analyst_narrative(_payload([_row()]))
    story = result["narrative_blocks"][0]["story_tr"]
    assert "birden fazla kez tekrarlandı" in story
    assert "2 benzer ilerleme" in story
    assert "1 başarısız sonlanma" in story
    assert "1 farklılaşan devam" in story
    assert "başarısızlık sayılmadı" in story


def test_counterexample_prevents_unconditional_superiority_language():
    story = compose_sequence_analyst_narrative(_payload([_row()]))["narrative_blocks"][0]["counterweight_tr"]
    assert "koşulsuz çalışan bir üstünlük" in story
    assert "okunmamalı" in story


def test_no_counterexample_does_not_become_confirmation():
    row = _row(success=5, failure=0, divergence=0, no_followup=0)
    text = compose_sequence_analyst_narrative(_payload([row]))["narrative_blocks"][0]["counterweight_tr"]
    assert "kanıtlamaz" in text


def test_story_priority_uses_evidence_strength_not_fake_chronology():
    weak = _row("DISCOVERY_ONLY", support=10)
    weak["analyst_report_block_id"] = "weak"
    robust = _row("ROBUST_RECURRENT_VISIBLE_TRACE", support=3)
    robust["analyst_report_block_id"] = "robust"
    result = compose_sequence_analyst_narrative(_payload([weak, robust]))
    assert result["narrative_blocks"][0]["source_report_block_id"] == "robust"
    assert result["story_order_basis"].endswith("NOT_FOOTBALL_CHRONOLOGY")
    assert result["chronological_story_claimed"] is False


def test_review_upstream_survives_as_review_not_fake_pass():
    payload = _payload([_row()])
    payload["status"] = "REVIEW_REQUIRED"
    result = compose_sequence_analyst_narrative(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "binding_upstream_review_required" in result["review_hits"]


def test_claim_lock_breach_fails_closed():
    row = _row()
    row["claim_output_allowed"] = True
    result = compose_sequence_analyst_narrative(_payload([row]))
    assert result["status"] == "FAIL_CLOSED"
    assert result["narrative_block_count"] == 0


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/sequence_analyst_narrative.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
