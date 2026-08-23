from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "composite_argument_builder_lite_v1"
OUTPUT_JSON = "composite_argument_builder_lite_v1.json"
OUTPUT_TXT = "composite_argument_builder_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "fusion_relation_candidate_only"
ARGUMENT_CLAIM_CEILING = "argument_candidate_only"
MISSING_FUSION_ID = "MISSING_FUSION_ID"

ALLOWED_ARGUMENT_FAMILIES = {
    "progression_without_terminal_value",
    "territory_access_without_shot_conversion",
    "recovery_to_progression_chain",
    "restart_dependency_with_low_open_play_value",
    "high_loss_exposure_under_context",
    "corridor_bias_with_terminal_limit",
    "circulation_without_penetration",
    "direct_play_isolation_candidate",
    "late_terminal_pressure_candidate",
    "defensive_event_height_without_pressing_truth",
    "player_function_proxy_from_sequence_role",
    "rhythm_shift_candidate_from_event_density",
}

RELATION_SCOPE_TYPES = {
    "standalone_observation",
    "context_bound_relation",
    "sequence_candidate",
}

ANALYSIS_ROUTE_TYPES = {
    "unit_to_whole",
    "whole_to_unit",
    "bidirectional",
    "undetermined",
}

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
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

DEFAULT_COUNTER_SCENARIOS = {
    "progression_without_terminal_value": [
        "shot_timing_or_angle_limited_terminal_action",
        "opponent_setup_at_terminal_moment_limited_shot_selection",
        "sample_window_may_understate_terminal_output",
    ],
    "territory_access_without_shot_conversion": [
        "territory_access_may_be_low_value_access",
        "box_entry_surface_may_be_missing_or_sparse",
    ],
    "recovery_to_progression_chain": [
        "recovery_location_may_explain_progression_access",
        "sequence_window_may_be_too_short",
    ],
    "corridor_bias_with_terminal_limit": [
        "corridor_access_may_be_opponent_concession_not_plan_truth",
        "terminal_options_may_be_blocked_at_action_moment",
    ],
}

DEFAULT_WITHDRAWAL_CONDITIONS = {
    "progression_without_terminal_value": [
        "terminal_action_value_becomes_high_in_same_window",
        "box_entry_and_shot_quality_support_conversion",
    ],
    "territory_access_without_shot_conversion": [
        "shot_conversion_surface_supports_territory_output",
        "access_window_not_repeated",
    ],
    "recovery_to_progression_chain": [
        "sequence_repetition_not_detected",
        "progression_after_recovery_not_present",
    ],
    "corridor_bias_with_terminal_limit": [
        "opposite_corridor_has_equal_or_stronger_access",
        "terminal_conversion_not_limited",
    ],
}


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


def _fusion_id(fusion: dict[str, Any]) -> str:
    return str(fusion.get("fusion_id") or "")


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


def _forbidden_hits(fusion: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(fusion)))


def _relation_records(fusion: dict[str, Any]) -> list[dict[str, Any]]:
    return [record for record in _as_list(fusion.get("relation_records")) if isinstance(record, dict)]


def _relations_by_type(fusion: dict[str, Any], relation_type: str) -> list[str]:
    refs: list[str] = []
    for record in _relation_records(fusion):
        if str(record.get("relation_type") or "").upper() == relation_type:
            if record.get("signal_ref") not in [None, ""]:
                refs.append(str(record["signal_ref"]))
    return refs


def _has_sequence_marker(fusion: dict[str, Any]) -> bool:
    if fusion.get("sequence_candidate") is True:
        return True
    if fusion.get("sequence_window_id") not in [None, "", []]:
        return True
    if fusion.get("sequence_refs") not in [None, "", []]:
        return True
    for record in _relation_records(fusion):
        role = str(record.get("evidence_role") or "").lower()
        ref = str(record.get("signal_ref") or "").lower()
        if "sequence" in role or "sequence" in ref:
            return True
        if record.get("sequence_candidate") is True:
            return True
    return False


def _has_context_marker(fusion: dict[str, Any]) -> bool:
    if fusion.get("context_window") not in [None, "", []]:
        return True
    if fusion.get("context_refs") not in [None, "", []]:
        return True
    if _relations_by_type(fusion, "CONTEXTUALIZES"):
        return True
    return False


def _relation_scope(fusion: dict[str, Any]) -> str:
    explicit_scope = str(fusion.get("relation_scope") or "")
    if explicit_scope in RELATION_SCOPE_TYPES:
        return explicit_scope
    if _has_sequence_marker(fusion):
        return "sequence_candidate"
    if _has_context_marker(fusion):
        return "context_bound_relation"
    return "standalone_observation"


