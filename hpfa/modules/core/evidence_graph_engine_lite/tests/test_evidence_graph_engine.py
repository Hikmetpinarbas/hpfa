import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "evidence_graph_engine_lite" / "src"
sys.path.insert(0, str(SRC))

from evidence_graph_engine import build_evidence_graph, build_graph_report, write_outputs


def base_route():
    return {
        "route_id": "defeasible_route_arg_fusion_cep_progression_001",
        "argument_id": "arg_fusion_cep_progression_001",
        "fusion_id": "fusion_cep_progression_001",
        "argument_family": "progression_without_terminal_value",
        "relation_scope": "context_bound_relation",
        "analysis_route": "bidirectional",
        "whole_to_unit": True,
        "unit_to_whole": True,
        "bidirectional": True,
        "supporting_refs": ["right_channel_access"],
        "qualifying_refs": [],
        "counter_evidence_refs": [],
        "complementary_refs": ["final_third_entry"],
        "context_refs": ["window_001"],
        "counter_scenarios": ["shot_timing_or_angle_limited_terminal_action"],
        "declared_withdrawal_conditions": ["terminal_action_value_becomes_high_in_same_window"],
        "matched_withdrawal_conditions": [],
        "defeasible_state": "SUPPORTED",
        "status": "SMOKE_PASS",
        "decision": "ROUTE_ARGUMENT_AS_SUPPORTED_CANDIDATE",
        "claim_ceiling": "defeasible_argument_candidate_only",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def weakened_route():
    route = base_route()
    route["route_id"] = "defeasible_route_arg_weakened"
    route["argument_id"] = "arg_weakened"
    route["qualifying_refs"] = ["low_shot_volume"]
    route["counter_evidence_refs"] = ["same_construct_opposite_direction"]
    route["defeasible_state"] = "WEAKENED"
    route["decision"] = "ROUTE_ARGUMENT_AS_WEAKENED_CANDIDATE"
    return route


def withdrawn_route():
    route = base_route()
    route["route_id"] = "defeasible_route_arg_withdrawn"
    route["argument_id"] = "arg_withdrawn"
    route["counter_evidence_refs"] = ["later_window_counter_ref"]
    route["matched_withdrawal_conditions"] = ["terminal_action_value_becomes_high_in_same_window"]
    route["defeasible_state"] = "WITHDRAWN"
    route["decision"] = "ROUTE_ARGUMENT_AS_WITHDRAWN_CANDIDATE"
    return route


def test_graph_requires_route_id():
    route = base_route()
    route.pop("route_id")
    graph = build_evidence_graph(route)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "route_id" in graph["missing_fields"]
    assert "defeasible_route_required_fields_missing" in graph["hard_block_hits"]
    assert graph["route_id"] == "MISSING_ROUTE_ID"


def test_graph_requires_argument_id_support_and_claim_ceiling():
    route = base_route()
    route.pop("argument_id")
    route.pop("supporting_refs")
    route["claim_ceiling"] = "argument_candidate_only"
    graph = build_evidence_graph(route)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "argument_id" in graph["missing_fields"]
    assert "supporting_refs" in graph["missing_fields"]
    assert "claim_ceiling" in graph["missing_fields"]


def test_graph_preserves_route_argument_and_fusion_nodes():
    graph = build_evidence_graph(base_route())
    node_types = {node["node_type"] for node in graph["nodes"]}
    assert "defeasible_route" in node_types
    assert "argument" in node_types
    assert "fusion" in node_types
    assert graph["trace_start"] == "defeasible_route_arg_fusion_cep_progression_001"
    assert graph["trace_end"] == "arg_fusion_cep_progression_001"


def test_graph_preserves_support_context_and_complement_nodes():
    graph = build_evidence_graph(base_route())
    node_payload_refs = {node["payload"].get("ref") for node in graph["nodes"]}
    assert "right_channel_access" in node_payload_refs
    assert "window_001" in node_payload_refs
    assert "final_third_entry" in node_payload_refs
    edge_types = {edge["relation_type"] for edge in graph["edges"]}
    assert "SUPPORTS_ARGUMENT" in edge_types
    assert "CONTEXTUALIZES_ARGUMENT" in edge_types
    assert "COMPLEMENTS_ARGUMENT" in edge_types


def test_graph_preserves_scope_and_analysis_route_nodes():
    graph = build_evidence_graph(base_route())
    payloads = [node["payload"] for node in graph["nodes"]]
    assert {"relation_scope": "context_bound_relation"} in payloads
    assert any(payload.get("analysis_route") == "bidirectional" and payload.get("bidirectional") is True for payload in payloads)


def test_weakened_route_preserves_counterevidence_and_requires_review():
    graph = build_evidence_graph(weakened_route())
    node_payload_refs = {node["payload"].get("ref") for node in graph["nodes"]}
    assert "low_shot_volume" in node_payload_refs
    assert "same_construct_opposite_direction" in node_payload_refs
    assert graph["defeasible_state"] == "WEAKENED"
    assert graph["status"] == "REVIEW_REQUIRED"
    assert graph["decision"] == "ROUTE_EVIDENCE_GRAPH_TO_REVIEW"
    assert graph["review_required"] is True
    assert "defeasible_argument_weakened" in graph["review_reasons"]


def test_withdrawn_route_preserves_matched_withdrawal_and_requires_review():
    graph = build_evidence_graph(withdrawn_route())
    edge_types = {edge["relation_type"] for edge in graph["edges"]}
    assert "WITHDRAWAL_CONDITION_MATCHED" in edge_types
    assert graph["defeasible_state"] == "WITHDRAWN"
    assert graph["status"] == "REVIEW_REQUIRED"
    assert "defeasible_argument_withdrawn" in graph["review_reasons"]


def test_failed_upstream_route_blocks_graph():
    route = base_route()
    route["defeasible_state"] = "BLOCKED"
    route["status"] = "FAIL_CLOSED"
    route["decision"] = "BLOCK_ARGUMENT_ROUTE"
    route["hard_block_hits"] = ["upstream_argument_failed_closed"]
    graph = build_evidence_graph(route)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "upstream_defeasible_route_failed_closed" in graph["hard_block_hits"]


def test_nested_forbidden_upstream_route_blocks_graph_with_path():
    route = base_route()
    route["route_metadata"] = {"payload": {"claim_text": "unsafe nested claim"}}
    graph = build_evidence_graph(route)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "upstream_defeasible_route_forbidden_output_attempted" in graph["hard_block_hits"]
    assert "route_metadata.payload.claim_text" in graph["forbidden_output_hits"]


def test_graph_does_not_emit_claim_or_sentence():
    graph = build_evidence_graph(base_route())
    assert "claim_text" not in graph
    assert "safe_sentence" not in graph
    assert graph["claim_output_allowed"] is False
    assert graph["report_language_allowed"] is False
    assert graph["safe_sentence_allowed"] is False


def test_graph_blocks_truth_language_families():
    graph = build_evidence_graph(base_route())
    assert graph["tactical_truth"] is False
    assert graph["dominance_truth"] is False
    assert graph["control_truth"] is False
    assert graph["coach_intention_truth"] is False
    assert graph["off_ball_truth"] is False
    assert graph["pitch_control_truth"] is False
    assert graph["causal_truth"] is False
    assert graph["quality_truth"] is False
    assert graph["sequence_truth"] is False
    assert graph["organism_truth"] is False


def test_graph_report_surfaces_review_required():
    report = build_graph_report([base_route(), weakened_route()])
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["review_graph_count"] == 1
    assert report["blocked_graph_count"] == 0


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_route()], "/sdcard/Download/HPFA/evidence_graph_engine_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_route()], tmp_path)
    assert report["module_id"] == "evidence_graph_engine_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "evidence_graph_engine_lite_v1.json").exists()
    assert (tmp_path / "evidence_graph_engine_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "evidence_graph_engine_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["graph_count"] == 1
    assert loaded["graphs"][0]["defeasible_state"] == "SUPPORTED"


def test_no_sample_match_identity_leak():
    src = (SRC / "evidence_graph_engine.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
