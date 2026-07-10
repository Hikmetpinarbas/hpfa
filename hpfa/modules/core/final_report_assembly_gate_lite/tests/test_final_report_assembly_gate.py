import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "final_report_assembly_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from final_report_assembly_gate import build_assembly_gate, evaluate_assembly_item, write_outputs


def base_contract_item():
    return {
        "contract_item_id": "contract_report_block_safe_sentence_graph_arg_fusion_cep_progression_001",
        "report_block_id": "report_block_safe_sentence_graph_arg_fusion_cep_progression_001",
        "inclusion_decision": "INCLUDE_BLOCK_CANDIDATE",
        "output_text_candidate_tr": "Analist okuması: Görünür kanıt grafiği context_bound_relation kapsamındaki bidirectional okumasında right_channel_access referanslarının argüman adayını desteklediğini; low_shot_volume referanslarının okumayı nitelendirdiğini gösterir.",
        "claim_ceiling": "report_output_contract_candidate_only",
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_assembly_requires_contract_item_id():
    item = base_contract_item()
    item.pop("contract_item_id")
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "contract_item_id" in result["missing_fields"]
    assert "assembly_required_fields_missing" in result["hard_block_hits"]
    assert result["contract_item_id"] == "MISSING_CONTRACT_ITEM_ID"


def test_assembly_requires_report_block_id():
    item = base_contract_item()
    item.pop("report_block_id")
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "report_block_id" in result["missing_fields"]


def test_assembly_requires_upstream_claim_ceiling():
    item = base_contract_item()
    item["claim_ceiling"] = "final_report_allowed"
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "claim_ceiling" in result["missing_fields"]


def test_ready_include_block_becomes_draft_assembly_candidate_only():
    result = evaluate_assembly_item(base_contract_item())
    assert result["status"] == "SMOKE_PASS"
    assert result["assembly_decision"] == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
    assert result["assembly_item_candidate_tr"].startswith("Analist okuması:")
    assert result["claim_ceiling"] == "final_report_assembly_candidate_only"
    assert result["draft_report_candidate_allowed"] is True
    assert result["final_report_allowed"] is False
    assert result["production_report_allowed"] is False


def test_review_block_routes_to_review_without_text():
    item = base_contract_item()
    item["inclusion_decision"] = "REVIEW_BLOCK"
    item["output_text_candidate_tr"] = ""
    result = evaluate_assembly_item(item)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["assembly_decision"] == "ROUTE_ASSEMBLY_ITEM_TO_REVIEW"
    assert "upstream_contract_item_requires_review" in result["review_hits"]
    assert result["assembly_item_candidate_tr"] == ""


def test_reject_block_fails_closed():
    item = base_contract_item()
    item["inclusion_decision"] = "REJECT_BLOCK"
    item["status"] = "FAIL_CLOSED"
    item["hard_block_hits"] = ["upstream_reject"]
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "upstream_contract_item_failed_closed" in result["hard_block_hits"]


def test_unknown_decision_rejected():
    item = base_contract_item()
    item["inclusion_decision"] = "FINAL_REPORT_NOW"
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "unknown_inclusion_decision_rejected" in result["hard_block_hits"]


def test_included_block_requires_output_candidate_text():
    item = base_contract_item()
    item["output_text_candidate_tr"] = ""
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "included_block_missing_output_candidate" in result["hard_block_hits"]


def test_forbidden_upstream_output_attempt_rejected():
    item = base_contract_item()
    item["final_report_text"] = "unsafe final report"
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "upstream_contract_forbidden_output_attempted" in result["hard_block_hits"]
    assert "final_report_text" in result["forbidden_upstream_hits"]


def test_final_or_production_flags_rejected():
    item = base_contract_item()
    item["final_report_allowed"] = True
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "upstream_contract_final_report_allowed" in result["hard_block_hits"]

    item = base_contract_item()
    item["production_report_allowed"] = True
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "upstream_contract_production_output_allowed" in result["hard_block_hits"]


def test_forbidden_language_detected():
    item = base_contract_item()
    item["output_text_candidate_tr"] = "Bu veri kesin oyun kontrolü kanıtlıyor."
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "assembly_candidate_forbidden_language_detected" in result["hard_block_hits"]
    assert result["assembly_item_candidate_tr"] == ""


def test_canonical_event_count_claim_rejected():
    item = base_contract_item()
    item["canonical_event_count"] = 123
    result = evaluate_assembly_item(item)
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "canonical_event_count_claim_rejected" in result["hard_block_hits"]


def test_build_assembly_gate_counts_ready_review_blocked():
    ready = base_contract_item()
    review = base_contract_item()
    review["contract_item_id"] = "contract_review"
    review["inclusion_decision"] = "REVIEW_BLOCK"
    review["output_text_candidate_tr"] = ""
    blocked = base_contract_item()
    blocked["contract_item_id"] = "contract_blocked"
    blocked["claim_text"] = "unsafe claim"
    report = build_assembly_gate([ready, review, blocked])
    assert report["status"] == "FAIL_CLOSED"
    assert report["ready_count"] == 1
    assert report["review_count"] == 1
    assert report["blocked_count"] == 1
    assert report["draft_report_candidate_allowed"] is False


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_contract_item()], "/sdcard/Download/HPFA/final_report_assembly_gate_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_contract_item()], tmp_path)
    assert report["module_id"] == "final_report_assembly_gate_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "final_report_assembly_gate_lite_v1.json").exists()
    assert (tmp_path / "final_report_assembly_gate_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "final_report_assembly_gate_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["ready_count"] == 1
    assert loaded["final_report_allowed"] is False
    assert loaded["production_report_allowed"] is False


def test_no_sample_match_identity_leak():
    src = (SRC / "final_report_assembly_gate.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
