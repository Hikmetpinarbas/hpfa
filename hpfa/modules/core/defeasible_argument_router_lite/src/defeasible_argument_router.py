from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "defeasible_argument_router_lite_v1"
OUTPUT_JSON = "defeasible_argument_router_lite_v1.json"
OUTPUT_TXT = "defeasible_argument_router_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "argument_candidate_only"
ROUTER_CLAIM_CEILING = "defeasible_argument_candidate_only"
MISSING_ARGUMENT_ID = "MISSING_ARGUMENT_ID"

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
    "report_text",
    "report_language",
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


def _string_list(value: Any) -> list[str]:
    return sorted({str(item) for item in _as_list(value) if item not in [None, ""]})


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


def _forbidden_hits(argument: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(argument)))


def _upstream_failed(argument: dict[str, Any]) -> bool:
    if _as_list(argument.get("hard_block_hits")):
        return True
    if str(argument.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return str(argument.get("decision") or "").upper().startswith("BLOCK")


def route_argument(argument: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(argument)
    argument_id = str(normalized.get("argument_id") or "")
    missing_fields: list[str] = []
    if not argument_id:
        missing_fields.append("argument_id")
        argument_id = MISSING_ARGUMENT_ID
    for field in ["supporting_refs", "contradicting_refs", "withdrawal_conditions"]:
        if field not in normalized:
            missing_fields.append(field)
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    supporting_refs = _string_list(normalized.get("supporting_refs"))
    qualifying_refs = _string_list(normalized.get("qualifying_refs"))
    upstream_contradicting_refs = _string_list(normalized.get("contradicting_refs"))
    runtime_counter_refs = _string_list(normalized.get("counter_evidence_refs"))
    counter_evidence_refs = sorted(set(upstream_contradicting_refs + runtime_counter_refs))
    declared_withdrawal_conditions = _string_list(normalized.get("withdrawal_conditions"))
    triggered_withdrawal_conditions = _string_list(normalized.get("triggered_withdrawal_conditions"))
    matched_withdrawal_conditions = sorted(
        set(declared_withdrawal_conditions).intersection(triggered_withdrawal_conditions)
    )
    unmatched_triggered_conditions = sorted(
        set(triggered_withdrawal_conditions).difference(declared_withdrawal_conditions)
    )

    forbidden_upstream_hits = _forbidden_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("defeasible_router_required_fields_missing")
    if _upstream_failed(normalized):
        hard_block_hits.append("upstream_argument_failed_closed")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_argument_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_report_language_allowed")
    if normalized.get("safe_sentence_allowed") not in [False, None]:
        hard_block_hits.append("upstream_argument_safe_sentence_allowed")
    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")
    if unmatched_triggered_conditions:
        hard_block_hits.append("undeclared_withdrawal_condition_rejected")
    if not supporting_refs:
        hard_block_hits.append("supporting_evidence_required")
    if matched_withdrawal_conditions and not counter_evidence_refs:
        hard_block_hits.append("withdrawal_requires_explicit_counter_evidence")

    if hard_block_hits:
        status = "FAIL_CLOSED"
        defeasible_state = "BLOCKED"
        decision = "BLOCK_ARGUMENT_ROUTE"
    elif matched_withdrawal_conditions:
        status = "SMOKE_PASS"
        defeasible_state = "WITHDRAWN"
        decision = "ROUTE_ARGUMENT_AS_WITHDRAWN_CANDIDATE"
    elif counter_evidence_refs or qualifying_refs:
        status = "SMOKE_PASS"
        defeasible_state = "WEAKENED"
        decision = "ROUTE_ARGUMENT_AS_WEAKENED_CANDIDATE"
    else:
        status = "SMOKE_PASS"
        defeasible_state = "SUPPORTED"
        decision = "ROUTE_ARGUMENT_AS_SUPPORTED_CANDIDATE"

    return {
        "module_id": MODULE_ID,
        "route_id": f"defeasible_route_{argument_id}",
        "argument_id": argument_id,
        "fusion_id": str(normalized.get("fusion_id") or ""),
        "argument_family": str(normalized.get("argument_family") or ""),
        "relation_scope": str(normalized.get("relation_scope") or ""),
        "analysis_route": str(normalized.get("analysis_route") or ""),
        "whole_to_unit": bool(normalized.get("whole_to_unit")),
        "unit_to_whole": bool(normalized.get("unit_to_whole")),
        "bidirectional": bool(normalized.get("bidirectional")),
        "complementary_refs": _string_list(normalized.get("complementary_refs")),
        "context_refs": _string_list(normalized.get("context_refs")),
        "counter_scenarios": _string_list(normalized.get("counter_scenarios")),
        "upstream_argument_status": str(normalized.get("status") or ""),
        "upstream_argument_decision": str(normalized.get("decision") or ""),
        "status": status,
        "defeasible_state": defeasible_state,
        "decision": decision,
        "supporting_refs": supporting_refs,
        "qualifying_refs": qualifying_refs,
        "counter_evidence_refs": counter_evidence_refs,
        "declared_withdrawal_conditions": declared_withdrawal_conditions,
        "triggered_withdrawal_conditions": triggered_withdrawal_conditions,
        "matched_withdrawal_conditions": matched_withdrawal_conditions,
        "unmatched_triggered_conditions": unmatched_triggered_conditions,
        "support_count": len(supporting_refs),
        "qualifier_count": len(qualifying_refs),
        "counter_evidence_count": len(counter_evidence_refs),
        "absence_of_counter_evidence_proves_support": False,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "claim_ceiling": ROUTER_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
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


def build_router_report(arguments: list[dict[str, Any]]) -> dict[str, Any]:
    routes = [route_argument(argument) for argument in arguments]
    state_counts = {state: sum(1 for route in routes if route["defeasible_state"] == state) for state in ["SUPPORTED", "WEAKENED", "WITHDRAWN", "BLOCKED"]}
    status = "FAIL_CLOSED" if state_counts["BLOCKED"] else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "route_count": len(routes),
        "state_counts": state_counts,
        "routes": routes,
        "claim_ceiling": ROUTER_CLAIM_CEILING,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "defeasible_argument_candidate_only_no_claim_no_truth",
    }


def write_outputs(arguments: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_router_report(arguments)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA DEFEASIBLE ARGUMENT ROUTER LITE V1",
        "========================================",
        f"status={report['status']}",
        f"route_count={report['route_count']}",
        f"state_counts={json.dumps(report['state_counts'], sort_keys=True)}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[routes]",
    ]
    for route in report["routes"][:50]:
        lines.append(
            f"- {route['route_id']} state={route['defeasible_state']} decision={route['decision']} "
            f"support={route['support_count']} counter={route['counter_evidence_count']} "
            f"withdrawal_matches={len(route['matched_withdrawal_conditions'])}"
        )
    lines.append("")
    (out / OUTPUT_TXT).write_text("\n".join(lines), encoding="utf-8")
    return report
