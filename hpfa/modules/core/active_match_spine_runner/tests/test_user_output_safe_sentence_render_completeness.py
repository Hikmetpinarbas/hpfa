import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import ANALYST_OUTPUT_CLAIM_JSON, build_analyst_report


def _source_contract(decision: str = "DOWNGRADE"):
    return {
        "analyst_output_contract_id": "aoc_test",
        "source_safe_finding_handoff_ref": "sfh_test",
        "claim_scope": (
            "NO_CLAIM_OUTPUT"
            if decision == "ABSTAIN"
            else "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY"
        ),
        "safe_finding_admission_decision": decision,
        "professional_emit_allowed": False,
        "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
        "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
        "counter_scenario_candidates": ["SHARED_ANCHOR_DEPENDENCY"],
        "withdrawal_condition_candidates": ["WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED"],
        "render_evidence_refs": ["seq_success_1"],
        "render_counterevidence_refs": ["seq_failure_1"],
        "analyst_or_llm_text_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _source_bound_row(*, state="COMPLETE_BOUNDED_RENDER", sentence=None, decision="DOWNGRADE"):
    if sentence is None:
        sentence = (
            "Bu maçta aynı görünür başlangıçtan çıkan 5 uygun vakanın 3 tanesinde SUCCESS, "
            "2 tanesinde FAILURE sonucu görünür olarak etiketlendi. "
            "Güvenli anlam: MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY."
        )
    render_allowed = state in {"COMPLETE_BOUNDED_RENDER", "FACT_ONLY_RENDER"}
    return {
        "source_analyst_output_contract_ref": "aoc_test",
        "source_safe_finding_handoff_ref": "sfh_test",
        "source_safe_finding_admission_decision": decision,
        "rendered_sentence_contract": {
            "source_analyst_output_contract_ref": "aoc_test",
            "sentence_type": "FACT_ONLY" if state == "FACT_ONLY_RENDER" else "INTERPRETIVE",
            "what_visible": "Bu maçta aynı görünür başlangıçtan 5 uygun vaka gözlendi.",
            "safe_meaning": None if state == "FACT_ONLY_RENDER" else "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
            "claim_limiter": None if state == "FACT_ONLY_RENDER" else "MATCH_LOCAL; OBSERVED_VISIBLE_BRANCHES_ONLY",
            "counter_scenarios": ["SHARED_ANCHOR_DEPENDENCY"],
            "withdrawal_conditions": ["WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED"],
            "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
            "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
            "evidence_refs": ["seq_success_1"],
            "counterevidence_refs": ["seq_failure_1"],
            "render_creates_new_evidence": False,
            "render_authorizes_emit": False,
            "analyst_or_llm_text_is_evidence": False,
            "absence_is_counterevidence": False,
        },
        "render_validation": {
            "render_completeness_state": state,
            "render_allowed": render_allowed,
            "fallback_allowed": state == "FACT_ONLY_RENDER",
            "fallback_mode": "FACT_ONLY_RENDER" if state == "FACT_ONLY_RENDER" else None,
            "render_creates_new_evidence": False,
            "render_can_authorize_emit": False,
            "render_can_strengthen_claim_ceiling": False,
            "analyst_or_llm_text_is_evidence": False,
        },
        "final_human_sentence_tr": sentence if render_allowed else None,
        "render_creates_new_evidence": False,
        "render_can_authorize_emit": False,
        "render_can_strengthen_claim_ceiling": False,
        "analyst_or_llm_text_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _complete_generic_sentence():
    return {
        "safe_sentence_candidate_tr": "Generic C4 yorum cümlesi.",
        "rendered_sentence_contract": {
            "source_analyst_output_contract_ref": "aoc_test",
            "sentence_type": "INTERPRETIVE",
            "what_visible": "Generic görünür fark.",
            "safe_meaning": "Generic match-local cue.",
            "claim_limiter": "Causality değildir.",
            "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            "required_qualifiers": ["MATCH_LOCAL", "OBSERVED_VISIBLE_BRANCHES_ONLY"],
            "forbidden_claim_families": ["CAUSALITY", "TACTICAL_PATTERN_TRUTH"],
            "counter_scenarios": ["SHARED_ANCHOR_DEPENDENCY"],
            "withdrawal_conditions": ["WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED"],
            "evidence_refs": ["seq_success_1"],
            "counterevidence_refs": ["seq_failure_1"],
            "render_creates_new_evidence": False,
            "render_authorizes_emit": False,
            "professional_emit_allowed": False,
            "analyst_or_llm_text_is_evidence": False,
            "absence_is_counterevidence": False,
        },
    }


def _full_spine(root: Path, source_rows, generic_safe=None):
    claim_path = root / ANALYST_OUTPUT_CLAIM_JSON
    claim_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "analyst_output_contracts": [_source_contract()],
                "source_bound_render_contracts": source_rows,
                "source_bound_render_contract_count": len(source_rows),
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
        "current_invocation_artifacts": [],
        "variant_feature_challenge_runtime_binding": {
            "post_sequence_admission_finalized": True,
            "post_sequence_current_invocation_artifacts": [str(claim_path)],
        },
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": False,
            "rich_multiformat_lane_executed": False,
            "current_c4_producers_reused": True,
        },
        "intelligence_chains": ([{"safe_sentence": generic_safe}] if generic_safe is not None else []),
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _safe_output_section(report: str) -> str:
    marker = "[5] SAFE_ARGUMENT_CANDIDATES / SAFE FINDING → ANALYST OUTPUT — SOURCE-BOUND RENDER"
    assert marker in report
    return report.split(marker, 1)[1].split("[6]", 1)[0]


def test_source_bound_complete_sentence_reaches_user_report(tmp_path: Path):
    row = _source_bound_row()
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [row], _complete_generic_sentence()))
    assert row["final_human_sentence_tr"] in report
    assert "source_bound_render_contract_count=1" in report
    assert '"COMPLETE_BOUNDED_RENDER": 1' in report
    assert "render_can_authorize_emit=false" in report
    assert "analyst_or_llm_text_is_evidence=false" in report


