from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

MODULE_ID = "context_conditioned_trace_deviation_lite_v1"
VARIANT_MODULE_ID = "partial_order_trace_variant_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "CONTEXT_CONDITIONED_VISIBLE_TRACE_DEVIATION_CANDIDATE_ONLY"
ALLOWED_CONTEXT_DIMENSIONS = {
    "period_candidate",
    "start_reason_candidate",
    "end_reason_candidate",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _signature(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fail(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "context_conditioned_trace_deviations": [],
        "context_conditioned_trace_deviation_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_context_conditioned_trace_deviations(
    variant_payload: dict[str, Any],
    *,
    context_dimension: str,
    baseline_context_value: str,
    comparison_context_value: str,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if variant_payload.get("module_id") != VARIANT_MODULE_ID:
        blocks.append("variant_module_id_mismatch")
    if variant_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("variant_canonical_event_count_claimed")
    if variant_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("variant_true_action_count_claimed")
    if variant_payload.get("production_release") is True:
        blocks.append("variant_production_release_claimed")
    if variant_payload.get("hard_block_hits") or _clean(variant_payload.get("status")).upper() == "FAIL_CLOSED":
        blocks.append("variant_input_fail_closed")
    elif _clean(variant_payload.get("status")).upper() == "REVIEW_REQUIRED":
        reviews.append("variant_upstream_review_required")

    dimension = _clean(context_dimension)
    baseline_value = _clean(baseline_context_value)
    comparison_value = _clean(comparison_context_value)
    if dimension not in ALLOWED_CONTEXT_DIMENSIONS:
        blocks.append(f"unsupported_context_dimension:{dimension or 'UNKNOWN'}")
    if not baseline_value or not comparison_value:
        blocks.append("context_value_missing")
    if baseline_value == comparison_value:
        blocks.append("context_values_must_differ")

    variants = [row for row in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(row, dict)]
    if not variants:
        blocks.append("partial_order_trace_variants_empty")
    if blocks:
        return _fail(blocks, reviews)

    missing_context_refs: list[str] = []
    by_family: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in variants:
        ref = _clean(row.get("trace_variant_id"))
        context = row.get("context_signature") if isinstance(row.get("context_signature"), dict) else {}
        raw_value = context.get(dimension)
        value = _clean(raw_value)
        if not value:
            if ref:
                missing_context_refs.append(ref)
            continue
        if value not in {baseline_value, comparison_value}:
            continue
        family_signature = {
            "action_family_signature": row.get("action_family_signature") or [],
            "ordering_completeness": row.get("ordering_completeness"),
        }
        family_ref = "ctf_" + _digest(family_signature)[:24]
        by_family.setdefault(family_ref, {baseline_value: [], comparison_value: []})[value].append(row)

    out: list[dict[str, Any]] = []
    for family_ref, cohorts in sorted(by_family.items()):
        baseline = cohorts[baseline_value]
        comparison = cohorts[comparison_value]
        if not baseline or not comparison:
            continue

        def distributions(rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
            variant_counts: Counter[str] = Counter()
            outcome_counts: Counter[str] = Counter()
            sequence_counts: Counter[str] = Counter()
            for item in rows:
                variant_counts[_signature({
                    "action_family_signature": item.get("action_family_signature") or [],
                    "ordering_completeness": item.get("ordering_completeness"),
                })] += 1
                outcome_counts[_signature(item.get("outcome_signature") or [])] += 1
                ctx = item.get("context_signature") if isinstance(item.get("context_signature"), dict) else {}
                sequence_counts[_clean(ctx.get("end_reason_candidate")) or "UNKNOWN_END_REASON"] += 1
            return dict(sorted(variant_counts.items())), dict(sorted(outcome_counts.items())), dict(sorted(sequence_counts.items()))

        base_variant, base_outcome, base_sequence = distributions(baseline)
        comp_variant, comp_outcome, comp_sequence = distributions(comparison)
        base_deps = sorted({_clean(v) for row in baseline for v in (row.get("dependency_group_refs") or []) if _clean(v)})
        comp_deps = sorted({_clean(v) for row in comparison for v in (row.get("dependency_group_refs") or []) if _clean(v)})
        shared_deps = sorted(set(base_deps) & set(comp_deps))
        sample_warning = None
        if len(baseline) < 2 or len(comparison) < 2:
            sample_warning = "SMALL_CONTEXT_COHORT_REVIEW_REQUIRED"
            reviews.append(f"small_context_cohort:{family_ref}")

        outcome_diff = base_outcome != comp_outcome
        sequence_diff = base_sequence != comp_sequence
        if outcome_diff and sequence_diff:
            effect = "VISIBLE_OUTCOME_AND_SEQUENCE_DISTRIBUTION_DIFFERENCE_CANDIDATE"
        elif outcome_diff:
            effect = "VISIBLE_OUTCOME_DISTRIBUTION_DIFFERENCE_CANDIDATE"
        elif sequence_diff:
            effect = "VISIBLE_SEQUENCE_DISTRIBUTION_DIFFERENCE_CANDIDATE"
        else:
            effect = "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION"

        out.append({
            "context_conditioned_trace_deviation_id": "ctd_" + _digest(family_ref, dimension, baseline_value, comparison_value)[:24],
            "trace_family_ref": family_ref,
            "context_dimension": dimension,
            "context_value": comparison_value,
            "baseline_cohort_ref": f"{dimension}:{baseline_value}",
            "comparison_cohort_ref": f"{dimension}:{comparison_value}",
            "baseline_trace_refs": sorted(_clean(row.get("trace_variant_id")) for row in baseline),
            "comparison_trace_refs": sorted(_clean(row.get("trace_variant_id")) for row in comparison),
            "baseline_variant_distribution": base_variant,
            "comparison_variant_distribution": comp_variant,
            "baseline_outcome_distribution": base_outcome,
            "comparison_outcome_distribution": comp_outcome,
            "baseline_sequence_distribution": base_sequence,
            "comparison_sequence_distribution": comp_sequence,
            "support_difference": len(comparison) - len(baseline),
            "outcome_difference": outcome_diff,
            "sequence_difference": sequence_diff,
            "effect_descriptor": effect,
            "uncertainty": {
                "cohort_counts_are_independence_truth": False,
                "missing_context_is_zero": False,
                "missing_context_trace_count": len(missing_context_refs),
            },
            "sample_warning": sample_warning,
            "counterevidence": "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION" if not outcome_diff and not sequence_diff else None,
            "alternative_explanations": [
                "SAMPLE_COMPOSITION",
                "DEPENDENT_EVIDENCE",
                "UNOBSERVED_VIDEO_TRACKING_CONTEXT",
            ],
            "dependency_summary": {
                "baseline_dependency_group_refs": base_deps,
                "comparison_dependency_group_refs": comp_deps,
                "shared_dependency_group_refs": shared_deps,
                "independence_proven": False,
            },
            "context_difference_is_causality_truth": False,
            "context_difference_is_tactical_adaptation_truth": False,
            "context_difference_is_coach_intention_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if not out:
        reviews.append("no_trace_family_with_both_context_cohorts")
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "context_conditioned_trace_deviations": out,
        "context_conditioned_trace_deviation_count": len(out),
        "context_dimension": dimension,
        "baseline_context_value": baseline_value,
        "comparison_context_value": comparison_value,
        "missing_context_trace_refs": sorted(set(missing_context_refs)),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "context_difference_is_causality_truth": False,
        "context_difference_is_tactical_adaptation_truth": False,
        "context_difference_is_coach_intention_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
