from pathlib import Path

from hpfa.modules.core.professional_finding_candidate_lite.src.match_ecg_signal import build_match_ecg_signal


def _payload(row):
    return {
        "status": "PASS",
        "change_comparisons": [row],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _row(**overrides):
    row = {
        "comparison_id": "cmp_1",
        "entity_scope": {"team_identity_candidate_id": "team_a"},
        "process_ref": "process_1",
        "baseline_window_ref": "w1",
        "comparison_window_ref": "w2",
        "temporal_relation": "AFTER_CONFIRMED",
        "coverage_state": "ADEQUATE_FOR_COMPARISON",
        "direction": "RISE",
        "outcome_mix_changed": True,
        "sequence_mix_changed": False,
        "counterevidence": ["failure_examples_remain_visible"],
        "alternative_explanations": ["sample_composition"],
    }
    row.update(overrides)
    return row


def test_admitted_after_can_emit_descriptive_rise():
    result = build_match_ecg_signal(_payload(_row()))
    assert result["status"] == "PASS"
    signal = result["signals"][0]
    assert signal["signal_state"] == "RISE"
    assert signal["directional_language_admitted"] is True
    assert "sonraki pencerede yükseldi" in signal["safe_meaning_tr"]
    assert "MOMENTUM_TRUTH" in signal["forbidden_inference"]


def test_unordered_relation_cannot_emit_rise_or_fall():
    result = build_match_ecg_signal(_payload(_row(temporal_relation="SAME_TIME_UNORDERED")))
    assert result["status"] == "FAIL_CLOSED"
    assert "directional_change_without_before_after_admission:cmp_1" in result["hard_block_hits"]


def test_distribution_difference_without_direction_becomes_break():
    result = build_match_ecg_signal(_payload(_row(direction="", temporal_relation="ORDER_INDETERMINATE")))
    assert result["status"] == "PASS"
    signal = result["signals"][0]
    assert signal["signal_state"] == "BREAK"
    assert signal["directional_language_admitted"] is False


def test_partial_coverage_downgrades_direction_to_uncertain():
    result = build_match_ecg_signal(_payload(_row(coverage_state="PARTIAL")))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["signals"][0]["signal_state"] == "UNCERTAIN"
    assert "direction_downgraded_for_coverage:cmp_1" in result["review_hits"]


def test_unknown_temporal_relation_fails_closed():
    result = build_match_ecg_signal(_payload(_row(temporal_relation="ROW_ORDER_ONLY")))
    assert result["status"] == "FAIL_CLOSED"
    assert "temporal_relation_not_admitted:cmp_1" in result["hard_block_hits"]


def test_claim_locks_remain_closed():
    result = build_match_ecg_signal(_payload(_row()))
    assert result["momentum_truth_claimed"] is False
    assert result["dominance_truth_claimed"] is False
    assert result["causality_claimed"] is False
    assert result["coach_intention_claimed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/professional_finding_candidate_lite/src/match_ecg_signal.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
