from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

CLAIM_SAFETY = "EVIDENCE_ONLY"
UNKNOWN_STATUSES = {"UNKNOWN", "MISSING", "ABSTAIN"}


@dataclass(frozen=True)
class MetricNode:
    metric_id: str
    value: float | int | str
    status: str
    surface_id: str
    confidence: float = 1.0


@dataclass(frozen=True)
class MetricEdge:
    from_metric: str
    to_metric: str
    relation: str
    strength: float
    reason: str
    claim_safety: str = CLAIM_SAFETY


def _pair(a: MetricNode, b: MetricNode) -> frozenset[str]:
    return frozenset({a.metric_id, b.metric_id})


def _min_confidence(a: MetricNode, b: MetricNode) -> float:
    return round(max(0.0, min(1.0, min(a.confidence, b.confidence))), 4)


def build_relation(a: MetricNode, b: MetricNode) -> MetricEdge | None:
    """Build one claim-safe relation between two primitive metric nodes.

    V1 is deliberately small. It does not calculate football truth. It only records
    relation candidates that later Claim Gate / Football Output Audit may inspect.
    """
    if a.status in UNKNOWN_STATUSES or b.status in UNKNOWN_STATUSES:
        return None

    pair = _pair(a, b)
    strength = _min_confidence(a, b)

    if pair == frozenset({"M_PROG_PASS_COUNT", "M_FINAL_THIRD_ENTRY_COUNT"}):
        return MetricEdge(
            from_metric=a.metric_id,
            to_metric=b.metric_id,
            relation="SUPPORTS",
            strength=strength,
            reason="Progressive pass count and final-third entry count support the same progression evidence family.",
        )

    if pair == frozenset({"M_SHOT_COUNT", "M_ACTIONS_IN_BOX_COUNT"}):
        return MetricEdge(
            from_metric=a.metric_id,
            to_metric=b.metric_id,
            relation="CONTEXTUALIZES",
            strength=strength,
            reason="Shot volume requires box-action context before any attacking claim can be considered.",
        )

    if pair == frozenset({"M_PASS_COUNT", "M_SEQUENCE_LENGTH"}):
        return MetricEdge(
            from_metric=a.metric_id,
            to_metric=b.metric_id,
            relation="COMPLEMENTS",
            strength=strength,
            reason="Pass count and sequence length complement each other for possession-circulation evidence.",
        )

    if pair == frozenset({"M_PROG_PASS_COUNT", "M_TURNOVER_COUNT"}):
        return MetricEdge(
            from_metric=a.metric_id,
            to_metric=b.metric_id,
            relation="CONTEXTUALIZES",
            strength=strength,
            reason="Progression volume must be interpreted together with turnover exposure.",
        )

    return None


def build_support_graph(nodes: list[MetricNode]) -> dict[str, Any]:
    edges: list[MetricEdge] = []
    for i, left in enumerate(nodes):
        for right in nodes[i + 1:]:
            edge = build_relation(left, right)
            if edge is not None:
                edges.append(edge)

    return {
        "graph_id": "metric_support_graph_v1",
        "status": "PASS",
        "nodes": [asdict(n) for n in nodes],
        "edges": [asdict(e) for e in edges],
        "claim_safety": CLAIM_SAFETY,
        "report_language_allowed": False,
        "production_binding_allowed": False,
    }
