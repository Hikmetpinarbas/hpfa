import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "safe_argument_router_tr_lite" / "src"
sys.path.insert(0, str(SRC))

from safe_argument_router_tr import build_safe_sentence_report, route_safe_sentence, write_outputs


def node(node_id, node_type, payload):
    return {"node_id": node_id, "node_type": node_type, "source": "test", "payload": payload}


def base_graph():
    return {
        "graph_id": "graph_arg_fusion_cep_progression_001",
        "argument_id": "arg_fusion_cep_progression_001",
        "fusion_id": "fusion_cep_progression_001",
        "claim_ceiling": "evidence_graph_candidate_only",
        "defeasible_state": "SUPPORTED",
        "review_required": False,
        "review_reasons": [],
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_EVIDENCE_TRACE_CONSUMER",
        "nodes": [
            node("support_1", "support_ref", {"ref": "right_channel_access"}),
            node("qualifier_1", "qualifier_ref", {"ref": "low_shot_volume"}),
            node("context_1", "context_ref", {"ref": "window_001"}),
            node("counter_1", "counter_scenario", {"ref": "shot_timing_or_angle_limited_terminal_action"}),
            node("withdraw_1", "withdrawal_condition", {"ref": "terminal_action_value_becomes_high_in_same_window"}),
            node("scope_1", "relation_scope", {"relation_scope": "context_bound_relation"}),
            node("route_1", "analysis_route", {"analysis_route": "bidirectional", "bidirectional": True}),
            node("defeasible_1", "defeasible_route", {"defeasible_state": "SUPPORTED"}),
        ],
        "edges": [
            {"source": "support_1", "target": "arg", "relation_type": "SUPPORTS_ARGUMENT"},
            {"source": "qualifier_1", "target": "arg", "relation_type": "QUALIFIES_ARGUMENT"},
        ],
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
    }


def test_router_requires_graph_id():
    graph = base_graph()
    graph.pop("graph_id")
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "graph_id" in item["missing_fields"]
    assert "graph_required_fields_missing" in item["hard_block_hits"]
    assert item["graph_id"] == "MISSING_GRAPH_ID"


def test_router_requires_nodes_edges_and_claim_ceiling():
    graph = base_graph()
    graph.pop("nodes")
    graph.pop("edges")
    graph["claim_ceiling"] = "claim_text_allowed"
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "nodes" in item["missing_fields"]
    assert "edges" in item["missing_fields"]
    assert "claim_ceiling" in item["missing_fields"]


def test_router_creates_safe_turkish_sentence_candidate():
    item = route_safe_sentence(base_graph())
    assert item["status"] == "SMOKE_PASS"
    assert item["decision"] == "READY_FOR_REPORT_COMPOSER_CANDIDATE"
    assert item["sentence_language"] == "tr"
    assert item["defeasible_state"] == "SUPPORTED"
    assert "Görünür kanıt grafiği" in item["safe_sentence_candidate_tr"]
    assert "right_channel_access" in item["safe_sentence_candidate_tr"]
    assert "low_shot_volume" in item["safe_sentence_candidate_tr"]
    assert "geri çekilebileceğini" in item["safe_sentence_candidate_tr"]


def test_router_emits_standard_safe_sentence_candidate_key():
    item = route_safe_sentence(base_graph())
    assert item["safe_sentence_candidate_tr"]
    assert item["sentence_candidate_tr"] == item["safe_sentence_candidate_tr"]


def test_router_blocks_failed_upstream_graph():
    graph = base_graph()
    graph["decision"] = "BLOCK_GRAPH"
    graph["hard_block_hits"] = ["upstream_argument_failed_closed"]
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "upstream_graph_failed_closed" in item["hard_block_hits"]
    assert item["safe_sentence_candidate_tr"] == ""


def test_router_blocks_upstream_truth_output():
    graph = base_graph()
    graph["coach_intention_truth"] = True
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "upstream_graph_forbidden_output_attempted" in item["hard_block_hits"]
    assert "coach_intention_truth" in item["forbidden_upstream_hits"]


def test_router_blocks_nested_payload_forbidden_output():
    graph = base_graph()
    graph["nodes"].append(node("unsafe_payload", "support_ref", {"ref": "unsafe_ref", "claim_text": "unsafe claim"}))
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "upstream_graph_forbidden_output_attempted" in item["hard_block_hits"]
    assert "nodes[8].payload.claim_text" in item["forbidden_upstream_hits"]
    assert item["safe_sentence_candidate_tr"] == ""


def test_router_blocks_deep_nested_forbidden_output():
    graph = base_graph()
    graph["nodes"][0]["payload"]["metadata"] = {"nested": {"quality_truth": "unsafe"}}
    item = route_safe_sentence(graph)
    assert item["decision"] == "BLOCK_SAFE_SENTENCE"
    assert "nodes[0].payload.metadata.nested.quality_truth" in item["forbidden_upstream_hits"]


