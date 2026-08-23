import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "defeasible_argument_router_lite" / "src"
sys.path.insert(0, str(SRC))

from defeasible_argument_router import route_argument


def base_argument():
    return {
        "argument_id": "arg_generic_001",
        "argument_family": "progression_without_terminal_value",
        "supporting_refs": ["support_generic_001"],
        "qualifying_refs": [],
        "contradicting_refs": [],
        "withdrawal_conditions": ["supporting_relation_disappears_in_same_context"],
        "claim_ceiling": "argument_candidate_only",
        "status": "ARGUMENT_SUPPORTED",
        "decision": "READY_FOR_SAFE_ROUTER",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_defeasible_router_blocks_nested_claim_text():
    argument = base_argument()
    argument["metadata"] = {"payload": {"claim_text": "unsafe"}}
    route = route_argument(argument)
    assert route["status"] == "FAIL_CLOSED"
    assert route["defeasible_state"] == "BLOCKED"
    assert "upstream_argument_forbidden_output_attempted" in route["hard_block_hits"]
    assert "metadata.payload.claim_text" in route["forbidden_upstream_hits"]


def test_defeasible_router_blocks_nested_truth_field_in_list():
    argument = base_argument()
    argument["counter_scenarios"] = [{"ref": "generic_counter", "metadata": {"quality_truth": "unsafe"}}]
    route = route_argument(argument)
    assert route["status"] == "FAIL_CLOSED"
    assert "counter_scenarios[0].metadata.quality_truth" in route["forbidden_upstream_hits"]


def test_no_sample_match_identity_leak():
    src = (SRC / "defeasible_argument_router.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
