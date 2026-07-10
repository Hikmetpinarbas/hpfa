from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "evidence_lens_matrix_lite_v1"
OUTPUT_JSON = "evidence_lens_matrix_lite_v1.json"
OUTPUT_TXT = "evidence_lens_matrix_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "evidence_graph_candidate_only"
LENS_CLAIM_CEILING = "evidence_lens_coverage_candidate_only"
MISSING_GRAPH_ID = "MISSING_GRAPH_ID"

REQUIRED_LENSES = (
    "time",
    "space",
    "actor",
    "team",
    "action",
    "outcome",
    "sequence",
    "context",
    "opponent",
    "contradiction",
)

EXPLICIT_NODE_TYPE_LENSES = {
    "context_ref": "context",
    "contradiction_ref": "contradiction",
}

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
    "report_text",
    "final_report_text",
    "production_report",
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


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _collect_forbidden_hits(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_UPSTREAM_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_collect_forbidden_hits(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(_collect_forbidden_hits(child, child_path))
    return hits


def _forbidden_hits(graph: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(graph)))


def _upstream_failed(graph: dict[str, Any]) -> bool:
    if _as_list(graph.get("hard_block_hits")):
        return True
    if str(graph.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return str(graph.get("decision") or "").upper().startswith("BLOCK")


def _node_lenses(node: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_lenses: list[Any] = []
    raw_lenses.extend(_as_list(node.get("lens")))
    raw_lenses.extend(_as_list(node.get("lenses")))
    payload = node.get("payload")
    if isinstance(payload, dict):
        raw_lenses.extend(_as_list(payload.get("lens")))
        raw_lenses.extend(_as_list(payload.get("lenses")))
    explicit = EXPLICIT_NODE_TYPE_LENSES.get(str(node.get("node_type") or ""))
    if explicit:
        raw_lenses.append(explicit)

    normalized = sorted({str(value).strip().lower() for value in raw_lenses if str(value).strip()})
    known = [lens for lens in normalized if lens in REQUIRED_LENSES]
    unknown = [lens for lens in normalized if lens not in REQUIRED_LENSES]
    return known, unknown


def build_lens_matrix(graph: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(graph)
    graph_id = str(normalized.get("graph_id") or "")
    missing_fields: list[str] = []
    if not graph_id:
        missing_fields.append("graph_id")
        graph_id = MISSING_GRAPH_ID
    if not isinstance(normalized.get("nodes"), list):
        missing_fields.append("nodes")
    if not isinstance(normalized.get("edges"), list):
        missing_fields.append("edges")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    nodes = [node for node in _as_list(normalized.get("nodes")) if isinstance(node, dict)]
    node_ids = [str(node.get("node_id") or "") for node in nodes]
    duplicate_node_ids = sorted({node_id for node_id in node_ids if node_id and node_ids.count(node_id) > 1})
    lens_refs: dict[str, list[str]] = {lens: [] for lens in REQUIRED_LENSES}
    unknown_lens_tags: set[str] = set()
    for node in nodes:
        known, unknown = _node_lenses(node)
        unknown_lens_tags.update(unknown)
        node_id = str(node.get("node_id") or "")
        for lens in known:
            if node_id and node_id not in lens_refs[lens]:
                lens_refs[lens].append(node_id)

    forbidden_upstream_hits = _forbidden_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("lens_matrix_required_fields_missing")
    if _upstream_failed(normalized):
        hard_block_hits.append("upstream_evidence_graph_failed_closed")
    if duplicate_node_ids:
        hard_block_hits.append("duplicate_graph_node_id")
    if unknown_lens_tags:
        hard_block_hits.append("unknown_lens_tag_rejected")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_graph_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_graph_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_graph_report_language_allowed")
    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")

    lens_rows = [
        {
            "lens": lens,
            "status": "COVERED" if lens_refs[lens] else "MISSING",
            "evidence_node_refs": lens_refs[lens],
            "evidence_ref_count": len(lens_refs[lens]),
        }
        for lens in REQUIRED_LENSES
    ]
    covered_lenses = [row["lens"] for row in lens_rows if row["status"] == "COVERED"]
    missing_lenses = [row["lens"] for row in lens_rows if row["status"] == "MISSING"]
    coverage_score = len(covered_lenses) / len(REQUIRED_LENSES)

    if hard_block_hits:
        status = "FAIL_CLOSED"
        decision = "BLOCK_LENS_MATRIX"
    elif missing_lenses:
        status = "REVIEW_REQUIRED"
        decision = "ROUTE_INCOMPLETE_LENS_COVERAGE_TO_REVIEW"
    else:
        status = "SMOKE_PASS"
        decision = "READY_FOR_LENS_AWARE_REVIEW_CANDIDATE"

    return {
        "module_id": MODULE_ID,
        "matrix_id": f"lens_matrix_{graph_id}",
        "graph_id": graph_id,
        "status": status,
        "decision": decision,
        "lenses": lens_rows,
        "covered_lenses": covered_lenses,
        "missing_lenses": missing_lenses,
        "covered_lens_count": len(covered_lenses),
        "required_lens_count": len(REQUIRED_LENSES),
        "coverage_score": coverage_score,
        "coverage_score_meaning": "explicit_lens_inventory_completeness_only",
        "absence_inference_allowed": False,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "duplicate_node_ids": duplicate_node_ids,
        "unknown_lens_tags": sorted(unknown_lens_tags),
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "claim_ceiling": LENS_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "claim_output_allowed": False,
        "report_language_allowed": False,
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


def build_lens_report(graphs: list[dict[str, Any]]) -> dict[str, Any]:
    matrices = [build_lens_matrix(graph) for graph in graphs]
    blocked_count = sum(1 for matrix in matrices if matrix["status"] == "FAIL_CLOSED")
    review_count = sum(1 for matrix in matrices if matrix["status"] == "REVIEW_REQUIRED")
    ready_count = sum(1 for matrix in matrices if matrix["status"] == "SMOKE_PASS")
    status = "FAIL_CLOSED" if blocked_count else "REVIEW_REQUIRED" if review_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "matrix_count": len(matrices),
        "ready_count": ready_count,
        "review_count": review_count,
        "blocked_count": blocked_count,
        "matrices": matrices,
        "claim_ceiling": LENS_CLAIM_CEILING,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "absence_inference_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "evidence_lens_coverage_candidate_only_missing_is_not_absence",
    }


def write_outputs(graphs: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_lens_report(graphs)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA 360 EVIDENCE LENS MATRIX LITE V1",
        "========================================",
        f"status={report['status']}",
        f"matrix_count={report['matrix_count']}",
        f"ready_count={report['ready_count']}",
        f"review_count={report['review_count']}",
        f"blocked_count={report['blocked_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[matrices]",
    ]
    for matrix in report["matrices"][:50]:
        lines.append(
            f"- {matrix['matrix_id']} decision={matrix['decision']} "
            f"coverage_score={matrix['coverage_score']:.2f} "
            f"missing_lenses={','.join(matrix['missing_lenses'])}"
        )
    lines.append("")
    (out / OUTPUT_TXT).write_text("\n".join(lines), encoding="utf-8")
    return report
