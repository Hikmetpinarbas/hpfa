from __future__ import annotations

from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROCESS_VARIANT_DIFFERENCE_BINDING_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _family_key(signature: Any) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    if not isinstance(signature, dict):
        return None
    anchor = tuple(sorted(_clean(v) for v in (signature.get("anchor_action_families") or []) if _clean(v)))
    response = tuple(sorted(_clean(v) for v in (signature.get("response_action_families") or []) if _clean(v)))
    if not anchor and not response:
        return None
    return anchor, response


def _difference_sentence_tr(row: dict[str, Any]) -> str:
    modal = _clean(row.get("modal_resolution_class_candidate")) or "UNKNOWN"
    deviant = _clean(row.get("deviant_resolution_class_candidate")) or "UNKNOWN"
    differences = [
        item for item in (row.get("visible_difference_candidates") or [])
        if isinstance(item, dict) and _clean(item.get("observation_dimension"))
    ]
    dimensions = ", ".join(_clean(item.get("observation_dimension")) for item in differences[:4])
    if dimensions:
        return (
            f"Aynı görünür process ailesinde maç içi modal çözülme {modal}, ayrışan çözülme {deviant}. "
            f"Gözlenen fark boyutları: {dimensions}. Bu farklar birlikte görülmüştür; nedensellik kanıtı değildir."
        )
    return (
        f"Aynı görünür process ailesinde maç içi modal çözülme {modal}, ayrışan çözülme {deviant}; "
        "mevcut admitted gözlemler ayrışmayı açıklayacak ek fark boyutu göstermedi."
    )


def attach_process_variant_difference_explanations(
    finding_payload: dict[str, Any],
    difference_payload: dict[str, Any],
) -> dict[str, Any]:
    """Attach match-local modal/deviant visible differences to existing findings.

    This enriches analyst meaning only. It does not create a new finding, independent
    evidence, causal explanation, tactical adaptation truth, or release permission.
    """
    result = dict(finding_payload)
    rows = [dict(row) for row in (finding_payload.get("professional_finding_candidates") or []) if isinstance(row, dict)]
    result["professional_finding_candidates"] = rows

    blocks: list[str] = []
    reviews: list[str] = []
    if finding_payload.get("module_id") != FINDING_MODULE_ID:
        blocks.append("finding_module_id_mismatch")
    if finding_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("finding_canonical_event_count_claimed")
    if finding_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("finding_true_action_count_claimed")
    if finding_payload.get("production_release") is True:
        blocks.append("finding_production_release_claimed")
    if _clean(finding_payload.get("status")).upper() == "FAIL_CLOSED" or finding_payload.get("hard_block_hits"):
        blocks.append("finding_input_fail_closed")

    if difference_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("difference_canonical_event_count_claimed")
    if difference_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("difference_true_action_count_claimed")
    if difference_payload.get("production_release") is True:
        blocks.append("difference_production_release_claimed")
    if difference_payload.get("right_censoring_used_as_counterevidence") is not False:
        blocks.append("difference_censoring_counterevidence_lock_breach")
    if difference_payload.get("difference_is_causal_explanation") is not False:
        blocks.append("difference_causality_lock_breach")
    difference_status = _clean(difference_payload.get("status")).upper()
    if difference_status == "FAIL_CLOSED":
        blocks.append("difference_input_fail_closed")
    elif difference_status not in {"PASS", "NO_ELIGIBLE_COMPARISON"}:
        reviews.append(f"difference_status_review:{difference_status or 'UNKNOWN'}")

    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["process_variant_difference_binding_status"] = "FAIL_CLOSED"
        result["hard_block_hits"] = sorted(set((finding_payload.get("hard_block_hits") or []) + blocks))
        result["claim_output_allowed_count"] = 0
        result["professional_finding_emitted_count"] = 0
        result["canonical_event_count"] = CANONICAL_EVENT_COUNT
        result["true_action_count"] = TRUE_ACTION_COUNT
        result["production_release"] = False
        return result

    by_family: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict[str, Any]]] = {}
    for explanation in difference_payload.get("process_variant_difference_explanations") or []:
        if not isinstance(explanation, dict):
            continue
        key = _family_key(explanation.get("process_family_signature_candidate"))
        if key is None:
            continue
        by_family.setdefault(key, []).append(explanation)

    attached = 0
    for finding in rows:
        signature = finding.get("process_family_signature_candidate") or finding.get("process_family_signature")
        key = _family_key(signature)
        explanations = [dict(item) for item in by_family.get(key, [])] if key is not None else []
        finding["visible_process_variant_difference_explanations"] = explanations
        finding["visible_process_variant_difference_explanation_count"] = len(explanations)
        finding["process_variant_difference_analyst_summary_tr"] = [
            _difference_sentence_tr(item) for item in explanations
        ]
        finding["process_variant_difference_is_causal_explanation"] = False
        finding["process_variant_difference_is_tactical_adaptation_truth"] = False
        finding["process_variant_difference_is_coach_intention_truth"] = False
        finding["process_variant_difference_creates_independent_evidence"] = False
        finding["right_censoring_used_as_process_counterevidence"] = False
        if explanations:
            attached += 1
            uncertainty = dict(finding.get("uncertainty") or {})
            uncertainty["variant_difference_explanation_scope"] = "MATCH_LOCAL_VISIBLE_DIFFERENCE_ONLY"
            uncertainty["unobserved_video_tracking_context_may_explain_difference"] = True
            finding["uncertainty"] = uncertainty
            action = _clean(finding.get("ANALYST_ACTION") or finding.get("analyst_action"))
            suffix = "Modal ve ayrışan process örneklerini görünür fark boyutları üzerinden birlikte incele."
            finding["ANALYST_ACTION"] = f"{action} {suffix}".strip()

    result["process_variant_difference_binding_status"] = "REVIEW_REQUIRED" if reviews else "PASS"
    result["process_variant_difference_explanation_attached_finding_count"] = attached
    result["process_variant_difference_explanation_available_count"] = sum(
        len(v) for v in by_family.values()
    )
    result["process_variant_difference_binding_review_hits"] = sorted(set(reviews))
    result["process_variant_difference_creates_independent_evidence"] = False
    result["right_censoring_used_as_process_counterevidence"] = False
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
