from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "report_output_contract_lite_v1"
OUTPUT_JSON = "report_output_contract_lite_v1.json"
OUTPUT_TXT = "report_output_contract_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "analyst_report_block_candidate_only"
OUTPUT_CONTRACT_CLAIM_CEILING = "report_output_contract_candidate_only"
MISSING_REPORT_BLOCK_ID = "MISSING_REPORT_BLOCK_ID"
SEQUENCE_FINDING_CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
SEQUENCE_NARRATIVE_CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"
MATCH_STORY_CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY"
NULL_CONTRAST_CLAIM_CEILING = "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY"

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text", "report_text", "final_report_text", "production_report",
    "production_report_output", "tactical_truth", "dominance_truth", "control_truth",
    "coach_intention", "coach_intention_truth", "off_ball_truth", "pitch_control_truth",
    "causal_truth", "quality_truth", "sequence_truth", "organism_truth",
}

FORBIDDEN_BLOCK_FRAGMENTS = [
    "domine etti", "saha kontrolünü aldı", "hoca planladı", "bilinçli olarak",
    "taktiksel gerçek", "kesin", "kanıtlıyor", "nedeni budur", "off-ball yapı",
    "pitch control", "oyun kontrolü",
]

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth", "dominance_truth", "control_truth", "coach_intention",
    "off_ball_truth", "pitch_control_truth", "causal_truth", "quality_truth",
    "sequence_truth", "organism_truth",
]

ALLOWED_BLOCK_FAMILIES = {
    "analyst_reading_candidate", "technical_limit_candidate", "evidence_note_candidate",
    "review_required_candidate", "sequence_safe_finding_analyst_reading_candidate",
    "sequence_narrative_analyst_reading_candidate", "match_story_analyst_reading_candidate",
}
SEQUENCE_BLOCK_FAMILIES = {
    "sequence_safe_finding_analyst_reading_candidate",
    "sequence_narrative_analyst_reading_candidate",
}
MATCH_STORY_BLOCK_FAMILIES = {"match_story_analyst_reading_candidate"}


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


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _report_block_id(block: dict[str, Any]) -> str:
    return str(block.get("report_block_id") or "")


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


def _forbidden_upstream_hits(block: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(block)))


def _upstream_block_failed(block: dict[str, Any]) -> bool:
    if _as_list(block.get("hard_block_hits")):
        return True
    if str(block.get("decision") or "").upper().startswith("BLOCK"):
        return True
    return str(block.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}


def _upstream_review_required(block: dict[str, Any]) -> bool:
    if block.get("review_required") is True:
        return True
    if _as_list(block.get("review_reasons")):
        return True
    if str(block.get("status") or "").upper() == "REVIEW_REQUIRED":
        return True
    return str(block.get("block_family") or "") == "review_required_candidate"


def _forbidden_text_hits(text: str) -> list[str]:
    lower = text.lower()
    return [fragment for fragment in FORBIDDEN_BLOCK_FRAGMENTS if fragment in lower]


