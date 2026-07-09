import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "evidence_graph_engine_lite" / "src"
sys.path.insert(0, str(SRC))

from evidence_graph_engine import build_evidence_graph, build_graph_report, write_outputs


def base_argument():
    return {
        "argument_id": "arg_fusion_cep_progression_001",
        "fusion_id": "fusion_cep_progression_001",
        "argument_family": "progression_without_terminal_value",
        "relation_scope": "context_bound_relation",
        "analysis_route": "bidirectional",
        "whole_to_unit": True,
        "unit_to_whole": True,
        "bidirectional": True,
        "supporting_refs": ["right_channel_access"],
        "qualifying_refs": ["low_shot_volume"],
        "contradicting_refs": [],
        "complementary_refs": ["final_third_entry"],
        "context_refs": ["window_001"],
        "counter_scenarios": ["shot_timing_or_angle_limited_terminal_action"],
        "withdrawal_conditions": ["terminal_action_value_becomes_high_in_same_window"],
        "claim_ceiling": "argument_candidate_only",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
    }


def test_graph_requires_argument_id():
    argument = base_argument()
    argument.pop("argument_id")
    graph = build_evidence_graph(argument)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "argument_id" in graph["missing_fields"]
    assert "argument_required_fields_missing" in graph["hard_block_hits"]
    assert graph["argument_id"] == "MISSING_ARGUMENT_ID"


def test_graph_requires_fusion_id_and_supporting_refs():
    argument = base_argument()
    argument.pop("fusion_id")
    argument.pop("supporting_refs")
    graph = build_evidence_graph(argument)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "fusion_id" in graph["missing_fields"]
    assert "supporting_refs" in graph["missing_fields"]


def test_graph_preserves_argument_and_fusion_nodes():
    graph = build_evidence_graph(base_argument())
    node_types = {node["node_type"] for node in graph["nodes"]}
    assert "argument" in node_types
    assert "fusion" in node_types
    assert graph["trace_start"] == "fusion_cep_progression_001"
    assert graph["trace_end"] == "arg_fusion_cep_progression_001"


def test_graph_preserves_support_qualifier_context_nodes():
    graph = build_evidence_graph(base_argument())
    node_payload_refs = {node["payload"].get("ref") for node in graph["nodes"]}
    assert "right_channel_access" in node_payload_refs
    assert "low_shot_volume" in node_payload_refs
    assert "window_001" in node_payload_refs
    edge_types = {edge["relation_type"] for edge in graph["edges"]}
    assert "SUPPORTS_ARGUMENT" in edge_types
    assert "QUALIFIES_ARGUMENT" in edge_types
    assert "CONTEXTUALIZES_ARGUMENT" in edge_types


def test_graph_preserves_scope_and_route_nodes():
    graph = build_evidence_graph(base_argument())
    payloads = [node["payload"] for node in graph["nodes"]]
    assert {"relation_scope": "context_bound_relation"} in payloads
    assert any(payload.get("analysis_route") == "bidirectional" and payload.get("bidirectional") is True for payload in payloads)


def test_graph_keeps_counter_scenarios_and_withdrawal_conditions():
    graph = build_evidence_graph(base_argument())
    edge_types = {edge["relation_type"] for edge in graph["edges"]}
    assert "CHALLENGES_ARGUMENT" in edge_types
    assert "WITHDRAWS_ARGUMENT_IF_TRUE" in edge_types


def test_failed_upstream_argument_blocks_graph():
    argument = base_argument()
    argument["decision"] = "BLOCK_ARGUMENT"
    argument["hard_block_hits"] = ["upstream_fusion_failed_closed"]
    graph = build_evidence_graph(argument)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "upstream_argument_failed_closed" in graph["hard_block_hits"]


def test_forbidden_upstream_argument_output_blocks_graph():
    argument = base_argument()
    argument["safe_sentence"] = "unsafe sentence"
    graph = build_evidence_graph(argument)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "upstream_argument_forbidden_output_attempted" in graph["hard_block_hits"]
    assert "safe_sentence" in graph["forbidden_output_hits"]


def test_coach_intention_truth_upstream_argument_blocks_graph():
    argument = base_argument()
    argument["coach_intention_truth"] = True
    graph = build_evidence_graph(argument)
    assert graph["decision"] == "BLOCK_GRAPH"
    assert "upstream_argument_forbidden_output_attempted" in graph["hard_block_hits"]
    assert "coach_intention_truth" in graph["forbidden_output_hits"]


def test_graph_does_not_emit_claim_or_sentence():
    graph = build_evidence_graph(base_argument())
    assert "claim_text" not in graph
    assert "safe_sentence" not in graph
    assert graph["claim_output_allowed"] is False
    assert graph["report_language_allowed"] is False
    assert graph["safe_sentence_allowed"] is False


def test_graph_blocks_truth_language_families():
    graph = build_evidence_graph(base_argument())
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


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_argument()], "/sdcard/Download/HPFA/evidence_graph_engine_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_argument()], tmp_path)
    assert report["module_id"] == "evidence_graph_engine_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "evidence_graph_engine_lite_v1.json").exists()
    assert (tmp_path / "evidence_graph_engine_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "evidence_graph_engine_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["graph_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "evidence_graph_engine.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
