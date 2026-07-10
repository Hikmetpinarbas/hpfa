import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "evidence_lens_matrix_lite" / "src"
sys.path.insert(0, str(SRC))

from evidence_lens_matrix import REQUIRED_LENSES, build_lens_matrix, build_lens_report, write_outputs


def base_graph():
    nodes = [
        {
            "node_id": f"node_{lens}",
            "node_type": "evidence_ref",
            "source": "evidence_graph_engine_lite_v1",
            "payload": {"lens": lens, "ref": f"ref_{lens}"},
        }
        for lens in REQUIRED_LENSES
    ]
    return {
        "graph_id": "graph_argument_001",
        "nodes": nodes,
        "edges": [],
        "claim_ceiling": "evidence_graph_candidate_only",
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_EVIDENCE_TRACE_CONSUMER",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_matrix_requires_graph_id_nodes_edges_and_claim_ceiling():
    graph = base_graph()
    graph.pop("graph_id")
    graph.pop("nodes")
    graph.pop("edges")
    graph["claim_ceiling"] = "argument_candidate_only"
    matrix = build_lens_matrix(graph)
    assert matrix["decision"] == "BLOCK_LENS_MATRIX"
    assert matrix["missing_fields"] == ["graph_id", "nodes", "edges", "claim_ceiling"]


def test_complete_explicit_lens_set_is_ready():
    matrix = build_lens_matrix(base_graph())
    assert matrix["decision"] == "READY_FOR_LENS_AWARE_REVIEW_CANDIDATE"
    assert matrix["coverage_score"] == 1.0
    assert matrix["missing_lenses"] == []


def test_missing_lens_routes_to_review_not_absence_claim():
    graph = base_graph()
    graph["nodes"] = [node for node in graph["nodes"] if node["payload"]["lens"] != "opponent"]
    matrix = build_lens_matrix(graph)
    assert matrix["decision"] == "ROUTE_INCOMPLETE_LENS_COVERAGE_TO_REVIEW"
    assert matrix["status"] == "REVIEW_REQUIRED"
    assert matrix["missing_lenses"] == ["opponent"]
    assert matrix["absence_inference_allowed"] is False


def test_coverage_score_is_inventory_fraction():
    graph = base_graph()
    graph["nodes"] = graph["nodes"][:4]
    matrix = build_lens_matrix(graph)
    assert matrix["coverage_score"] == 0.4
    assert matrix["coverage_score_meaning"] == "explicit_lens_inventory_completeness_only"


def test_node_level_lenses_are_explicitly_accepted():
    graph = base_graph()
    graph["nodes"][0].pop("payload")
    graph["nodes"][0]["lenses"] = ["time"]
    matrix = build_lens_matrix(graph)
    assert "time" in matrix["covered_lenses"]


def test_context_and_contradiction_node_types_are_explicit_lenses():
    graph = base_graph()
    graph["nodes"] = [
        {"node_id": "context_1", "node_type": "context_ref", "payload": {"ref": "window_1"}},
        {"node_id": "contra_1", "node_type": "contradiction_ref", "payload": {"ref": "signal_2"}},
    ]
    matrix = build_lens_matrix(graph)
    assert matrix["covered_lenses"] == ["context", "contradiction"]


def test_ids_and_free_text_are_not_interpreted_as_lens_proof():
    graph = base_graph()
    graph["nodes"] = [{"node_id": "time_space_actor_team", "node_type": "support_ref", "payload": {"ref": "all lenses"}}]
    matrix = build_lens_matrix(graph)
    assert matrix["covered_lenses"] == []
    assert matrix["missing_lenses"] == list(REQUIRED_LENSES)


def test_unknown_lens_tag_fails_closed():
    graph = base_graph()
    graph["nodes"][0]["payload"]["lens"] = "intent"
    matrix = build_lens_matrix(graph)
    assert matrix["decision"] == "BLOCK_LENS_MATRIX"
    assert matrix["unknown_lens_tags"] == ["intent"]


def test_failed_upstream_graph_fails_closed():
    graph = base_graph()
    graph["status"] = "FAIL_CLOSED"
    graph["hard_block_hits"] = ["upstream_error"]
    matrix = build_lens_matrix(graph)
    assert "upstream_evidence_graph_failed_closed" in matrix["hard_block_hits"]


def test_duplicate_node_ids_fail_closed():
    graph = base_graph()
    graph["nodes"][1]["node_id"] = graph["nodes"][0]["node_id"]
    matrix = build_lens_matrix(graph)
    assert "duplicate_graph_node_id" in matrix["hard_block_hits"]


def test_forbidden_upstream_output_fails_closed():
    graph = base_graph()
    graph["claim_text"] = "forbidden"
    matrix = build_lens_matrix(graph)
    assert "upstream_graph_forbidden_output_attempted" in matrix["hard_block_hits"]
    assert "claim_text" in matrix["forbidden_upstream_hits"]


def test_canonical_event_count_claim_fails_closed():
    graph = base_graph()
    graph["canonical_event_count"] = 100
    matrix = build_lens_matrix(graph)
    assert "canonical_event_count_claim_rejected" in matrix["hard_block_hits"]
    assert matrix["canonical_event_count"] == "UNKNOWN"


def test_matrix_does_not_emit_claim_or_truth():
    matrix = build_lens_matrix(base_graph())
    assert "claim_text" not in matrix
    assert matrix["claim_output_allowed"] is False
    assert matrix["report_language_allowed"] is False
    for key in [
        "tactical_truth", "dominance_truth", "control_truth", "coach_intention_truth",
        "off_ball_truth", "pitch_control_truth", "causal_truth", "quality_truth",
        "sequence_truth", "organism_truth",
    ]:
        assert matrix[key] is False


def test_report_counts_ready_review_and_blocked():
    ready = base_graph()
    review = base_graph()
    review["graph_id"] = "graph_review"
    review["nodes"] = review["nodes"][:-1]
    blocked = base_graph()
    blocked["graph_id"] = "graph_blocked"
    blocked["claim_text"] = "forbidden"
    report = build_lens_report([ready, review, blocked])
    assert report["ready_count"] == 1
    assert report["review_count"] == 1
    assert report["blocked_count"] == 1
    assert report["status"] == "FAIL_CLOSED"


def test_write_outputs_rejects_nested_phone_output():
    try:
        write_outputs([base_graph()], "/sdcard/Download/HPFA/evidence_lens_matrix_lite")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested phone output directory was not rejected")


def test_write_outputs(tmp_path):
    report = write_outputs([base_graph()], tmp_path)
    assert report["status"] == "SMOKE_PASS"
    assert (tmp_path / "evidence_lens_matrix_lite_v1.json").exists()
    assert (tmp_path / "evidence_lens_matrix_lite_v1.txt").exists()
    loaded = json.loads((tmp_path / "evidence_lens_matrix_lite_v1.json").read_text(encoding="utf-8"))
    assert loaded["matrix_count"] == 1


def test_no_sample_match_identity_leak():
    src = (SRC / "evidence_lens_matrix.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
