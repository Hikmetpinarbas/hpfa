from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "evidence_graph_engine_lite_v1"
OUTPUT_JSON = "evidence_graph_engine_lite_v1.json"
OUTPUT_TXT = "evidence_graph_engine_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "argument_candidate_only"
GRAPH_CLAIM_CEILING = "evidence_graph_candidate_only"
MISSING_ARGUMENT_ID = "MISSING_ARGUMENT_ID"

ALLOWED_NODE_TYPES = {
    "argument",
    "fusion",
    "support_ref",
    "qualifier_ref",
    "contradiction_ref",
    "complement_ref",
    "context_ref",
    "counter_scenario",
    "withdrawal_condition",
    "relation_scope",
    "analysis_route",
}

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
    "report_text",
    "report_language",
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
    "quality_truth",
    "sequence_truth",
    "organism_truth",
}

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
    "quality_truth",
    "sequence_truth",
    "organism_truth",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _validate_output_root(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore

    return validate_output_root(out_dir)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if item not in [None, ""]]


def _argument_id(argument: dict[str, Any]) -> str:
    return str(argument.get("argument_id") or "")


def _forbidden_hits(argument: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for field in FORBIDDEN_UPSTREAM_FIELDS:
        if field in argument and argument.get(field) not in [None, "", False, []]:
            hits.append(field)
    return sorted(hits)


def _upstream_argument_failed(argument: dict[str, Any]) -> bool:
    if _as_list(argument.get("hard_block_hits")):
        return True
    if str(argument.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(argument.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _node(node_id: str, node_type: str, source: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "node_type": node_type,
        "source": source,
        "payload": payload or {},
    }


def _edge(source: str, target: str, relation_type: str) -> dict[str, str]:
    return {
        "source": source,
        "target": target,
        "relation_type": relation_type,
    }


def _ref_nodes_and_edges(argument_id: str, key: str, node_type: str, relation_type: str, refs: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for idx, ref in enumerate(refs):
        node_id = f"{argument_id}:{node_type}:{idx}:{ref}"
        nodes.append(_node(node_id, node_type, key, {"ref": ref}))
        edges.append(_edge(node_id, argument_id, relation_type))
    return nodes, edges


def build_evidence_graph(argument: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(argument)
    argument_id = _argument_id(normalized)
    missing_fields: list[str] = []
    if not argument_id:
        missing_fields.append("argument_id")
        argument_id = MISSING_ARGUMENT_ID
    if "fusion_id" not in normalized or normalized.get("fusion_id") in [None, ""]:
        missing_fields.append("fusion_id")
    if "supporting_refs" not in normalized:
        missing_fields.append("supporting_refs")
    if "claim_ceiling" not in normalized or normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    forbidden_hits = _forbidden_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("argument_required_fields_missing")
    if _upstream_argument_failed(normalized):
        hard_block_hits.append("upstream_argument_failed_closed")
    if forbidden_hits:
        hard_block_hits.append("upstream_argument_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_report_language_allowed")
    if normalized.get("safe_sentence_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_safe_sentence_allowed")

    nodes: list[dict[str, Any]] = [
        _node(argument_id, "argument", "composite_argument_builder_lite_v1", {
            "argument_family": normalized.get("argument_family"),
            "relation_scope": normalized.get("relation_scope"),
            "analysis_route": normalized.get("analysis_route"),
            "claim_ceiling": normalized.get("claim_ceiling"),
        })
    ]
    edges: list[dict[str, str]] = []

    fusion_id = str(normalized.get("fusion_id") or "")
    if fusion_id:
        nodes.append(_node(fusion_id, "fusion", "multi_signal_evidence_fusion_lite_v1", {"fusion_id": fusion_id}))
        edges.append(_edge(fusion_id, argument_id, "BUILDS_ARGUMENT"))

    relation_scope = str(normalized.get("relation_scope") or "")
    if relation_scope:
        scope_id = f"{argument_id}:relation_scope:{relation_scope}"
        nodes.append(_node(scope_id, "relation_scope", "composite_argument_builder_lite_v1", {"relation_scope": relation_scope}))
        edges.append(_edge(scope_id, argument_id, "SCOPES_ARGUMENT"))

    analysis_route = str(normalized.get("analysis_route") or "")
    if analysis_route:
        route_id = f"{argument_id}:analysis_route:{analysis_route}"
        nodes.append(_node(route_id, "analysis_route", "composite_argument_builder_lite_v1", {
            "analysis_route": analysis_route,
            "whole_to_unit": bool(normalized.get("whole_to_unit")),
            "unit_to_whole": bool(normalized.get("unit_to_whole")),
            "bidirectional": bool(normalized.get("bidirectional")),
        }))
        edges.append(_edge(route_id, argument_id, "ROUTES_ARGUMENT"))

    ref_specs = [
        ("supporting_refs", "support_ref", "SUPPORTS_ARGUMENT"),
        ("qualifying_refs", "qualifier_ref", "QUALIFIES_ARGUMENT"),
        ("contradicting_refs", "contradiction_ref", "CONTRADICTS_ARGUMENT"),
        ("complementary_refs", "complement_ref", "COMPLEMENTS_ARGUMENT"),
        ("context_refs", "context_ref", "CONTEXTUALIZES_ARGUMENT"),
        ("counter_scenarios", "counter_scenario", "CHALLENGES_ARGUMENT"),
        ("withdrawal_conditions", "withdrawal_condition", "WITHDRAWS_ARGUMENT_IF_TRUE"),
    ]
    for key, node_type, relation_type in ref_specs:
        new_nodes, new_edges = _ref_nodes_and_edges(argument_id, key, node_type, relation_type, _string_list(normalized.get(key)))
        nodes.extend(new_nodes)
        edges.extend(new_edges)

    node_ids = [node["node_id"] for node in nodes]
    duplicate_node_ids = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
    if duplicate_node_ids:
        hard_block_hits.append("duplicate_graph_node_id")
    if not _string_list(normalized.get("supporting_refs")):
        hard_block_hits.append("supporting_refs_required_for_graph")

    status = "FAIL_CLOSED" if hard_block_hits else "SMOKE_PASS"
    decision = "BLOCK_GRAPH" if hard_block_hits else "READY_FOR_EVIDENCE_TRACE_CONSUMER"

    return {
        "module_id": MODULE_ID,
        "graph_id": f"graph_{argument_id}",
        "argument_id": argument_id,
        "fusion_id": fusion_id,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "duplicate_node_ids": duplicate_node_ids,
        "trace_start": fusion_id,
        "trace_end": argument_id,
        "claim_ceiling": GRAPH_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "status": status,
        "decision": decision,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_output_hits": forbidden_hits,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "control_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "pitch_control_truth": False,
        "causal_truth": False,
        "quality_truth": False,
        "sequence_truth": False,
        "organism_truth": False,
        "blocked_language_families": list(BLOCKED_LANGUAGE_FAMILIES),
        "canonical_event_count": "UNKNOWN",
    }


def build_graph_report(arguments: list[dict[str, Any]]) -> dict[str, Any]:
    graphs = [build_evidence_graph(argument, idx) for idx, argument in enumerate(arguments)]
    blocked_count = sum(1 for graph in graphs if graph["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "graph_count": len(graphs),
        "blocked_graph_count": blocked_count,
        "graphs": graphs,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "claim_ceiling": GRAPH_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "evidence_graph_candidate_only_no_sentence_no_claim_text",
    }


def write_outputs(arguments: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_graph_report(arguments)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA EVIDENCE GRAPH ENGINE LITE V1",
        "===================================",
        f"status={report['status']}",
        f"graph_count={report['graph_count']}",
        f"blocked_graph_count={report['blocked_graph_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[graphs]",
    ]
    for graph in report["graphs"][:50]:
        lines.append(
            f"- {graph['graph_id']} argument={graph['argument_id']} nodes={graph['node_count']} "
            f"edges={graph['edge_count']} status={graph['status']} decision={graph['decision']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
