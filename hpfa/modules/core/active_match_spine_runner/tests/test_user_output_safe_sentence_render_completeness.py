import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import ANALYST_OUTPUT_CLAIM_JSON, build_analyst_report


def _source_contract():
    return {
        "analyst_output_contract_id": "aoc_test",
        "source_safe_finding_handoff_ref": "sfh_test",
        "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
        "safe_finding_admission_decision": "DOWNGRADE",
        "professional_emit_allowed": False,
        "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
        "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
        "variant_feature_challenge_counter_scenario_candidates": ["counter_1"],
        "variant_feature_challenge_withdrawal_condition_candidates": ["withdraw_1"],
        "analyst_or_llm_text_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _full_spine(root: Path, safe: dict):
    claim_path = root / ANALYST_OUTPUT_CLAIM_JSON
    claim_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "analyst_output_contracts": [_source_contract()],
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        ),
        encoding="utf-8",
    )
    return {
        "status": "REVIEW_REQUIRED",
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED",
        "current_invocation_artifacts": [str(claim_path)],
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": False,
            "rich_multiformat_lane_executed": False,
            "current_c4_producers_reused": True,
        },
        "intelligence_chains": [{"safe_sentence": safe}],
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _complete_safe_sentence():
    return {
        "safe_sentence_candidate_tr": "Bu maçta gözlenen örneklerde X farkı görüldü; bu match-local variation candidate'dır.",
        "rendered_sentence_contract": {
            "source_analyst_output_contract_ref": "aoc_test",
            "sentence_type": "INTERPRETIVE",
            "what_visible": "Bu maçta gözlenen örneklerde X farkı görüldü.",
            "safe_meaning": "Bu match-local variation candidate olarak okunabilir.",
            "claim_limiter": "Causality veya tactical-pattern truth değildir.",
            "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
            "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
            "counter_scenarios": ["counter_1"],
            "withdrawal_conditions": ["withdraw_1"],
            "render_creates_new_evidence": False,
            "render_authorizes_emit": False,
            "professional_emit_allowed": False,
            "analyst_or_llm_text_is_evidence": False,
            "absence_is_counterevidence": False,
        },
    }


def test_complete_bounded_safe_sentence_reaches_user_report(tmp_path: Path):
    safe = _complete_safe_sentence()
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, safe))
    assert safe["safe_sentence_candidate_tr"] in report
    assert '"COMPLETE_BOUNDED_RENDER": 1' in report
    assert "render_can_authorize_emit=false" in report
    assert "analyst_or_llm_text_is_evidence=false" in report


def test_unbound_legacy_interpretive_sentence_is_blocked(tmp_path: Path):
    unsafe_text = "Takım X konusunda sorun yaşıyor."
    safe = {"safe_sentence_candidate_tr": unsafe_text}
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, safe))
    assert unsafe_text not in report
    assert "Complete source-bounded render bulunmadi" in report


def test_incomplete_interpretive_sentence_falls_back_only_to_explicit_fact(tmp_path: Path):
    safe = _complete_safe_sentence()
    safe["safe_sentence_candidate_tr"] = "Daha güçlü yorum."
    render = safe["rendered_sentence_contract"]
    render["claim_limiter"] = ""
    visible_fact = render["what_visible"]
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, safe))
    assert "Daha güçlü yorum." not in report
    assert visible_fact in report
    assert '"INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED": 1' in report


def test_other_report_surfaces_remain_backward_compatible(tmp_path: Path):
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, _complete_safe_sentence()))
    assert "[1] WHAT_VISIBLE" in report
    assert "[6] ANALYST REVIEW" in report
    assert "canonical_event_count=UNKNOWN" in report
    assert "true_action_count=UNKNOWN" in report
    assert "production_release=false" in report


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py").read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Fenerbahçe", "Roma", "09.09.2026", "10.09.2026"):
        assert token not in source
