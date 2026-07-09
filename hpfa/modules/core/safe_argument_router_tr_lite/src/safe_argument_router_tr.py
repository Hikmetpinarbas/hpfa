from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "safe_argument_router_tr_lite_v1"
OUTPUT_JSON = "safe_argument_router_tr_lite_v1.json"
OUTPUT_TXT = "safe_argument_router_tr_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "evidence_graph_candidate_only"
SAFE_SENTENCE_CLAIM_CEILING = "safe_sentence_candidate_only"
MISSING_GRAPH_ID = "MISSING_GRAPH_ID"

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "report_text",
    "report_language",
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "coach_intention_truth",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
    "quality_truth",
    "sequence_truth",
    "organism_truth",
}

FORBIDDEN_OUTPUT_FRAGMENTS = [
    "domine etti",
    "saha kontrolünü aldı",
    "hoca planladı",
    "bilinçli olarak",
    "taktiksel gerçek",
    "kesin",
    "kanıtlıyor",
    "nedeni budur",
    "off-ball yapı",
    "pitch control",
    "oyun kontrolü",
]

SAFE_PREFIX_BY_STATUS = {
    "SMOKE_PASS": "Görünür kanıt grafiği",
    "REVIEW_REQUIRED": "Gözden geçirme gerektiren kanıt grafiği",
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


def _graph_id(graph: dict[str, Any]) -> str:
    return str(graph.get("graph_id") or "")


def _forbidden_upstream_hits(graph: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for field in FORBIDDEN_UPSTREAM_FIELDS:
        if field in graph and graph.get(field) not in [None, "", False, []]:
            hits.append(field)
    return sorted(hits)


def _upstream_graph_failed(graph: dict[str, Any]) -> bool:
    if _as_list(graph.get("hard_block_hits")):
        return True
    if str(graph.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(graph.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _nodes_by_type(graph: dict[str, Any], node_type: str) -> list[dict[str, Any]]:
    return [node for node in _as_list(graph.get("nodes")) if isinstance(node, dict) and node.get("node_type") == node_type]


def _payload_refs(graph: dict[str, Any], node_type: str) -> list[str]:
    refs: list[str] = []
    for node in _nodes_by_type(graph, node_type):
        payload = node.get("payload") if isinstance(node.get("payload"), dict) else {}
        if payload.get("ref") not in [None, ""]:
            refs.append(str(payload["ref"]))
    return refs


def _first_payload_value(graph: dict[str, Any], node_type: str, key: str) -> str:
    for node in _nodes_by_type(graph, node_type):
        payload = node.get("payload") if isinstance(node.get("payload"), dict) else {}
        if payload.get(key) not in [None, ""]:
            return str(payload[key])
    return "UNKNOWN"


def _clip(values: list[str], limit: int = 2) -> str:
    if not values:
        return "yok"
    return ", ".join(values[:limit])


def _safe_sentence(graph: dict[str, Any]) -> str:
    support_refs = _payload_refs(graph, "support_ref")
    qualifier_refs = _payload_refs(graph, "qualifier_ref")
    contradiction_refs = _payload_refs(graph, "contradiction_ref")
    context_refs = _payload_refs(graph, "context_ref")
    counter_scenarios = _payload_refs(graph, "counter_scenario")
    withdrawal_conditions = _payload_refs(graph, "withdrawal_condition")
    relation_scope = _first_payload_value(graph, "relation_scope", "relation_scope")
    analysis_route = _first_payload_value(graph, "analysis_route", "analysis_route")

    sentence = (
        f"Görünür kanıt grafiği {relation_scope} kapsamındaki {analysis_route} okumasında "
        f"{_clip(support_refs)} referanslarının argüman adayını desteklediğini; "
        f"{_clip(qualifier_refs)} referanslarının okumayı nitelendirdiğini"
    )
    if contradiction_refs:
        sentence += f"; {_clip(contradiction_refs)} referanslarının açık çelişki sinyali taşıdığını"
    if context_refs:
        sentence += f"; {_clip(context_refs)} referanslarının bağlam verdiğini"
    if counter_scenarios:
        sentence += f"; {_clip(counter_scenarios)} karşı senaryosunun dikkate alınması gerektiğini"
    if withdrawal_conditions:
        sentence += f"; {_clip(withdrawal_conditions)} gerçekleşirse aday okumanın geri çekilebileceğini"
    sentence += " gösterir."
    return sentence


def _forbidden_sentence_hits(sentence: str) -> list[str]:
    lower = sentence.lower()
    return [fragment for fragment in FORBIDDEN_OUTPUT_FRAGMENTS if fragment in lower]


def route_safe_sentence(graph: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(graph)
    graph_id = _graph_id(normalized)
    missing_fields: list[str] = []
    if not graph_id:
        missing_fields.append("graph_id")
        graph_id = MISSING_GRAPH_ID
    if "nodes" not in normalized:
        missing_fields.append("nodes")
    if "edges" not in normalized:
        missing_fields.append("edges")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    forbidden_upstream_hits = _forbidden_upstream_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("graph_required_fields_missing")
    if _upstream_graph_failed(normalized):
        hard_block_hits.append("upstream_graph_failed_closed")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_graph_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_graph_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_graph_report_language_allowed")

    sentence_candidate = "" if hard_block_hits else _safe_sentence(normalized)
    forbidden_sentence_hits = _forbidden_sentence_hits(sentence_candidate)
    if forbidden_sentence_hits:
        hard_block_hits.append("safe_sentence_forbidden_language_detected")
        sentence_candidate = ""

    status = "FAIL_CLOSED" if hard_block_hits else "SMOKE_PASS"
    decision = "BLOCK_SAFE_SENTENCE" if hard_block_hits else "READY_FOR_REPORT_COMPOSER_CANDIDATE"

    return {
        "module_id": MODULE_ID,
        "safe_sentence_id": f"safe_sentence_{graph_id}",
        "graph_id": graph_id,
        "sentence_candidate_tr": sentence_candidate,
        "sentence_language": "tr",
        "claim_ceiling": SAFE_SENTENCE_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "status": status,
        "decision": decision,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "forbidden_sentence_hits": forbidden_sentence_hits,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": True if not hard_block_hits else False,
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


def build_safe_sentence_report(graphs: list[dict[str, Any]]) -> dict[str, Any]:
    routed = [route_safe_sentence(graph, idx) for idx, graph in enumerate(graphs)]
    blocked_count = sum(1 for item in routed if item["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "safe_sentence_count": len(routed),
        "blocked_safe_sentence_count": blocked_count,
        "safe_sentences": routed,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "claim_ceiling": SAFE_SENTENCE_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "safe_sentence_candidate_only_no_claim_text_no_report_language",
    }


def write_outputs(graphs: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_safe_sentence_report(graphs)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA SAFE ARGUMENT ROUTER TR LITE V1",
        "======================================",
        f"status={report['status']}",
        f"safe_sentence_count={report['safe_sentence_count']}",
        f"blocked_safe_sentence_count={report['blocked_safe_sentence_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[safe_sentence_candidates]",
    ]
    for item in report["safe_sentences"][:50]:
        lines.append(f"- {item['safe_sentence_id']} status={item['status']} decision={item['decision']}")
        if item["sentence_candidate_tr"]:
            lines.append(f"  {item['sentence_candidate_tr']}")
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
