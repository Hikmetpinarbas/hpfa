import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "final_report_assembly_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from final_report_assembly_gate import evaluate_assembly_item


def base_contract_item():
    return {
        "contract_item_id": "contract_generic_001",
        "report_block_id": "report_block_generic_001",
        "inclusion_decision": "INCLUDE_BLOCK_CANDIDATE",
        "output_text_candidate_tr": "Analist okuması: görünür kanıt adayı sınırlı biçimde desteklenmektedir.",
        "claim_ceiling": "report_output_contract_candidate_only",
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_assembly_blocks_nested_claim_text():
    item = base_contract_item()
    item["metadata"] = {"payload": {"claim_text": "unsafe"}}
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert result["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"
    assert "upstream_contract_forbidden_output_attempted" in result["hard_block_hits"]
    assert "metadata.payload.claim_text" in result["forbidden_upstream_hits"]


def test_assembly_blocks_nested_truth_field_in_list():
    item = base_contract_item()
    item["evidence"] = [{"metadata": {"quality_truth": "unsafe"}}]
    result = evaluate_assembly_item(item)
    assert result["status"] == "FAIL_CLOSED"
    assert "evidence[0].metadata.quality_truth" in result["forbidden_upstream_hits"]


def test_no_sample_match_identity_leak():
    src = (SRC / "final_report_assembly_gate.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
