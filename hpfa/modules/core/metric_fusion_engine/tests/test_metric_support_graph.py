from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_fusion_engine" / "src"
sys.path.insert(0, str(SRC))

from metric_support_graph import MetricNode, build_relation, build_support_graph


def node(metric_id, value=1, status="PASS", surface_id="players_csv", confidence=0.8):
    return MetricNode(
        metric_id=metric_id,
        value=value,
        status=status,
        surface_id=surface_id,
        confidence=confidence,
    )


def test_progression_and_final_third_support_relation():
    edge = build_relation(
        node("M_PROG_PASS_COUNT", 12, confidence=0.7),
        node("M_FINAL_THIRD_ENTRY_COUNT", 8, confidence=0.9),
    )

    assert edge is not None
    assert edge.relation == "SUPPORTS"
    assert edge.claim_safety == "EVIDENCE_ONLY"
    assert edge.strength == 0.7


def test_shots_and_box_actions_contextualize_relation():
    edge = build_relation(
        node("M_SHOT_COUNT", 14),
        node("M_ACTIONS_IN_BOX_COUNT", 20),
    )

    assert edge is not None
    assert edge.relation == "CONTEXTUALIZES"
    assert edge.claim_safety == "EVIDENCE_ONLY"


def test_unknown_metric_status_abstains_from_relation():
    edge = build_relation(
        node("M_PROG_PASS_COUNT", 12, status="UNKNOWN"),
        node("M_FINAL_THIRD_ENTRY_COUNT", 8),
    )

    assert edge is None


def test_build_support_graph_blocks_report_language():
    graph = build_support_graph([
        node("M_PROG_PASS_COUNT", 12),
        node("M_FINAL_THIRD_ENTRY_COUNT", 8),
        node("M_PASS_COUNT", 420),
        node("M_SEQUENCE_LENGTH", 9),
    ])

    assert graph["status"] == "PASS"
    assert graph["claim_safety"] == "EVIDENCE_ONLY"
    assert graph["report_language_allowed"] is False
    assert graph["production_binding_allowed"] is False
    assert len(graph["edges"]) == 2
    assert {edge["relation"] for edge in graph["edges"]} == {"SUPPORTS", "COMPLEMENTS"}
