from __future__ import annotations

from typing import Any

MODULE_ID = "recurrence_robustness_envelope_lite_v1"
VARIANT_MODULE_ID = "partial_order_trace_variant_lite_v1"
CONTRAST_MODULE_ID = "trace_contrast_packet_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "RECURRENCE_ROBUSTNESS_ENVELOPE_CANDIDATE_ONLY"
DEFAULT_THRESHOLDS = (0.70, 0.80, 0.90)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _fail(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID, "status": "FAIL_CLOSED",
        "recurrence_robustness_envelopes": [], "recurrence_robustness_envelope_count": 0,
        "hard_block_hits": sorted(set(blocks)), "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False, "claim_ceiling": CLAIM_CEILING,
    }


def build_recurrence_robustness_envelopes(
    variant_payload: dict[str, Any], contrast_payload: dict[str, Any],
    *, tested_similarity_thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload, expected in (
        ("variant", variant_payload, VARIANT_MODULE_ID),
        ("contrast", contrast_payload, CONTRAST_MODULE_ID),
    ):
        if payload.get("module_id") != expected: blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT: blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}: blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True: blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits") or _clean(payload.get("status")).upper() == "FAIL_CLOSED": blocks.append(f"{name}_input_fail_closed")
        elif _clean(payload.get("status")).upper() == "REVIEW_REQUIRED": reviews.append(f"{name}_upstream_review_required")
    try:
        thresholds = tuple(sorted({round(float(v), 6) for v in tested_similarity_thresholds if 0 <= float(v) <= 1}))
    except (TypeError, ValueError):
        thresholds = ()
    if not thresholds: blocks.append("tested_similarity_threshold_range_empty")
    variants = [v for v in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(v, dict)]
    by_id = {_clean(v.get("trace_variant_id")): v for v in variants if _clean(v.get("trace_variant_id"))}
    packets = [p for p in (contrast_payload.get("trace_contrast_packets") or []) if isinstance(p, dict)]
    if not packets: blocks.append("trace_contrast_packets_empty")
    if blocks: return _fail(blocks, reviews)

    out: list[dict[str, Any]] = []
    for packet in packets:
        anchor = _clean(packet.get("anchor_trace_family"))
        eligible = [_clean(x) for x in (packet.get("eligible_trace_refs") or []) if _clean(x)]
        if not anchor or anchor not in eligible or any(ref not in by_id for ref in eligible):
            blocks.append(f"envelope_trace_reference_invalid:{anchor or 'UNKNOWN'}")
            continue
        score_by_ref = {anchor: 1.0}
        for row in packet.get("pair_eligibility_evidence") or []:
            if not isinstance(row, dict): continue
            ref = _clean(row.get("trace_ref")); score = row.get("eligibility_similarity")
            if ref and score is not None:
                try: score_by_ref[ref] = float(score)
                except (TypeError, ValueError): pass
        threshold_counts = []
        threshold_ref_sets = []
        for threshold in thresholds:
            refs = sorted(ref for ref, score in score_by_ref.items() if score >= threshold)
            threshold_counts.append({"similarity_threshold": threshold, "supported_recurrence": len(refs), "trace_refs": refs})
            threshold_ref_sets.append(set(refs))
        nominal = len(eligible)
        min_supported = min(row["supported_recurrence"] for row in threshold_counts)
        max_supported = max(row["supported_recurrence"] for row in threshold_counts)
        stable_core = sorted(set.intersection(*threshold_ref_sets)) if threshold_ref_sets else []
        fragile = sorted(set(eligible) - set(stable_core))

        order_confirmed = []
        order_uncertain = []
        contexts = set()
        for ref in eligible:
            variant = by_id[ref]
            if variant.get("chronology_confidence") == "EXPLICIT_POSITIVE_TIME_LAYER_ORDER": order_confirmed.append(ref)
            else: order_uncertain.append(ref)
            ctx = variant.get("context_signature") if isinstance(variant.get("context_signature"), dict) else {}
            contexts.add(tuple(sorted((str(k), str(v)) for k, v in ctx.items())))

        if nominal < 2:
            state = "INSUFFICIENT_EVIDENCE"
        elif min_supported < 2:
            state = "FRAGILE"
        elif min_supported < nominal:
            state = "THRESHOLD_SENSITIVE"
        elif len(order_confirmed) < nominal:
            state = "ORDER_SENSITIVE"
        elif len(contexts) > 1:
            state = "CONTEXT_SENSITIVE"
        else:
            state = "ROBUST_WITHIN_TESTED_RANGE"

        out.append({
            "pattern_family_ref": anchor,
            "nominal_recurrence": nominal,
            "similarity_threshold_range": [thresholds[0], thresholds[-1]],
            "threshold_sensitivity": threshold_counts,
            "window_sensitivity": "NOT_EVALUATED_NO_ALTERNATE_WINDOW_CONTRACT",
            "episode_boundary_sensitivity": "NOT_EVALUATED_NO_ALTERNATE_BOUNDARY_CONTRACT",
            "context_sensitivity": {"distinct_context_signature_count": len(contexts), "state": "VARIATION_VISIBLE" if len(contexts) > 1 else "NO_VARIATION_VISIBLE_CURRENT_SCOPE"},
            "player_removal_sensitivity": "NOT_EVALUATED_MISSING_ADMITTED_ACTOR_BINDING_IN_TRACE_VARIANT_CONTRACT",
            "segment_sensitivity": {"distinct_context_signature_count": len(contexts), "proxy_only": True},
            "reflection_sensitivity": "NOT_EVALUATED_DEPENDENCY_REF_DOES_NOT_PROVE_REMOVABLE_REFLECTION_DUPLICATE",
            "ordering_uncertainty_sensitivity": {"confirmed_order_trace_refs": sorted(order_confirmed), "order_uncertain_trace_refs": sorted(order_uncertain), "confirmed_order_recurrence": len(order_confirmed)},
            "min_supported_recurrence": min_supported,
            "max_supported_recurrence": max_supported,
            "stable_core_trace_refs": stable_core,
            "fragile_trace_refs": fragile,
            "robustness_state": state,
            "robustness_is_tactical_pattern_truth": False,
            "robustness_is_coach_intention_truth": False,
            "threshold_is_objective_football_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })
    if blocks: return _fail(blocks, reviews)
    return {
        "module_id": MODULE_ID, "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "recurrence_robustness_envelopes": out, "recurrence_robustness_envelope_count": len(out),
        "tested_similarity_thresholds": list(thresholds), "hard_block_hits": [], "review_hits": sorted(set(reviews)),
        "robustness_is_tactical_pattern_truth": False, "robustness_is_coach_intention_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT, "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False, "claim_ceiling": CLAIM_CEILING,
    }