def _has_unit_surface(fusion: dict[str, Any]) -> bool:
    if fusion.get("unit_refs") not in [None, "", []]:
        return True
    for record in _relation_records(fusion):
        role = str(record.get("evidence_role") or "").lower()
        ref = str(record.get("signal_ref") or "").lower()
        if any(token in role for token in ["feature", "metric", "action", "event", "player", "unit"]):
            return True
        if any(token in ref for token in ["feature", "metric", "action", "event", "player", "entry", "shot", "pass", "carry", "duel", "recovery", "loss"]):
            return True
    return bool(_relations_by_type(fusion, "SUPPORTS") or _relations_by_type(fusion, "COMPLEMENTS"))


def _has_whole_surface(fusion: dict[str, Any]) -> bool:
    if fusion.get("whole_refs") not in [None, "", []]:
        return True
    if fusion.get("context_window") not in [None, "", []]:
        return True
    if fusion.get("team_context") not in [None, "", []]:
        return True
    if fusion.get("phase_context") not in [None, "", []]:
        return True
    if _relations_by_type(fusion, "CONTEXTUALIZES"):
        return True
    for record in _relation_records(fusion):
        role = str(record.get("evidence_role") or "").lower()
        ref = str(record.get("signal_ref") or "").lower()
        if any(token in role for token in ["context", "window", "phase", "team", "whole", "sequence"]):
            return True
        if any(token in ref for token in ["context", "window", "phase", "team", "whole", "sequence", "corridor", "zone"]):
            return True
    return False


def _analysis_route(fusion: dict[str, Any]) -> str:
    explicit_route = str(fusion.get("analysis_route") or "")
    if explicit_route in ANALYSIS_ROUTE_TYPES:
        return explicit_route
    has_unit = _has_unit_surface(fusion)
    has_whole = _has_whole_surface(fusion)
    if has_unit and has_whole:
        return "bidirectional"
    if has_unit:
        return "unit_to_whole"
    if has_whole:
        return "whole_to_unit"
    return "undetermined"


def _default_argument_family(fusion: dict[str, Any]) -> str:
    family = str(fusion.get("argument_family") or fusion.get("packet_family") or "")
    if family in ALLOWED_ARGUMENT_FAMILIES:
        return family
    if family == "progression":
        return "progression_without_terminal_value"
    if family == "production_consequence":
        return "progression_without_terminal_value"
    if family == "restart":
        return "restart_dependency_with_low_open_play_value"
    if family == "risk":
        return "high_loss_exposure_under_context"
    if family == "tempo":
        return "rhythm_shift_candidate_from_event_density"
    return "progression_without_terminal_value"