def _sequence_lineage(block: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    block_family = str(block.get("block_family") or "")
    family_refs = sorted(set(_string_list(block.get("trace_family_refs"))))
    trace_refs = sorted(set(_string_list(block.get("trace_variant_refs"))))
    counter_refs = sorted(set(_string_list(block.get("counterevidence_refs"))))
    dependency = block.get("dependency_summary") if isinstance(block.get("dependency_summary"), dict) else None
    robustness = block.get("robustness_summary") if isinstance(block.get("robustness_summary"), dict) else None
    uncertainty = block.get("uncertainty") if isinstance(block.get("uncertainty"), dict) else None
    withdrawal = str(block.get("withdrawal_condition") or "").strip()
    upstream_claim_ceiling = str(block.get("upstream_claim_ceiling") or "").strip()
    origin_claim_ceiling = str(block.get("origin_claim_ceiling") or "").strip()
    support = block.get("observed_support")
    raw_null_summary = block.get("null_contrast_summary")
    raw_context_variations = block.get("context_variations")
    hits: list[str] = []

    if not family_refs:
        hits.append("sequence_lineage_trace_family_refs_missing")
    if not trace_refs:
        hits.append("sequence_lineage_trace_variant_refs_missing")
    if not isinstance(support, int) or isinstance(support, bool) or support < 0:
        hits.append("sequence_lineage_observed_support_invalid")
    elif len(trace_refs) != support:
        hits.append("sequence_lineage_trace_cohort_support_mismatch")
    if family_refs and trace_refs and family_refs[0] not in trace_refs:
        hits.append("sequence_lineage_anchor_not_in_trace_cohort")
    if dependency is None:
        hits.append("sequence_lineage_dependency_summary_missing")
    if robustness is None:
        hits.append("sequence_lineage_robustness_summary_missing")
    if uncertainty is None:
        hits.append("sequence_lineage_uncertainty_missing")
    if not withdrawal:
        hits.append("sequence_lineage_withdrawal_condition_missing")
    if not upstream_claim_ceiling:
        hits.append("sequence_lineage_upstream_claim_ceiling_missing")
    elif block_family == "sequence_safe_finding_analyst_reading_candidate" and upstream_claim_ceiling != SEQUENCE_FINDING_CLAIM_CEILING:
        hits.append("sequence_lineage_upstream_claim_ceiling_mismatch")
    elif block_family == "sequence_narrative_analyst_reading_candidate" and upstream_claim_ceiling != SEQUENCE_NARRATIVE_CLAIM_CEILING:
        hits.append("sequence_lineage_upstream_claim_ceiling_mismatch")
    if block_family == "sequence_narrative_analyst_reading_candidate":
        if not origin_claim_ceiling:
            hits.append("sequence_lineage_origin_claim_ceiling_missing")
        elif origin_claim_ceiling != SEQUENCE_FINDING_CLAIM_CEILING:
            hits.append("sequence_lineage_origin_claim_ceiling_mismatch")
    elif origin_claim_ceiling:
        hits.append("sequence_lineage_unexpected_origin_claim_ceiling")

    null_summary: dict[str, Any] = {}
    if raw_null_summary is not None:
        if not isinstance(raw_null_summary, dict):
            hits.append("sequence_lineage_null_contrast_summary_invalid")
        else:
            null_summary = dict(raw_null_summary)
            if null_summary.get("claim_strengthened") is not False:
                hits.append("sequence_lineage_null_contrast_claim_strengthened")
            null_state = str(null_summary.get("state") or "NOT_EVALUATED").strip()
            if null_state != "NOT_EVALUATED":
                if str(null_summary.get("claim_ceiling") or "").strip() != NULL_CONTRAST_CLAIM_CEILING:
                    hits.append("sequence_lineage_null_contrast_claim_ceiling_mismatch")
                if null_summary.get("multiple_testing_corrected") is not False:
                    hits.append("sequence_lineage_null_contrast_multiple_testing_lock_breach")
                if null_summary.get("significance_claim_allowed") is not False:
                    hits.append("sequence_lineage_null_contrast_significance_lock_breach")
                if null_summary.get("tactical_pattern_truth_allowed") is not False:
                    hits.append("sequence_lineage_null_contrast_tactical_truth_lock_breach")
                if null_summary.get("causality_allowed") is not False:
                    hits.append("sequence_lineage_null_contrast_causality_lock_breach")
                simulation_count = null_summary.get("simulation_count")
                if not isinstance(simulation_count, int) or isinstance(simulation_count, bool) or simulation_count < 1:
                    hits.append("sequence_lineage_null_contrast_simulation_count_invalid")
                else:
                    tail_resolution = null_summary.get("empirical_upper_tail_resolution")
                    expected_resolution = 1 / (simulation_count + 1)
                    if not isinstance(tail_resolution, (int, float)) or isinstance(tail_resolution, bool) or abs(float(tail_resolution) - expected_resolution) > 1e-12:
                        hits.append("sequence_lineage_null_contrast_tail_resolution_mismatch")
                if null_summary.get("finite_simulation_resolution_only") is not True:
                    hits.append("sequence_lineage_null_contrast_finite_resolution_lock_breach")
                if not str(null_summary.get("withdrawal_condition") or "").strip():
                    hits.append("sequence_lineage_null_contrast_withdrawal_condition_missing")

    context_variations: list[dict[str, Any]] = []
    if raw_context_variations is not None:
        if not isinstance(raw_context_variations, list):
            hits.append("sequence_lineage_context_variations_invalid")
        else:
            trace_ref_set = set(trace_refs)
            for raw_variation in raw_context_variations:
                if not isinstance(raw_variation, dict):
                    hits.append("sequence_lineage_context_variation_invalid")
                    continue
                variation = dict(raw_variation)
                for flag in ("chronology_direction_claimed", "causality_claimed", "tactical_adaptation_claimed", "coach_intention_claimed"):
                    if variation.get(flag) is not False:
                        hits.append(f"sequence_lineage_context_variation_claim_lock_breach:{flag}")
                baseline_refs = set(_string_list(variation.get("baseline_trace_refs")))
                comparison_refs = set(_string_list(variation.get("comparison_trace_refs")))
                if not baseline_refs.issubset(trace_ref_set) or not comparison_refs.issubset(trace_ref_set):
                    hits.append("sequence_lineage_context_variation_trace_lineage_mismatch")
                context_variations.append(variation)

    return {
        "trace_family_refs": family_refs, "trace_variant_refs": trace_refs,
        "counterevidence_refs": counter_refs, "dependency_summary": dict(dependency or {}),
        "robustness_summary": dict(robustness or {}), "uncertainty": dict(uncertainty or {}),
        "withdrawal_condition": withdrawal, "observed_support": support,
        "upstream_claim_ceiling": upstream_claim_ceiling, "origin_claim_ceiling": origin_claim_ceiling,
        "null_contrast_summary": null_summary, "context_variations": context_variations,
    }, hits


def _match_story_lineage(block: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    source_ids = sorted(set(_string_list(block.get("source_narrative_ids"))))
    trace_refs = sorted(set(_string_list(block.get("unique_trace_refs"))))
    shared_refs = sorted(set(_string_list(block.get("shared_trace_refs_across_processes"))))
    unique_count = block.get("unique_trace_ref_count")
    nominal_support = block.get("nominal_support_sum")
    process_count = block.get("process_narrative_count")
    recurrent_count = block.get("recurrent_process_count")
    robust_count = block.get("robust_recurrent_process_count")
    counter_count = block.get("counterevidence_bearing_process_count")
    context_count = block.get("context_sensitive_process_count")
    null_count = block.get("null_evaluated_process_count")
    accounting = {
        "process_narrative_count": process_count,
        "recurrent_process_count": recurrent_count,
        "robust_recurrent_process_count": robust_count,
        "counterevidence_bearing_process_count": counter_count,
        "context_sensitive_process_count": context_count,
        "null_evaluated_process_count": null_count,
    }
    withdrawal = str(block.get("withdrawal_condition") or "").strip()
    upstream_claim_ceiling = str(block.get("upstream_claim_ceiling") or "").strip()
    hits: list[str] = []

    if not source_ids:
        hits.append("match_story_lineage_source_narrative_ids_missing")
    if not trace_refs:
        hits.append("match_story_lineage_unique_trace_refs_missing")
    for key, value in accounting.items():
        if not _is_nonnegative_int(value):
            hits.append(f"match_story_lineage_{key}_invalid")
    if _is_nonnegative_int(process_count):
        if process_count != len(source_ids):
            hits.append("match_story_lineage_process_narrative_count_mismatch")
        for key, value in accounting.items():
            if key != "process_narrative_count" and _is_nonnegative_int(value) and value > process_count:
                hits.append(f"match_story_lineage_{key}_exceeds_process_count")
    if _is_nonnegative_int(robust_count) and _is_nonnegative_int(recurrent_count) and robust_count > recurrent_count:
        hits.append("match_story_lineage_robust_recurrent_process_count_exceeds_recurrent")
    if not _is_nonnegative_int(unique_count):
        hits.append("match_story_lineage_unique_trace_ref_count_invalid")
    elif unique_count != len(trace_refs):
        hits.append("match_story_lineage_unique_trace_ref_count_mismatch")
    if not _is_nonnegative_int(nominal_support) or nominal_support < len(trace_refs):
        hits.append("match_story_lineage_nominal_support_invalid")
    if not set(shared_refs).issubset(set(trace_refs)):
        hits.append("match_story_lineage_shared_trace_refs_not_subset")
    if block.get("nominal_support_is_independent_evidence_count") is not False:
        hits.append("match_story_lineage_nominal_support_independence_lock_breach")
    if block.get("cross_process_support_independence_proven") is not False:
        hits.append("match_story_lineage_cross_process_independence_lock_breach")
    if not withdrawal:
        hits.append("match_story_lineage_withdrawal_condition_missing")
    if upstream_claim_ceiling != MATCH_STORY_CLAIM_CEILING:
        hits.append("match_story_lineage_upstream_claim_ceiling_mismatch")

    return {
        "source_narrative_ids": source_ids,
        "process_narrative_count": process_count,
        "recurrent_process_count": recurrent_count,
        "robust_recurrent_process_count": robust_count,
        "counterevidence_bearing_process_count": counter_count,
        "context_sensitive_process_count": context_count,
        "null_evaluated_process_count": null_count,
        "unique_trace_refs": trace_refs,
        "unique_trace_ref_count": unique_count,
        "shared_trace_refs_across_processes": shared_refs,
        "nominal_support_sum": nominal_support,
        "nominal_support_is_independent_evidence_count": False,
        "cross_process_support_independence_proven": False,
        "story_state": str(block.get("story_state") or ""),
        "entity_scope": str(block.get("entity_scope") or ""),
        "withdrawal_condition": withdrawal,
        "upstream_claim_ceiling": upstream_claim_ceiling,
    }, hits


def evaluate_report_block(block: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(block)
    block_id = _report_block_id(normalized)
    missing_fields: list[str] = []
    if not block_id:
        missing_fields.append("report_block_id")
        block_id = MISSING_REPORT_BLOCK_ID
    if "report_block_candidate_tr" not in normalized or normalized.get("report_block_candidate_tr") in [None, ""]:
        missing_fields.append("report_block_candidate_tr")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    block_family = str(normalized.get("block_family") or "")
    if block_family not in ALLOWED_BLOCK_FAMILIES:
        missing_fields.append("block_family")

    forbidden_upstream_hits = _forbidden_upstream_hits(normalized)
    hard_block_hits: list[str] = []
    review_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("report_block_required_fields_missing")
    if _upstream_block_failed(normalized):
        hard_block_hits.append("upstream_report_block_failed_closed")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_report_block_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_claim_output_allowed")
    if normalized.get("production_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_production_output_allowed")
    if normalized.get("final_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_final_output_allowed")

    text = str(normalized.get("report_block_candidate_tr") or "")
    forbidden_block_hits = _forbidden_text_hits(text)
    if forbidden_block_hits:
        hard_block_hits.append("report_block_forbidden_language_detected")

    upstream_review_required = _upstream_review_required(normalized)
    upstream_review_reasons = _string_list(normalized.get("review_reasons"))
    if block_family == "review_required_candidate":
        review_hits.append("block_family_requires_review")
    if upstream_review_required:
        review_hits.append("upstream_report_block_requires_review")
        if not upstream_review_reasons:
            upstream_review_reasons = ["upstream_report_block_review_required"]
    review_hits = sorted(set(review_hits))

    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")
    if normalized.get("true_action_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("true_action_count_claim_rejected")
    if normalized.get("production_release") is True:
        hard_block_hits.append("production_release_claim_rejected")

    sequence_lineage: dict[str, Any] = {}
    if block_family in SEQUENCE_BLOCK_FAMILIES:
        sequence_lineage, lineage_hits = _sequence_lineage(normalized)
        hard_block_hits.extend(lineage_hits)

    match_story_lineage: dict[str, Any] = {}
    if block_family in MATCH_STORY_BLOCK_FAMILIES:
        match_story_lineage, lineage_hits = _match_story_lineage(normalized)
        hard_block_hits.extend(lineage_hits)

    if hard_block_hits:
        inclusion_decision, status, output_text = "REJECT_BLOCK", "FAIL_CLOSED", ""
    elif review_hits:
        inclusion_decision, status, output_text = "REVIEW_BLOCK", "REVIEW_REQUIRED", ""
    else:
        inclusion_decision, status, output_text = "INCLUDE_BLOCK_CANDIDATE", "SMOKE_PASS", text

    return {
        "module_id": MODULE_ID,
        "contract_item_id": f"contract_{block_id}",
        "report_block_id": block_id,
        "block_family": block_family,
        "block_language": str(normalized.get("block_language") or "UNKNOWN"),
        "defeasible_state": str(normalized.get("defeasible_state") or ""),
        "upstream_review_required": upstream_review_required,
        "upstream_review_reasons": upstream_review_reasons,
        "inclusion_decision": inclusion_decision,
        "output_text_candidate_tr": output_text,
        "claim_ceiling": OUTPUT_CONTRACT_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "upstream_status": normalized.get("status"),
        "upstream_decision": normalized.get("decision"),
        "status": status,
        "hard_block_hits": sorted(set(hard_block_hits)),
        "review_hits": review_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "forbidden_block_hits": forbidden_block_hits,
        "sequence_evidence_lineage": sequence_lineage,
        "match_story_evidence_lineage": match_story_lineage,
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
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
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def build_output_contract(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    items = [evaluate_report_block(block, idx) for idx, block in enumerate(blocks)]
    rejected_count = sum(1 for item in items if item["inclusion_decision"] == "REJECT_BLOCK")
    review_count = sum(1 for item in items if item["inclusion_decision"] == "REVIEW_BLOCK")
    include_count = sum(1 for item in items if item["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE")
    status = "FAIL_CLOSED" if rejected_count else "REVIEW_REQUIRED" if review_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID, "status": status, "contract_item_count": len(items),
        "include_count": include_count, "review_count": review_count, "rejected_count": rejected_count,
        "contract_items": items, "claim_output_allowed": False, "final_report_allowed": False,
        "production_report_allowed": False, "claim_ceiling": OUTPUT_CONTRACT_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False,
        "claim_boundary": "report_output_contract_candidate_only_not_final_report",
    }


def write_outputs(blocks: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_output_contract(blocks)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA REPORT OUTPUT CONTRACT LITE V1", "====================================",
        f"status={report['status']}", f"contract_item_count={report['contract_item_count']}",
        f"include_count={report['include_count']}", f"review_count={report['review_count']}",
        f"rejected_count={report['rejected_count']}", f"canonical_event_count={report['canonical_event_count']}",
        f"true_action_count={report['true_action_count']}", "production_release=false", "", "[contract_items]",
    ]
    for item in report["contract_items"][:50]:
        lines.append(f"- {item['contract_item_id']} decision={item['inclusion_decision']} status={item['status']}")
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report