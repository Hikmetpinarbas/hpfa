import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULES = ROOT / "hpfa" / "modules" / "core"

SRC_DIRS = [
    MODULES / "composite_evidence_packet_builder_lite" / "src",
    MODULES / "multi_signal_evidence_fusion_lite" / "src",
    MODULES / "composite_argument_builder_lite" / "src",
    MODULES / "defeasible_argument_router_lite" / "src",
    MODULES / "evidence_graph_engine_lite" / "src",
    MODULES / "evidence_lens_matrix_lite" / "src",
    MODULES / "safe_argument_router_tr_lite" / "src",
    MODULES / "analyst_report_block_composer_lite" / "src",
    MODULES / "report_output_contract_lite" / "src",
    MODULES / "final_report_assembly_gate_lite" / "src",
]
for src in reversed(SRC_DIRS):
    sys.path.insert(0, str(src))

from composite_evidence_packet_builder import build_composite_packet
from multi_signal_evidence_fusion import fuse_packet
from composite_argument_builder import build_argument_candidate
from defeasible_argument_router import route_argument
from evidence_graph_engine import build_evidence_graph
from evidence_lens_matrix import build_lens_matrix
from safe_argument_router_tr import route_safe_sentence
from analyst_report_block_composer import compose_report_block
from report_output_contract import evaluate_report_block
from final_report_assembly_gate import evaluate_assembly_item


def supported_candidate():
    return {
        "packet_family": "progression",
        "input_features": [
            {"feature_id": "feature_generic_001", "source_surface": "feature_surface"},
        ],
        "input_windows": [
            {"window_id": "window_generic_001", "source_surface": "window_surface"},
        ],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": [
            {"signal_id": "support_generic_001", "source_surface": "support_surface"},
        ],
        "contradicting_signals": [],
        "claim_ceiling": "composite_candidate_only",
    }


def explicit_contradiction_candidate():
    candidate = supported_candidate()
    candidate["contradicting_signals"] = [
        {
            "signal_id": "counter_generic_001",
            "source_surface": "counter_surface",
            "relation_type": "CONTRADICTS",
            "contradiction_basis": "same_construct_same_window_opposite_direction_candidate",
        }
    ]
    return candidate


def blocked_candidate():
    return {
        "packet_family": "progression",
        "input_features": [{"feature_id": "feature_generic_001"}],
        "claim_ceiling": "composite_candidate_only",
    }


def run_chain(candidate):
    packet = build_composite_packet(candidate)
    fusion = fuse_packet(packet)
    argument = build_argument_candidate(fusion)
    route = route_argument(argument)
    graph = build_evidence_graph(route)
    lens = build_lens_matrix(graph)
    safe_sentence = route_safe_sentence(graph)
    report_block = compose_report_block(safe_sentence)
    output_contract = evaluate_report_block(report_block)
    assembly = evaluate_assembly_item(output_contract)
    return {
        "packet": packet,
        "fusion": fusion,
        "argument": argument,
        "route": route,
        "graph": graph,
        "lens": lens,
        "safe_sentence": safe_sentence,
        "report_block": report_block,
        "output_contract": output_contract,
        "assembly": assembly,
    }