def test_source_bound_blocked_sentence_does_not_render(tmp_path: Path):
    forbidden = "Bu cümle yayınlanmamalı."
    row = _source_bound_row(state="INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED", sentence=forbidden)
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [row]))
    assert forbidden not in report
    assert "Source-bound Analyst Output contractlari mevcut fakat bu run'da render edilebilir cümle bulunmadi" in report
    assert '"INCOMPLETE_INTERPRETIVE_RENDER_BLOCKED": 1' in report


def test_source_bound_fact_only_fallback_reaches_report_without_interpretation(tmp_path: Path):
    fact = "Bu maçta aynı görünür başlangıçtan 5 uygun vaka gözlendi."
    row = _source_bound_row(state="FACT_ONLY_RENDER", sentence=fact, decision="ABSTAIN")
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [row]))
    assert fact in report
    assert '"FACT_ONLY_RENDER": 1' in report
    assert "Güvenli anlam:" not in _safe_output_section(report)


def test_generic_c4_sentence_does_not_replace_source_bound_safe_finding(tmp_path: Path):
    generic = _complete_generic_sentence()
    row = _source_bound_row()
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [row], generic))
    assert row["final_human_sentence_tr"] in report
    assert generic["safe_sentence_candidate_tr"] not in report
    assert "generic_c4_render_state_counts=" in report


def test_unbound_legacy_interpretive_sentence_remains_blocked(tmp_path: Path):
    unsafe_text = "Takım X konusunda sorun yaşıyor."
    unsafe = {"safe_sentence_candidate_tr": unsafe_text}
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [], unsafe))
    assert unsafe_text not in report
    assert "generic C4 interpretive render da güvenli biçimde bloklandi" in report


def test_other_report_surfaces_and_truth_locks_remain_backward_compatible(tmp_path: Path):
    report = build_analyst_report(tmp_path, _full_spine(tmp_path, [_source_bound_row()]))
    assert "[1] WHAT_VISIBLE" in report
    assert "[5] SAFE_ARGUMENT_CANDIDATES" in report
    assert "[6] ANALYST REVIEW" in report
    assert "canonical_event_count=UNKNOWN" in report
    assert "true_action_count=UNKNOWN" in report
    assert "production_release=false" in report
    assert "render_creates_new_evidence=false" in report
    assert "render_can_strengthen_claim_ceiling=false" in report


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py").read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Fenerbahçe", "Roma", "09.09.2026", "10.09.2026"):
        assert token not in source
