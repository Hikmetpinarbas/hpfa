import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "report_output_contract_lite" / "src"
sys.path.insert(0, str(SRC))

from report_output_contract import build_output_contract, evaluate_report_block, write_outputs


def base_report_block():
    return {
        "report_block_id": "report_block_safe_sentence_graph_arg_fusion_cep_progression_001",
        "safe_sentence_id": "safe_sentence_graph_arg_fusion_cep_progression_001",
        "defeasible_state": "SUPPORTED",
        "review_required": False,
        "review_reasons": [],
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_REPORT_OUTPUT_CONTRACT_CANDIDATE",
        "report_block_candidate_tr": "Analist okuması: Görünür kanıt grafiği context_bound_relation kapsamındaki bidirectional okumasında right_channel_access referanslarının argüman adayını desteklediğini; low_shot_volume referanslarının okumayı nitelendirdiğini gösterir.",
        "block_language": "tr",
        "block_family": "analyst_reading_candidate",
        "claim_ceiling": "analyst_report_block_candidate_only",
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_contract_requires_report_block_id():
    block = base_report_block()
    block.pop("report_block_id")
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "report_block_id" in item["missing_fields"]
    assert "report_block_required_fields_missing" in item["hard_block_hits"]
    assert item["report_block_id"] == "MISSING_REPORT_BLOCK_ID"


def test_contract_requires_report_block_candidate_text():
    block = base_report_block()
    block["report_block_candidate_tr"] = ""
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "report_block_candidate_tr" in item["missing_fields"]


def test_contract_requires_upstream_claim_ceiling():
    block = base_report_block()
    block["claim_ceiling"] = "final_report_allowed"
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "claim_ceiling" in item["missing_fields"]


def test_contract_includes_valid_block_candidate():
    item = evaluate_report_block(base_report_block())
    assert item["status"] == "SMOKE_PASS"
    assert item["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE"
    assert item["output_text_candidate_tr"].startswith("Analist okuması:")
    assert item["claim_ceiling"] == "report_output_contract_candidate_only"


def test_review_required_block_family_routes_to_review():
    block = base_report_block()
    block["block_family"] = "review_required_candidate"
    block["status"] = "REVIEW_REQUIRED"
    block["review_required"] = True
    block["review_reasons"] = ["defeasible_argument_weakened"]
    item = evaluate_report_block(block)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["inclusion_decision"] == "REVIEW_BLOCK"
    assert "block_family_requires_review" in item["review_hits"]
    assert "upstream_report_block_requires_review" in item["review_hits"]
    assert item["upstream_review_required"] is True
    assert item["upstream_review_reasons"] == ["defeasible_argument_weakened"]
    assert item["output_text_candidate_tr"] == ""


def test_review_status_routes_to_review_even_if_family_is_not_review_family():
    block = base_report_block()
    block["status"] = "REVIEW_REQUIRED"
    block["review_required"] = True
    block["review_reasons"] = ["upstream_safe_sentence_review_required"]
    item = evaluate_report_block(block)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["inclusion_decision"] == "REVIEW_BLOCK"
    assert "upstream_report_block_requires_review" in item["review_hits"]


def test_review_without_reason_gets_explicit_fallback_reason():
    block = base_report_block()
    block["status"] = "REVIEW_REQUIRED"
    block["review_required"] = True
    block["review_reasons"] = []
    item = evaluate_report_block(block)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["upstream_review_reasons"] == ["upstream_report_block_review_required"]


def test_failed_upstream_block_is_rejected():
    block = base_report_block()
    block["decision"] = "BLOCK_REPORT_BLOCK"
    block["hard_block_hits"] = ["upstream_safe_sentence_failed_closed"]
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "upstream_report_block_failed_closed" in item["hard_block_hits"]


def test_forbidden_upstream_claim_text_rejected():
    block = base_report_block()
    block["claim_text"] = "unsafe claim"
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "upstream_report_block_forbidden_output_attempted" in item["hard_block_hits"]
    assert "claim_text" in item["forbidden_upstream_hits"]


def test_nested_forbidden_upstream_truth_rejected():
    block = base_report_block()
    block["metadata"] = {"nested": {"quality_truth": "unsafe"}}
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "metadata.nested.quality_truth" in item["forbidden_upstream_hits"]


def test_final_or_production_output_flags_rejected():
    block = base_report_block()
    block["final_report_allowed"] = True
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "upstream_report_block_final_output_allowed" in item["hard_block_hits"]

    block = base_report_block()
    block["production_report_allowed"] = True
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "upstream_report_block_production_output_allowed" in item["hard_block_hits"]


def test_canonical_event_count_claim_rejected():
    block = base_report_block()
    block["canonical_event_count"] = 123
    item = evaluate_report_block(block)
    assert item["inclusion_decision"] == "REJECT_BLOCK"
    assert "canonical_event_count_claim_rejected" in item["hard_block_hits"]


def test_contract_does_not_emit_final_report_or_claim_text():
    item = evaluate_report_block(base_report_block())
    assert "claim_text" not in item
    assert "final_report_text" not in item
    assert item["claim_output_allowed"] is False
    assert item["final_report_allowed"] is False
    assert item["production_report_allowed"] is False


def test_contract_blocks_truth_language_families():
    item = evaluate_report_block(base_report_block())
    assert item["tactical_truth"] is False
    assert item["dominance_truth"] is False
    assert item["control_truth"] is False
    assert item["coach_intention_truth"] is False
    assert item["off_ball_truth"] is False
    assert item["pitch_control_truth"] is False
    assert item["causal_truth"] is False
    assert item["quality_truth"] is False
    assert item["sequence_truth"] is False
    assert item["organism_truth"] is False


def test_build_contract_counts_include_review_reject():
    valid = base_report_block()
    review = base_report_block()
    review["report_block_id"] = "report_block_review"
    review["block_family"] = "review_required_candidate"
    review["status"] = "REVIEW_REQUIRED"
    review["review_required"] = True
    review["review_reasons"] = ["defeasible_argument_weakened"]
    reject = base_report_block()
    reject["report_block_id"] = "report_block_reject"
    reject["claim_text"] = "unsafe claim"
    report = build_output_contract([valid, review, reject])
    assert report["status"] == "FAIL_CLOSED"
    assert report["include_count"] == 1
    assert report["review_count"] == 1
    assert report["rejected_count"] == 1


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_report_block()], "/sdcard/Download/HPFA/report_output_contract_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_report_block()], tmp_path)
    assert report["module_id"] == "report_output_contract_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "report_output_contract_lite_v1.json").exists()
    assert (tmp_path / "report_output_contract_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "report_output_contract_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["include_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "report_output_contract.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