def test_intelligence_chain_standard_fields_connect():
    chain = run_chain(supported_candidate())

    assert chain["packet"]["status"] == "SMOKE_PASS"
    assert chain["fusion"]["fusion_status"] == "SUPPORTED"
    assert chain["argument"]["status"] == "ARGUMENT_SUPPORTED"
    assert chain["route"]["defeasible_state"] == "SUPPORTED"
    assert chain["graph"]["status"] == "SMOKE_PASS"
    assert chain["safe_sentence"]["status"] == "SMOKE_PASS"
    assert chain["report_block"]["status"] == "SMOKE_PASS"
    assert chain["output_contract"]["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE"
    assert chain["assembly"]["assembly_decision"] == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"

    assert chain["fusion"]["packet_id"] == chain["packet"]["packet_id"]
    assert chain["argument"]["fusion_id"] == chain["fusion"]["fusion_id"]
    assert chain["route"]["argument_id"] == chain["argument"]["argument_id"]
    assert chain["graph"]["route_id"] == chain["route"]["route_id"]
    assert chain["lens"]["graph_id"] == chain["graph"]["graph_id"]
    assert chain["safe_sentence"]["graph_id"] == chain["graph"]["graph_id"]
    assert chain["report_block"]["safe_sentence_id"] == chain["safe_sentence"]["safe_sentence_id"]
    assert chain["output_contract"]["report_block_id"] == chain["report_block"]["report_block_id"]
    assert chain["assembly"]["contract_item_id"] == chain["output_contract"]["contract_item_id"]


def test_intelligence_chain_explicit_counterevidence_remains_review_bounded():
    chain = run_chain(explicit_contradiction_candidate())

    assert chain["fusion"]["fusion_status"] == "MIXED_WITH_EXPLICIT_CONTRADICTION"
    assert chain["fusion"]["contradiction_signal_count"] == 1
    assert chain["argument"]["contradicting_refs"] == ["counter_generic_001"]
    assert chain["route"]["defeasible_state"] == "WEAKENED"
    assert chain["graph"]["status"] == "REVIEW_REQUIRED"
    assert chain["graph"]["review_required"] is True
    assert "defeasible_argument_weakened" in chain["graph"]["review_reasons"]
    assert chain["safe_sentence"]["status"] == "REVIEW_REQUIRED"
    assert chain["safe_sentence"]["review_required"] is True
    assert chain["report_block"]["status"] == "REVIEW_REQUIRED"
    assert chain["report_block"]["block_family"] == "review_required_candidate"
    assert chain["output_contract"]["status"] == "REVIEW_REQUIRED"
    assert chain["output_contract"]["inclusion_decision"] == "REVIEW_BLOCK"
    assert chain["output_contract"]["output_text_candidate_tr"] == ""
    assert chain["assembly"]["status"] == "REVIEW_REQUIRED"
    assert chain["assembly"]["assembly_decision"] == "ROUTE_ASSEMBLY_ITEM_TO_REVIEW"
    assert chain["assembly"]["draft_report_candidate_allowed"] is False


def test_intelligence_chain_upstream_failure_propagates():
    chain = run_chain(blocked_candidate())

    assert chain["packet"]["status"] == "FAIL_CLOSED"
    assert chain["fusion"]["decision"] == "BLOCK_FUSION"
    assert chain["argument"]["decision"] == "BLOCK_ARGUMENT"
    assert chain["route"]["decision"] == "BLOCK_ARGUMENT_ROUTE"
    assert chain["graph"]["decision"] == "BLOCK_GRAPH"
    assert chain["safe_sentence"]["decision"] == "BLOCK_SAFE_SENTENCE"
    assert chain["report_block"]["decision"] == "BLOCK_REPORT_BLOCK"
    assert chain["output_contract"]["inclusion_decision"] == "REJECT_BLOCK"
    assert chain["assembly"]["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"


def test_intelligence_chain_nested_forbidden_field_fails_closed():
    candidate = supported_candidate()
    candidate["input_features"][0]["metadata"] = {"claim_text": "unsafe"}
    chain = run_chain(candidate)

    assert chain["packet"]["status"] == "FAIL_CLOSED"
    assert "input_features[0].metadata.claim_text" in chain["packet"]["forbidden_output_hits"]
    assert chain["fusion"]["decision"] == "BLOCK_FUSION"
    assert chain["argument"]["decision"] == "BLOCK_ARGUMENT"
    assert chain["route"]["decision"] == "BLOCK_ARGUMENT_ROUTE"
    assert chain["graph"]["decision"] == "BLOCK_GRAPH"
    assert chain["safe_sentence"]["decision"] == "BLOCK_SAFE_SENTENCE"
    assert chain["report_block"]["decision"] == "BLOCK_REPORT_BLOCK"
    assert chain["output_contract"]["inclusion_decision"] == "REJECT_BLOCK"
    assert chain["assembly"]["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM"


def test_intelligence_chain_canonical_event_count_stays_unknown():
    chain = run_chain(explicit_contradiction_candidate())
    for stage_name, stage in chain.items():
        assert stage["canonical_event_count"] == "UNKNOWN", stage_name


def test_intelligence_chain_lens_review_is_explicit_sidecar_evidence():
    chain = run_chain(supported_candidate())
    lens = chain["lens"]
    assert lens["status"] == "REVIEW_REQUIRED"
    assert lens["decision"] == "ROUTE_INCOMPLETE_LENS_COVERAGE_TO_REVIEW"
    assert lens["absence_inference_allowed"] is False
    assert lens["missing_lenses"]
    assert lens["graph_id"] == chain["graph"]["graph_id"]


def test_intelligence_chain_no_sample_match_identity_leak():
    source_files = [
        MODULES / "composite_evidence_packet_builder_lite" / "src" / "composite_evidence_packet_builder.py",
        MODULES / "multi_signal_evidence_fusion_lite" / "src" / "multi_signal_evidence_fusion.py",
        MODULES / "composite_argument_builder_lite" / "src" / "composite_argument_builder.py",
        MODULES / "defeasible_argument_router_lite" / "src" / "defeasible_argument_router.py",
        MODULES / "evidence_graph_engine_lite" / "src" / "evidence_graph_engine.py",
        MODULES / "evidence_lens_matrix_lite" / "src" / "evidence_lens_matrix.py",
        MODULES / "safe_argument_router_tr_lite" / "src" / "safe_argument_router_tr.py",
        MODULES / "analyst_report_block_composer_lite" / "src" / "analyst_report_block_composer.py",
        MODULES / "report_output_contract_lite" / "src" / "report_output_contract.py",
        MODULES / "final_report_assembly_gate_lite" / "src" / "final_report_assembly_gate.py",
    ]
    for path in source_files:
        source = path.read_text(encoding="utf-8")
        for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
            assert token not in source, f"{token} leaked in {path}"
