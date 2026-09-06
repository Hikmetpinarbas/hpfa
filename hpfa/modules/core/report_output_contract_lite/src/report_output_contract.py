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

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "report_text",
    "final_report_text",
    "production_report",
    "production_report_output",
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

FORBIDDEN_BLOCK_FRAGMENTS = [
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

ALLOWED_BLOCK_FAMILIES = {
    "analyst_reading_candidate",
    "technical_limit_candidate",
    "evidence_note_candidate",
    "review_required_candidate",
    "sequence_safe_finding_analyst_reading_candidate",
    "sequence_narrative_analyst_reading_candidate",
}
SEQUENCE_BLOCK_FAMILIES = {
    "sequence_safe_finding_analyst_reading_candidate",
    "sequence_narrative_analyst_reading_candidate",
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


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if item not in [None, ""]]


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
    if str(block.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


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
    if not isinstance(support, int) or support < 0:
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
                if null_summary.get("significance_claim_allowed") is not False:
                    hits.append("sequence_lineage_null_contrast_significance_lock_breach")
                if null_summary.get("tactical_pattern_truth_allowed") is not False:
                    hits.append("sequence_lineage_null_contrast_tactical_truth_lock_breach")

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
                for flag in (
                    "chronology_direction_claimed",
                    "causality_claimed",
                    "tactical_adaptation_claimed",
                    "coach_intention_claimed",
                ):
                    if variation.get(flag) is not False:
                        hits.append(f"sequence_lineage_context_variation_claim_lock_breach:{flag}")
                baseline_refs = set(_string_list(variation.get("baseline_trace_refs")))
                comparison_refs = set(_string_list(variation.get("comparison_trace_refs")))
                if not baseline_refs.issubset(trace_ref_set) or not comparison_refs.issubset(trace_ref_set):
                    hits.append("sequence_lineage_context_variation_trace_lineage_mismatch")
                context_variations.append(variation)

    return {
        "trace_family_refs": family_refs,
        "trace_variant_refs": trace_refs,
        "counterevidence_refs": counter_refs,
        "dependency_summary": dict(dependency or {}),
        "robustness_summary": dict(robustness or {}),
        "uncertainty": dict(uncertainty or {}),
        "withdrawal_condition": withdrawal,
        "observed_support": support,
        "upstream_claim_ceiling": upstream_claim_ceiling,
        "origin_claim_ceiling": origin_claim_ceiling,
        "null_contrast_summary": null_summary,
        "context_variations": context_variations,
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

    if hard_block_hits:
        inclusion_decision = "REJECT_BLOCK"
        status = "FAIL_CLOSED"
        output_text = ""
    elif review_hits:
        inclusion_decision = "REVIEW_BLOCK"
        status = "REVIEW_REQUIRED"
        output_text = ""
    else:
        inclusion_decision = "INCLUDE_BLOCK_CANDIDATE"
        status = "SMOKE_PASS"
        output_text = text

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
        "module_id": MODULE_ID,
        "status": status,
        "contract_item_count": len(items),
        "include_count": include_count,
        "review_count": review_count,
        "rejected_count": rejected_count,
        "contract_items": items,
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "claim_ceiling": OUTPUT_CONTRACT_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_boundary": "report_output_contract_candidate_only_not_final_report",
    }


def write_outputs(blocks: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_output_contract(blocks)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA REPORT OUTPUT CONTRACT LITE V1",
        "====================================",
        f"status={report['status']}",
        f"contract_item_count={report['contract_item_count']}",
        f"include_count={report['include_count']}",
        f"review_count={report['review_count']}",
        f"rejected_count={report['rejected_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        f"true_action_count={report['true_action_count']}",
        "production_release=false",
        "",
        "[contract_items]",
    ]
    for item in report["contract_items"][:50]:
        lines.append(f"- {item['contract_item_id']} decision={item['inclusion_decision']} status={item['status']}")
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