def _upstream_fusion_failed(fusion: dict[str, Any]) -> bool:
    if _as_list(fusion.get("hard_block_hits")):
        return True
    if str(fusion.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(fusion.get("fusion_status") or "").upper() == "BLOCKED":
        return True
    if str(fusion.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _status_and_decision(hard_block_hits: list[str], support_refs: list[str], qualifier_refs: list[str], contradiction_refs: list[str]) -> tuple[str, str]:
    if hard_block_hits:
        return "BLOCKED", "BLOCK_ARGUMENT"
    if not support_refs:
        return "REVIEW_REQUIRED", "INSUFFICIENT_SUPPORT"
    if contradiction_refs:
        return "ARGUMENT_WITH_EXPLICIT_CONTRADICTION", "READY_FOR_SAFE_ROUTER_WITH_CONTRADICTION"
    if qualifier_refs:
        return "ARGUMENT_WITH_QUALIFIER", "READY_FOR_SAFE_ROUTER_WITH_QUALIFIER"
    return "ARGUMENT_SUPPORTED", "READY_FOR_SAFE_ROUTER"


def build_argument_candidate(fusion: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(fusion)
    fusion_id = _fusion_id(normalized)
    missing_fields: list[str] = []
    if not fusion_id:
        missing_fields.append("fusion_id")
        fusion_id = MISSING_FUSION_ID

    if "relation_records" not in normalized:
        missing_fields.append("relation_records")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    forbidden_hits = _forbidden_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("fusion_required_fields_missing")
    if _upstream_fusion_failed(normalized):
        hard_block_hits.append("upstream_fusion_failed_closed")
    if forbidden_hits:
        hard_block_hits.append("upstream_fusion_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_fusion_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_fusion_report_language_allowed")

    support_refs = _relations_by_type(normalized, "SUPPORTS")
    qualifier_refs = _relations_by_type(normalized, "QUALIFIES")
    contradiction_refs = _relations_by_type(normalized, "CONTRADICTS")
    complement_refs = _relations_by_type(normalized, "COMPLEMENTS")
    context_refs = _relations_by_type(normalized, "CONTEXTUALIZES")

    relation_scope = _relation_scope(normalized)
    analysis_route = _analysis_route(normalized)
    sequence_candidate = relation_scope == "sequence_candidate"
    standalone_observation = relation_scope == "standalone_observation"
    context_bound_relation = relation_scope == "context_bound_relation"
    whole_to_unit = analysis_route in {"whole_to_unit", "bidirectional"}
    unit_to_whole = analysis_route in {"unit_to_whole", "bidirectional"}
    bidirectional = analysis_route == "bidirectional"

    argument_family = _default_argument_family(normalized)
    if argument_family in {"recovery_to_progression_chain", "direct_play_isolation_candidate", "late_terminal_pressure_candidate"} and not sequence_candidate:
        hard_block_hits.append("sequence_argument_requires_sequence_scope")
    if argument_family == "rhythm_shift_candidate_from_event_density" and relation_scope == "standalone_observation":
        hard_block_hits.append("rhythm_argument_requires_context_or_sequence_scope")
    if analysis_route == "undetermined":
        hard_block_hits.append("analysis_route_undetermined")

    counter_scenarios = list(normalized.get("counter_scenarios") or DEFAULT_COUNTER_SCENARIOS.get(argument_family) or [
        "alternative_explanation_may_account_for_observed_relation",
        "sample_window_or_surface_coverage_may_limit_argument",
    ])
    withdrawal_conditions = list(normalized.get("withdrawal_conditions") or DEFAULT_WITHDRAWAL_CONDITIONS.get(argument_family) or [
        "supporting_relation_disappears_in_same_context",
        "explicit_contradiction_becomes_stronger_than_support",
    ])

    if standalone_observation:
        counter_scenarios.append("observation_may_be_munferit_not_chain_evidence")
        withdrawal_conditions.append("no_context_or_sequence_marker_available")
    if context_bound_relation:
        counter_scenarios.append("context_may_explain_relation_without_sequence_dependency")
    if sequence_candidate:
        counter_scenarios.append("precedent_successor_link_requires_sequence_validation")
        withdrawal_conditions.append("sequence_marker_removed_or_window_not_repeated")
    if analysis_route == "unit_to_whole":
        counter_scenarios.append("unit_surface_may_not_scale_to_whole_pattern")
        withdrawal_conditions.append("whole_context_does_not_support_unit_signal")
    if analysis_route == "whole_to_unit":
        counter_scenarios.append("whole_surface_may_not_explain_individual_action")
        withdrawal_conditions.append("unit_signal_not_present_inside_whole_context")
    if bidirectional:
        counter_scenarios.append("bidirectional_alignment_requires_both_routes_to_remain_present")
        withdrawal_conditions.append("unit_or_whole_route_removed_from_evidence_packet")

    if not counter_scenarios:
        hard_block_hits.append("counter_scenario_required")
    if not withdrawal_conditions:
        hard_block_hits.append("withdrawal_condition_required")

    status, decision = _status_and_decision(hard_block_hits, support_refs, qualifier_refs, contradiction_refs)

    return {
        "module_id": MODULE_ID,
        "argument_id": f"arg_{fusion_id}",
        "fusion_id": fusion_id,
        "argument_family": argument_family,
        "relation_scope": relation_scope,
        "analysis_route": analysis_route,
        "whole_to_unit": whole_to_unit,
        "unit_to_whole": unit_to_whole,
        "bidirectional": bidirectional,
        "standalone_observation": standalone_observation,
        "context_bound_relation": context_bound_relation,
        "sequence_candidate": sequence_candidate,
        "sequence_truth": False,
        "organism_truth": False,
        "supporting_refs": support_refs,
        "qualifying_refs": qualifier_refs,
        "contradicting_refs": contradiction_refs,
        "complementary_refs": complement_refs,
        "context_refs": context_refs,
        "counter_scenarios": counter_scenarios,
        "withdrawal_conditions": withdrawal_conditions,
        "minimum_support_count": 1,
        "claim_ceiling": ARGUMENT_CLAIM_CEILING,
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
        "blocked_language_families": list(BLOCKED_LANGUAGE_FAMILIES),
        "canonical_event_count": "UNKNOWN",
    }


def build_argument_report(fusions: list[dict[str, Any]]) -> dict[str, Any]:
    arguments = [build_argument_candidate(fusion, idx) for idx, fusion in enumerate(fusions)]
    blocked_count = sum(1 for argument in arguments if argument["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "argument_count": len(arguments),
        "blocked_argument_count": blocked_count,
        "arguments": arguments,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": False,
        "claim_ceiling": ARGUMENT_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "argument_candidate_only_no_sentence_no_claim_text",
    }


def write_outputs(fusions: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_argument_report(fusions)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA COMPOSITE ARGUMENT BUILDER LITE V1",
        "========================================",
        f"status={report['status']}",
        f"argument_count={report['argument_count']}",
        f"blocked_argument_count={report['blocked_argument_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[arguments]",
    ]
    for argument in report["arguments"][:50]:
        lines.append(
            f"- {argument['argument_id']} family={argument['argument_family']} scope={argument['relation_scope']} "
            f"route={argument['analysis_route']} status={argument['status']} decision={argument['decision']} "
            f"support={len(argument['supporting_refs'])} qualifies={len(argument['qualifying_refs'])} "
            f"contradicts={len(argument['contradicting_refs'])}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
