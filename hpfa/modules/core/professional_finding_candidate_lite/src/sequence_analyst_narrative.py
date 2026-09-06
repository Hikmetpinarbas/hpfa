from __future__ import annotations

from typing import Any

MODULE_ID = "sequence_analyst_narrative_lite_v1"
UPSTREAM_MODULE_ID = "sequence_safe_finding_binding_lite_v1"
CONTEXT_DEVIATION_MODULE_ID = "context_conditioned_trace_deviation_lite_v1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "SEQUENCE_ANALYST_NARRATIVE_REJECTED",
        "narrative_blocks": [],
        "narrative_block_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _strength_rank(row: dict[str, Any]) -> tuple[int, int, int]:
    state = _clean((row.get("recurrence_summary") or {}).get("admission_state"))
    rank = {
        "ROBUST_RECURRENT_VISIBLE_TRACE": 4,
        "RECURRENT_VISIBLE_TRACE": 3,
        "PROXY_CANDIDATE": 2,
        "DISCOVERY_ONLY": 1,
    }.get(state, 0)
    support = int((row.get("recurrence_summary") or {}).get("observed_support") or 0)
    challenge = int(row.get("failure_support") or 0) + int(row.get("divergence_support") or 0)
    return rank, support, -challenge


def _validate_context_deviation(payload: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if payload is None:
        return [], [], []
    hard: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != CONTEXT_DEVIATION_MODULE_ID:
        hard.append("context_deviation_module_id_mismatch")
    if payload.get("canonical_event_count") != "UNKNOWN":
        hard.append("context_deviation_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, "UNKNOWN"}:
        hard.append("context_deviation_true_action_count_claimed")
    if payload.get("production_release") is True:
        hard.append("context_deviation_production_release_claimed")
    if payload.get("hard_block_hits"):
        hard.append("context_deviation_hard_blocks_present")
    if payload.get("context_difference_is_causality_truth") is not False:
        hard.append("context_deviation_causality_lock_missing")
    if payload.get("context_difference_is_tactical_adaptation_truth") is not False:
        hard.append("context_deviation_adaptation_lock_missing")
    if payload.get("context_difference_is_coach_intention_truth") is not False:
        hard.append("context_deviation_intention_lock_missing")
    status = _clean(payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        hard.append("context_deviation_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("context_deviation_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"context_deviation_status_review:{status or 'UNKNOWN'}")
    rows = [row for row in (payload.get("context_conditioned_trace_deviations") or []) if isinstance(row, dict)]
    return rows, hard, reviews


def _context_variations_for_row(row: dict[str, Any], deviations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)})
    entity_scope = _clean(row.get("entity_scope"))
    variations: list[dict[str, Any]] = []
    hard: list[str] = []
    reviews: list[str] = []

    for dev in deviations:
        baseline_refs = sorted({_clean(x) for x in (dev.get("baseline_trace_refs") or []) if _clean(x)})
        comparison_refs = sorted({_clean(x) for x in (dev.get("comparison_trace_refs") or []) if _clean(x)})
        cohort_refs = sorted(set(baseline_refs) | set(comparison_refs))
        if cohort_refs != trace_refs:
            continue
        dev_entity = _clean((dev.get("entity_scope") or {}).get("team_identity_candidate_id"))
        if entity_scope and dev_entity and entity_scope.lower() != dev_entity.lower():
            continue
        if not baseline_refs or not comparison_refs:
            hard.append("context_deviation_empty_comparison_cohort")
            continue
        if set(baseline_refs) & set(comparison_refs):
            hard.append("context_deviation_overlapping_cohorts")
            continue
        if dev.get("context_difference_is_causality_truth") is not False:
            hard.append("context_deviation_row_causality_lock_missing")
            continue
        if dev.get("context_difference_is_tactical_adaptation_truth") is not False:
            hard.append("context_deviation_row_adaptation_lock_missing")
            continue
        if dev.get("context_difference_is_coach_intention_truth") is not False:
            hard.append("context_deviation_row_intention_lock_missing")
            continue
        dimension = _clean(dev.get("context_dimension"))
        baseline_label = _clean(dev.get("baseline_cohort_ref"))
        comparison_label = _clean(dev.get("comparison_cohort_ref"))
        effect = _clean(dev.get("effect_descriptor"))
        if not dimension or not baseline_label or not comparison_label or not effect:
            hard.append("context_deviation_required_metadata_missing")
            continue

        if effect == "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION":
            sentence = (
                f"{dimension} için {baseline_label} ile {comparison_label} kohortlarında mevcut çözünürlükte görünür dağılım farkı saptanmadı; "
                "bu, sürecin değişmediğini veya iki bağlamın futbol açısından eşit olduğunu kanıtlamaz."
            )
        else:
            sentence = (
                f"{dimension} için {baseline_label} ile {comparison_label} kohortlarında aynı exact trace cohort farklı görünür sonuç/sequence dağılımı gösterdi. "
                "Bu fark yalnız bağlama bağlı görünür varyasyondur; neden, teknik direktör adaptasyonu veya taktik değişim kanıtı değildir."
            )
        if dev.get("sample_warning"):
            reviews.append(f"context_variation_sample_review:{dimension}:{baseline_label}:{comparison_label}")

        variations.append({
            "context_conditioned_trace_deviation_id": dev.get("context_conditioned_trace_deviation_id"),
            "context_dimension": dimension,
            "baseline_cohort_ref": baseline_label,
            "comparison_cohort_ref": comparison_label,
            "baseline_trace_refs": baseline_refs,
            "comparison_trace_refs": comparison_refs,
            "effect_descriptor": effect,
            "outcome_difference": bool(dev.get("outcome_difference")),
            "sequence_difference": bool(dev.get("sequence_difference")),
            "support_difference": dev.get("support_difference"),
            "dependency_summary": dict(dev.get("dependency_summary") or {}),
            "uncertainty": dict(dev.get("uncertainty") or {}),
            "alternative_explanations": list(dev.get("alternative_explanations") or []),
            "sample_warning": dev.get("sample_warning"),
            "safe_change_tr": sentence,
            "chronology_direction_claimed": False,
            "causality_claimed": False,
            "tactical_adaptation_claimed": False,
            "coach_intention_claimed": False,
        })
    return variations, hard, reviews


def _null_contrast_for_row(row: dict[str, Any]) -> tuple[dict[str, Any], str, list[str]]:
    raw = row.get("null_contrast_summary")
    if raw is None:
        return {}, "", []
    if not isinstance(raw, dict):
        return {}, "", ["upstream_null_contrast_summary_invalid"]
    summary = dict(raw)
    if summary.get("claim_strengthened") is not False:
        return {}, "", ["upstream_null_contrast_claim_strengthened"]
    state = _clean(summary.get("state")) or "NOT_EVALUATED"
    if state == "NOT_EVALUATED":
        return summary, "", []
    if summary.get("significance_claim_allowed") is not False:
        return {}, "", ["upstream_null_contrast_significance_lock_breach"]
    if summary.get("tactical_pattern_truth_allowed") is not False:
        return {}, "", ["upstream_null_contrast_tactical_truth_lock_breach"]
    sentence = (
        f"Tanımlı null karşılaştırması {state}; gözlenen bağımsız tekrar={summary.get('observed_independent_recurrence')}, "
        f"null medyan={summary.get('null_median')}, düzeltilmemiş üst-kuyruk olasılığı={summary.get('empirical_upper_tail_probability_uncorrected')}. "
        "Bu karşılaştırma istatistiksel anlamlılık, nedensellik veya taktik patern gerçeği değildir."
    )
    return summary, sentence, []


def compose_sequence_analyst_narrative(
    binding_payload: dict[str, Any],
    context_deviation_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose readable match-local story blocks from already admitted safe findings.

    Optional audited null contrast and context-conditioned deviation evidence remain
    descriptive and bind only to the already-admitted finding. No chronology,
    causality, tactical adaptation, significance or coach-intention truth is created.
    """
    hard: list[str] = []
    reviews: list[str] = []
    if binding_payload.get("module_id") != UPSTREAM_MODULE_ID:
        hard.append("binding_module_id_mismatch")
    if binding_payload.get("canonical_event_count") != "UNKNOWN":
        hard.append("canonical_event_count_claimed")
    if binding_payload.get("true_action_count") != "UNKNOWN":
        hard.append("true_action_count_claimed")
    if binding_payload.get("production_release") is True:
        hard.append("production_release_claimed")
    if binding_payload.get("hard_block_hits"):
        hard.append("binding_hard_blocks_present")
    upstream_status = _clean(binding_payload.get("status")).upper()
    if upstream_status == "FAIL_CLOSED":
        hard.append("binding_input_fail_closed")
    elif upstream_status == "REVIEW_REQUIRED":
        reviews.append("binding_upstream_review_required")
    elif upstream_status != "PASS":
        reviews.append(f"binding_status_review:{upstream_status or 'UNKNOWN'}")

    deviations, deviation_hard, deviation_reviews = _validate_context_deviation(context_deviation_payload)
    hard.extend(deviation_hard)
    reviews.extend(deviation_reviews)
    if hard:
        return _fail(*hard)

    rows = [row for row in (binding_payload.get("analyst_report_blocks") or []) if isinstance(row, dict)]
    eligible: list[dict[str, Any]] = []
    for row in rows:
        if row.get("professional_finding_emitted") is not False or row.get("claim_output_allowed") is not False:
            return _fail("upstream_claim_output_lock_breach")
        if row.get("production_release") is not False:
            return _fail("upstream_production_release_lock_breach")
        if row.get("canonical_event_count") != "UNKNOWN" or row.get("true_action_count") != "UNKNOWN":
            return _fail("upstream_count_truth_lock_breach")
        if not _clean(row.get("SAFE_MEANING")):
            reviews.append("safe_meaning_missing")
            continue

        recurrence = row.get("recurrence_summary") if isinstance(row.get("recurrence_summary"), dict) else {}
        support = int(recurrence.get("observed_support") or 0)
        trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)})
        family_refs = sorted({_clean(x) for x in (row.get("trace_family_refs") or []) if _clean(x)})
        upstream_claim_ceiling = _clean(row.get("claim_ceiling"))
        if not trace_refs:
            return _fail("upstream_trace_variant_refs_missing")
        if len(trace_refs) != support:
            return _fail("upstream_trace_cohort_support_mismatch")
        if family_refs and family_refs[0] not in trace_refs:
            return _fail("upstream_trace_family_anchor_not_in_cohort")
        if not isinstance(row.get("dependency_summary"), dict):
            return _fail("upstream_dependency_summary_missing")
        if not isinstance(row.get("robustness_summary"), dict):
            return _fail("upstream_robustness_summary_missing")
        if not isinstance(row.get("uncertainty"), dict):
            return _fail("upstream_uncertainty_missing")
        if not _clean(row.get("withdrawal_condition")):
            return _fail("upstream_withdrawal_condition_missing")
        if not upstream_claim_ceiling:
            return _fail("upstream_claim_ceiling_missing")
        _, _, null_hard = _null_contrast_for_row(row)
        if null_hard:
            return _fail(*null_hard)
        eligible.append(row)

    eligible.sort(key=_strength_rank, reverse=True)
    narratives: list[dict[str, Any]] = []
    for idx, row in enumerate(eligible):
        recurrence = row.get("recurrence_summary") or {}
        support = int(recurrence.get("observed_support") or 0)
        success = int(row.get("success_support") or 0)
        failure = int(row.get("failure_support") or 0)
        divergence = int(row.get("divergence_support") or 0)
        no_followup = int(row.get("no_visible_followup_support") or 0)
        counter_refs = sorted({_clean(x) for x in ((row.get("counterevidence") or {}).get("refs") or []) if _clean(x)})
        context_scope = row.get("context_scope") or []
        state = _clean(recurrence.get("admission_state"))
        trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)})
        family_refs = sorted({_clean(x) for x in (row.get("trace_family_refs") or []) if _clean(x)})
        upstream_claim_ceiling = _clean(row.get("claim_ceiling"))
        null_summary, null_text, null_hard = _null_contrast_for_row(row)
        if null_hard:
            return _fail(*null_hard)

        if failure or divergence or counter_refs:
            balance = "Aynı başlangıcın bozulduğu veya farklı sonuca gittiği örnekler de bulunduğu için bu tekrar koşulsuz çalışan bir üstünlük olarak okunmamalı."
        else:
            balance = "Mevcut görünür örneklerde açık bir karşı örnek bağlanmamış olması, bu yolun koşulsuz çalıştığını kanıtlamaz."

        if state == "ROBUST_RECURRENT_VISIBLE_TRACE":
            opening = "Aynı görünür süreç, test edilen kapsam içinde güçlü biçimde tekrarlandı."
        elif state == "RECURRENT_VISIBLE_TRACE":
            opening = "Aynı görünür süreç maç içinde birden fazla kez tekrarlandı."
        elif state == "PROXY_CANDIDATE":
            opening = "Benzer bir görünür süreç tekrar etti, ancak tekrarın gücü koşullara duyarlı görünüyor."
        else:
            opening = "Benzer bir görünür süreç gözlendi; bunu yerleşik bir tekrar olarak adlandırmak için mevcut kanıt sınırlı."

        evidence = (
            f"Görünür destek {support} örnek; bunların hesaplanabilir bölümünde {success} benzer ilerleme, "
            f"{failure} başarısız sonlanma ve {divergence} farklılaşan devam bulunuyor."
        )
        if no_followup:
            evidence += f" {no_followup} örnekte görünür takip yok; bunlar başarısızlık sayılmadı."
        if null_text:
            evidence += " " + null_text

        context_variations, variation_hard, variation_reviews = _context_variations_for_row(row, deviations)
        if variation_hard:
            return _fail(*variation_hard)
        reviews.extend(variation_reviews)
        change_text = " ".join(item["safe_change_tr"] for item in context_variations)
        story = f"{opening} {evidence} {balance}"
        if change_text:
            story += " " + change_text

        narratives.append({
            "narrative_id": f"sequence_story_{idx + 1:03d}",
            "priority_rank": idx + 1,
            "source_report_block_id": row.get("analyst_report_block_id"),
            "entity_scope": row.get("entity_scope"),
            "context_scope": context_scope,
            "trace_family_refs": family_refs,
            "trace_variant_refs": trace_refs,
            "headline_tr": opening,
            "evidence_tr": evidence,
            "counterweight_tr": balance,
            "null_contrast_tr": null_text,
            "null_contrast_summary": null_summary,
            "change_tr": change_text,
            "context_variations": context_variations,
            "safe_meaning_tr": _clean(row.get("SAFE_MEANING")),
            "analyst_action_tr": "Başarılı, bozulan, farklılaşan ve bağlama göre ayrışan örnekleri aynı video/veri inceleme grubunda karşılaştır.",
            "story_tr": story,
            "support": support,
            "success_support": success,
            "failure_support": failure,
            "divergence_support": divergence,
            "no_visible_followup_support": no_followup,
            "counterevidence_refs": counter_refs,
            "counterevidence_ref_count": len(counter_refs),
            "admission_state": state,
            "dependency_summary": dict(row.get("dependency_summary") or {}),
            "robustness_summary": dict(row.get("robustness_summary") or {}),
            "forbidden_inference": row.get("FORBIDDEN_INFERENCE") or [],
            "uncertainty": dict(row.get("uncertainty") or {}),
            "withdrawal_condition": row.get("withdrawal_condition"),
            "upstream_claim_ceiling": upstream_claim_ceiling,
            "claim_ceiling": CLAIM_CEILING,
            "claim_output_allowed": False,
            "chronology_direction_claimed": False,
            "context_change_causality_claimed": False,
            "tactical_adaptation_claimed": False,
            "null_contrast_significance_claimed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "MATCH_LOCAL_SEQUENCE_NARRATIVE_COMPOSED",
        "narrative_blocks": narratives,
        "narrative_block_count": len(narratives),
        "review_hits": sorted(set(reviews)),
        "hard_block_hits": [],
        "story_order_basis": "EVIDENCE_STRENGTH_THEN_SUPPORT_NOT_FOOTBALL_CHRONOLOGY",
        "chronological_story_claimed": False,
        "context_variation_descriptive_only": True,
        "context_change_causality_claimed": False,
        "null_contrast_descriptive_only": True,
        "statistical_significance_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "tactical_plan_truth_claimed": False,
        "lineage_preservation_required": True,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