def test_review_required_graph_remains_review_required():
    graph = base_graph()
    graph["status"] = "REVIEW_REQUIRED"
    graph["decision"] = "ROUTE_EVIDENCE_GRAPH_TO_REVIEW"
    graph["review_required"] = True
    graph["review_reasons"] = ["upstream_ambiguity_preserved"]
    item = route_safe_sentence(graph)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["decision"] == "ROUTE_REVIEW_SAFE_SENTENCE_CANDIDATE"
    assert item["review_required"] is True
    assert item["review_reasons"] == ["upstream_ambiguity_preserved"]
    assert item["safe_sentence_candidate_tr"].startswith("Gözden geçirme gerektiren kanıt grafiği")


def test_review_required_without_reason_gets_explicit_fallback_reason():
    graph = base_graph()
    graph["status"] = "REVIEW_REQUIRED"
    graph["review_required"] = True
    graph["review_reasons"] = []
    item = route_safe_sentence(graph)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["review_reasons"] == ["upstream_graph_review_required"]


def test_weakened_argument_stays_review_bounded_in_sentence():
    graph = base_graph()
    graph["defeasible_state"] = "WEAKENED"
    graph["status"] = "REVIEW_REQUIRED"
    graph["review_required"] = True
    graph["review_reasons"] = ["defeasible_argument_weakened"]
    graph["nodes"][-1]["payload"]["defeasible_state"] = "WEAKENED"
    graph["nodes"].append(node("contradiction_1", "contradiction_ref", {"ref": "counter_episode_004"}))
    item = route_safe_sentence(graph)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["defeasible_state"] == "WEAKENED"
    assert "zayıflamış durumda" in item["safe_sentence_candidate_tr"]
    assert "counter_episode_004" in item["safe_sentence_candidate_tr"]


def test_withdrawn_argument_stays_review_bounded_and_exposes_matched_condition():
    graph = base_graph()
    graph["defeasible_state"] = "WITHDRAWN"
    graph["status"] = "REVIEW_REQUIRED"
    graph["review_required"] = True
    graph["review_reasons"] = ["defeasible_argument_withdrawn"]
    graph["nodes"][-1]["payload"]["defeasible_state"] = "WITHDRAWN"
    graph["nodes"].append(node("contradiction_1", "contradiction_ref", {"ref": "counter_episode_007"}))
    graph["nodes"].append(node("matched_withdrawal_1", "matched_withdrawal_condition", {"ref": "terminal_action_value_becomes_high_in_same_window"}))
    item = route_safe_sentence(graph)
    assert item["status"] == "REVIEW_REQUIRED"
    assert item["defeasible_state"] == "WITHDRAWN"
    assert "geri çekilmiş durumda" in item["safe_sentence_candidate_tr"]
    assert "geri çekme koşulunun eşleştiğini" in item["safe_sentence_candidate_tr"]


def test_report_status_preserves_any_review_required_item():
    supported = base_graph()
    weakened = base_graph()
    weakened["graph_id"] = "graph_weakened"
    weakened["defeasible_state"] = "WEAKENED"
    weakened["status"] = "REVIEW_REQUIRED"
    weakened["review_required"] = True
    weakened["review_reasons"] = ["defeasible_argument_weakened"]
    weakened["nodes"][-1]["payload"]["defeasible_state"] = "WEAKENED"
    report = build_safe_sentence_report([supported, weakened])
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["blocked_safe_sentence_count"] == 0
    assert report["review_safe_sentence_count"] == 1


def test_router_does_not_emit_claim_text_or_report_language():
    item = route_safe_sentence(base_graph())
    assert "claim_text" not in item
    assert "report_text" not in item
    assert item["claim_output_allowed"] is False
    assert item["report_language_allowed"] is False
    assert item["safe_sentence_allowed"] is True
    assert item["claim_ceiling"] == "safe_sentence_candidate_only"


def test_router_blocks_truth_language_families():
    item = route_safe_sentence(base_graph())
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


def test_sentence_avoids_forbidden_claim_fragments():
    item = route_safe_sentence(base_graph())
    assert item["forbidden_sentence_hits"] == []
    lowered = item["safe_sentence_candidate_tr"].lower()
    for fragment in ["domine etti", "hoca planladı", "bilinçli olarak", "kanıtlıyor", "nedeni budur"]:
        assert fragment not in lowered


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_graph()], "/sdcard/Download/HPFA/safe_argument_router_tr_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_build_report_and_write_outputs(tmp_path):
    report = write_outputs([base_graph()], tmp_path)
    assert report["module_id"] == "safe_argument_router_tr_lite_v1"
    assert report["status"] == "SMOKE_PASS"
    assert report["review_safe_sentence_count"] == 0
    assert (tmp_path / "safe_argument_router_tr_lite_v1.json").exists()
    assert (tmp_path / "safe_argument_router_tr_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "safe_argument_router_tr_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["safe_sentence_count"] == 1
    assert loaded["safe_sentences"][0]["safe_sentence_candidate_tr"]


def test_no_sample_match_identity_leak():
    src = (SRC / "safe_argument_router_tr.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
