from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "discipline_lens_registry_lite_v1"
OUTPUT_JSON = "discipline_lens_registry_lite_v1.json"
OUTPUT_TXT = "discipline_lens_registry_lite_v1.txt"
REGISTRY_CLAIM_CEILING = "discipline_diagnostic_candidate_only"

FORBIDDEN_FIELDS = {
    "claim_text", "safe_sentence", "safe_sentence_candidate_tr", "report_text",
    "report_language", "final_report_text", "production_report", "tactical_truth",
    "dominance_truth", "control_truth", "coach_intention", "coach_intention_truth",
    "off_ball_truth", "pitch_control_truth", "causal_truth", "quality_truth",
    "sequence_truth", "organism_truth",
}

BLOCKED_LANGUAGE_FAMILIES = sorted(FORBIDDEN_FIELDS)

DISCIPLINE_REGISTRY: dict[str, dict[str, Any]] = {
    "statistics": {
        "allowed_primitives": ["distribution_summary", "rate_comparison", "uncertainty_interval", "sample_size_check"],
        "required_inputs": ["observations", "sample_size"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
    "entropy": {
        "allowed_primitives": ["categorical_entropy", "event_mix_dispersion", "window_distribution_change"],
        "required_inputs": ["categorical_counts", "observation_window"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
    "graph_theory": {
        "allowed_primitives": ["degree_summary", "centrality_candidate", "component_structure", "edge_density"],
        "required_inputs": ["nodes", "edges"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
    "geometry": {
        "allowed_primitives": ["coordinate_distance", "angle_candidate", "zone_occupancy", "corridor_intersection"],
        "required_inputs": ["event_coordinates", "pitch_dimensions"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
    "bayes": {
        "allowed_primitives": ["prior_posterior_update_candidate", "likelihood_ratio_candidate", "uncertainty_revision"],
        "required_inputs": ["prior", "observed_evidence", "likelihood_model"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
    "game_theory": {
        "allowed_primitives": ["observed_choice_set", "payoff_proxy_table", "response_pattern_candidate"],
        "required_inputs": ["observed_actions", "context_states", "declared_payoff_proxy"],
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _validate_output_root(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore
    return validate_output_root(out_dir)


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, [], {}]


def _scan_forbidden(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_scan_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_scan_forbidden(child, f"{path}[{index}]"))
    return sorted(set(hits))


def _upstream_failed(request: dict[str, Any]) -> bool:
    if request.get("hard_block_hits"):
        return True
    if str(request.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return str(request.get("decision") or "").upper().startswith("BLOCK")


def evaluate_lens_request(request: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(request)
    request_id = str(normalized.get("request_id") or "MISSING_REQUEST_ID")
    discipline = str(normalized.get("discipline") or "")
    primitive = str(normalized.get("diagnostic_primitive") or "")
    supplied_inputs = normalized.get("inputs") if isinstance(normalized.get("inputs"), dict) else {}
    registry_entry = DISCIPLINE_REGISTRY.get(discipline)

    missing_fields: list[str] = []
    for field in ["request_id", "discipline", "diagnostic_primitive", "inputs"]:
        if field not in normalized or normalized.get(field) in [None, "", {}]:
            missing_fields.append(field)

    forbidden_hits = _scan_forbidden(normalized)
    hard_block_hits: list[str] = []
    review_hits: list[str] = []

    if missing_fields:
        hard_block_hits.append("discipline_lens_required_fields_missing")
    if _upstream_failed(normalized):
        hard_block_hits.append("upstream_request_failed_closed")
    if forbidden_hits:
        hard_block_hits.append("forbidden_output_attempted")
    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")
    if normalized.get("claim_output_allowed") not in [None, False]:
        hard_block_hits.append("claim_output_not_allowed")
    if normalized.get("report_language_allowed") not in [None, False]:
        hard_block_hits.append("report_language_not_allowed")

    missing_inputs: list[str] = []
    if registry_entry is None:
        review_hits.append("unregistered_discipline")
    else:
        if primitive not in registry_entry["allowed_primitives"]:
            review_hits.append("primitive_not_allowed_for_discipline")
        missing_inputs = [name for name in registry_entry["required_inputs"] if supplied_inputs.get(name) in [None, "", [], {}]]
        if missing_inputs:
            review_hits.append("required_discipline_inputs_missing")

    if hard_block_hits:
        status = "FAIL_CLOSED"
        decision = "BLOCK_DISCIPLINE_LENS"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "ROUTE_DISCIPLINE_LENS_TO_REVIEW"
    else:
        status = "SMOKE_PASS"
        decision = "INCLUDE_DISCIPLINE_LENS_CANDIDATE"

    return {
        "module_id": MODULE_ID,
        "request_id": request_id,
        "discipline": discipline,
        "diagnostic_primitive": primitive,
        "status": status,
        "decision": decision,
        "required_inputs": list(registry_entry["required_inputs"]) if registry_entry else [],
        "supplied_input_keys": sorted(supplied_inputs),
        "missing_inputs": missing_inputs,
        "missing_fields": missing_fields,
        "review_hits": review_hits,
        "hard_block_hits": hard_block_hits,
        "forbidden_upstream_hits": forbidden_hits,
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
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
        "canonical_event_count": "UNKNOWN",
        "blocked_language_families": BLOCKED_LANGUAGE_FAMILIES,
    }


def build_registry_report(requests: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = [evaluate_lens_request(request) for request in requests]
    decision_counts = {
        decision: sum(1 for item in evaluations if item["decision"] == decision)
        for decision in ["INCLUDE_DISCIPLINE_LENS_CANDIDATE", "ROUTE_DISCIPLINE_LENS_TO_REVIEW", "BLOCK_DISCIPLINE_LENS"]
    }
    status = "FAIL_CLOSED" if decision_counts["BLOCK_DISCIPLINE_LENS"] else ("REVIEW_REQUIRED" if decision_counts["ROUTE_DISCIPLINE_LENS_TO_REVIEW"] else "SMOKE_PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "registry": DISCIPLINE_REGISTRY,
        "request_count": len(evaluations),
        "decision_counts": decision_counts,
        "evaluations": evaluations,
        "claim_ceiling": REGISTRY_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
    }


def write_outputs(requests: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_registry_report(requests)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA DISCIPLINE LENS REGISTRY LITE V1",
        "======================================",
        f"status={report['status']}",
        f"request_count={report['request_count']}",
        f"decision_counts={json.dumps(report['decision_counts'], sort_keys=True)}",
        "canonical_event_count=UNKNOWN",
    ]
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
