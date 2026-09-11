from __future__ import annotations

from typing import Any

MODULE_ID = "sequence_analyst_narrative_lite_v1"
UPSTREAM_MODULE_ID = "sequence_safe_finding_binding_lite_v1"
CONTEXT_DEVIATION_MODULE_ID = "context_conditioned_trace_deviation_lite_v1"
NULL_CLAIM_CEILING = "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _evidence_count(value: Any, field: str, *, missing_zero: bool = False) -> tuple[int, str | None]:
    if value is None and missing_zero:
        return 0, None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0, f"upstream_numeric_evidence_invalid:{field}"
    return value, None


def _validated_evidence_counts(row: dict[str, Any]) -> tuple[dict[str, int], list[str]]:
    recurrence = row.get("recurrence_summary") if isinstance(row.get("recurrence_summary"), dict) else {}
    specs = (
        ("observed_support", recurrence.get("observed_support"), False),
        ("success_support", row.get("success_support"), True),
        ("failure_support", row.get("failure_support"), True),
        ("divergence_support", row.get("divergence_support"), True),
        ("no_visible_followup_support", row.get("no_visible_followup_support"), True),
    )
    counts: dict[str, int] = {}
    hits: list[str] = []
    for field, value, missing_zero in specs:
        count, hit = _evidence_count(value, field, missing_zero=missing_zero)
        counts[field] = count
        if hit:
            hits.append(hit)
    return counts, hits


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
    rank = {"ROBUST_RECURRENT_VISIBLE_TRACE": 4, "RECURRENT_VISIBLE_TRACE": 3, "PROXY_CANDIDATE": 2, "DISCOVERY_ONLY": 1}.get(state, 0)
    counts = row.get("_validated_evidence_counts") or {}
    support = counts.get("observed_support", 0)
    challenge = counts.get("failure_support", 0) + counts.get("divergence_support", 0)
    return rank, support, -challenge


def _source_finding_gate(row: dict[str, Any]) -> tuple[str, str | None]:
    emitted = row.get("professional_finding_emitted")
    allowed = row.get("claim_output_allowed")
    status = _clean(row.get("finding_status")).upper()
    if not isinstance(emitted, bool) or not isinstance(allowed, bool):
        return "", "upstream_finding_emission_gate_missing"
    if emitted is not allowed:
        return "", "upstream_finding_emission_gate_mismatch"
    if status == "EMIT":
        if emitted is not True:
            return "", "upstream_emit_gate_mismatch"
        return status, None
    if status == "DOWNGRADE":
        if emitted is not False:
            return "", "upstream_downgrade_gate_mismatch"
        return status, None
    if status:
        return "", f"upstream_finding_status_unsupported:{status}"
    if emitted:
        return "", "upstream_emitted_finding_status_missing"
    return "LEGACY_DOWNGRADE", None


def _validate_context_deviation(payload: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if payload is None:
        return [], [], []
    hard: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != CONTEXT_DEVIATION_MODULE_ID: hard.append("context_deviation_module_id_mismatch")
    if payload.get("canonical_event_count") != "UNKNOWN": hard.append("context_deviation_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, "UNKNOWN"}: hard.append("context_deviation_true_action_count_claimed")
    if payload.get("production_release") is True: hard.append("context_deviation_production_release_claimed")
    if payload.get("hard_block_hits"): hard.append("context_deviation_hard_blocks_present")
    if payload.get("context_difference_is_causality_truth") is not False: hard.append("context_deviation_causality_lock_missing")
    if payload.get("context_difference_is_tactical_adaptation_truth") is not False: hard.append("context_deviation_adaptation_lock_missing")
    if payload.get("context_difference_is_coach_intention_truth") is not False: hard.append("context_deviation_intention_lock_missing")
    status = _clean(payload.get("status")).upper()
    if status == "FAIL_CLOSED": hard.append("context_deviation_input_fail_closed")
    elif status == "REVIEW_REQUIRED": reviews.append("context_deviation_upstream_review_required")
    elif status != "PASS": reviews.append(f"context_deviation_status_review:{status or 'UNKNOWN'}")
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
        if sorted(set(baseline_refs) | set(comparison_refs)) != trace_refs: continue
        dev_entity = _clean((dev.get("entity_scope") or {}).get("team_identity_candidate_id"))
        if entity_scope and dev_entity and entity_scope.lower() != dev_entity.lower(): continue
        if not baseline_refs or not comparison_refs: hard.append("context_deviation_empty_comparison_cohort"); continue
        if set(baseline_refs) & set(comparison_refs): hard.append("context_deviation_overlapping_cohorts"); continue
        if dev.get("context_difference_is_causality_truth") is not False: hard.append("context_deviation_row_causality_lock_missing"); continue
        if dev.get("context_difference_is_tactical_adaptation_truth") is not False: hard.append("context_deviation_row_adaptation_lock_missing"); continue
        if dev.get("context_difference_is_coach_intention_truth") is not False: hard.append("context_deviation_row_intention_lock_missing"); continue
        dimension = _clean(dev.get("context_dimension")); baseline_label = _clean(dev.get("baseline_cohort_ref")); comparison_label = _clean(dev.get("comparison_cohort_ref")); effect = _clean(dev.get("effect_descriptor"))
        if not dimension or not baseline_label or not comparison_label or not effect: hard.append("context_deviation_required_metadata_missing"); continue
        if effect == "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION":
            sentence = f"{dimension} için {baseline_label} ile {comparison_label} kohortlarında mevcut çözünürlükte görünür dağılım farkı saptanmadı; bu, sürecin değişmediğini veya iki bağlamın futbol açısından eşit olduğunu kanıtlamaz."
        else:
            sentence = f"{dimension} için {baseline_label} ile {comparison_label} kohortlarında aynı exact trace cohort farklı görünür sonuç/sequence dağılımı gösterdi. Bu fark yalnız bağlama bağlı görünür varyasyondur; neden, teknik direktör adaptasyonu veya taktik değişim kanıtı değildir."
        if dev.get("sample_warning"): reviews.append(f"context_variation_sample_review:{dimension}:{baseline_label}:{comparison_label}")
        variations.append({"context_conditioned_trace_deviation_id": dev.get("context_conditioned_trace_deviation_id"), "context_dimension": dimension, "baseline_cohort_ref": baseline_label, "comparison_cohort_ref": comparison_label, "baseline_trace_refs": baseline_refs, "comparison_trace_refs": comparison_refs, "effect_descriptor": effect, "outcome_difference": bool(dev.get("outcome_difference")), "sequence_difference": bool(dev.get("sequence_difference")), "support_difference": dev.get("support_difference"), "dependency_summary": dict(dev.get("dependency_summary") or {}), "uncertainty": dict(dev.get("uncertainty") or {}), "alternative_explanations": list(dev.get("alternative_explanations") or []), "sample_warning": dev.get("sample_warning"), "safe_change_tr": sentence, "chronology_direction_claimed": False, "causality_claimed": False, "tactical_adaptation_claimed": False, "coach_intention_claimed": False})
    return variations, hard, reviews


def _null_contrast_for_row(row: dict[str, Any]) -> tuple[dict[str, Any], str, list[str]]:
    raw = row.get("null_contrast_summary")
    if raw is None: return {}, "", []
    if not isinstance(raw, dict): return {}, "", ["upstream_null_contrast_summary_invalid"]
    summary = dict(raw)
    if summary.get("claim_strengthened") is not False: return {}, "", ["upstream_null_contrast_claim_strengthened"]
    state = _clean(summary.get("state")) or "NOT_EVALUATED"
    if state == "NOT_EVALUATED": return summary, "", []
    checks = (("claim_ceiling", NULL_CLAIM_CEILING, "upstream_null_contrast_claim_ceiling_mismatch"), ("multiple_testing_corrected", False, "upstream_null_contrast_multiple_testing_lock_breach"), ("significance_claim_allowed", False, "upstream_null_contrast_significance_lock_breach"), ("tactical_pattern_truth_allowed", False, "upstream_null_contrast_tactical_truth_lock_breach"), ("causality_allowed", False, "upstream_null_contrast_causality_lock_breach"))
    for key, expected, hit in checks:
        if summary.get(key) != expected: return {}, "", [hit]
    simulation_count = summary.get("simulation_count")
    if isinstance(simulation_count, bool) or not isinstance(simulation_count, int) or simulation_count < 1: return {}, "", ["upstream_null_contrast_simulation_count_invalid"]
    tail_resolution = summary.get("empirical_upper_tail_resolution")
    expected_resolution = 1 / (simulation_count + 1)
    if isinstance(tail_resolution, bool) or not isinstance(tail_resolution, (int, float)) or abs(float(tail_resolution) - expected_resolution) > 1e-12: return {}, "", ["upstream_null_contrast_tail_resolution_mismatch"]
    if summary.get("finite_simulation_resolution_only") is not True: return {}, "", ["upstream_null_contrast_finite_resolution_lock_breach"]
    if not _clean(summary.get("withdrawal_condition")): return {}, "", ["upstream_null_contrast_withdrawal_condition_missing"]
    sentence = f"Tanımlı null karşılaştırması {state}; gözlenen bağımsız tekrar={summary.get('observed_independent_recurrence')}, null medyan={summary.get('null_median')}, düzeltilmemiş üst-kuyruk olasılığı={summary.get('empirical_upper_tail_probability_uncorrected')}, simülasyon={simulation_count}, finite-simulation kuyruk çözünürlüğü={float(tail_resolution)}. Bu karşılaştırma istatistiksel anlamlılık, nedensellik veya taktik patern gerçeği değildir."
    return summary, sentence, []


def compose_sequence_analyst_narrative(binding_payload: dict[str, Any], context_deviation_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    hard: list[str] = []; reviews: list[str] = []
    if binding_payload.get("module_id") != UPSTREAM_MODULE_ID: hard.append("binding_module_id_mismatch")
    if binding_payload.get("canonical_event_count") != "UNKNOWN": hard.append("canonical_event_count_claimed")
    if binding_payload.get("true_action_count") != "UNKNOWN": hard.append("true_action_count_claimed")
    if binding_payload.get("production_release") is True: hard.append("production_release_claimed")
    if binding_payload.get("hard_block_hits"): hard.append("binding_hard_blocks_present")
    upstream_status = _clean(binding_payload.get("status")).upper()
    if upstream_status == "FAIL_CLOSED": hard.append("binding_input_fail_closed")
    elif upstream_status == "REVIEW_REQUIRED": reviews.append("binding_upstream_review_required")
    elif upstream_status != "PASS": reviews.append(f"binding_status_review:{upstream_status or 'UNKNOWN'}")
    deviations, deviation_hard, deviation_reviews = _validate_context_deviation(context_deviation_payload); hard.extend(deviation_hard); reviews.extend(deviation_reviews)
    if hard: return _fail(*hard)

    rows = [row for row in (binding_payload.get("analyst_report_blocks") or []) if isinstance(row, dict)]
    eligible: list[dict[str, Any]] = []
    for source_row in rows:
        row = dict(source_row)
        source_status, gate_error = _source_finding_gate(row)
        if gate_error: return _fail(gate_error)
        row["_source_finding_status"] = source_status
        if row.get("production_release") is not False: return _fail("upstream_production_release_lock_breach")
        if row.get("canonical_event_count") != "UNKNOWN" or row.get("true_action_count") != "UNKNOWN": return _fail("upstream_count_truth_lock_breach")
        if not _clean(row.get("SAFE_MEANING")): reviews.append("safe_meaning_missing"); continue
        counts, count_hard = _validated_evidence_counts(row)
        if count_hard: return _fail(*count_hard)
        row["_validated_evidence_counts"] = counts
        support = counts["observed_support"]
        trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)})
        family_refs = sorted({_clean(x) for x in (row.get("trace_family_refs") or []) if _clean(x)})
        upstream_claim_ceiling = _clean(row.get("claim_ceiling"))
        if not trace_refs: return _fail("upstream_trace_variant_refs_missing")
        if len(trace_refs) != support: return _fail("upstream_trace_cohort_support_mismatch")
        if family_refs and family_refs[0] not in trace_refs: return _fail("upstream_trace_family_anchor_not_in_cohort")
        if not isinstance(row.get("dependency_summary"), dict): return _fail("upstream_dependency_summary_missing")
        if not isinstance(row.get("robustness_summary"), dict): return _fail("upstream_robustness_summary_missing")
        if not isinstance(row.get("uncertainty"), dict): return _fail("upstream_uncertainty_missing")
        if not _clean(row.get("withdrawal_condition")): return _fail("upstream_withdrawal_condition_missing")
        if not upstream_claim_ceiling: return _fail("upstream_claim_ceiling_missing")
        _, _, null_hard = _null_contrast_for_row(row)
        if null_hard: return _fail(*null_hard)
        eligible.append(row)

    eligible.sort(key=_strength_rank, reverse=True)
    narratives: list[dict[str, Any]] = []
    for idx, row in enumerate(eligible):
        recurrence = row.get("recurrence_summary") or {}
        counts = row.get("_validated_evidence_counts") or {}
        support = counts["observed_support"]
        success = counts["success_support"]
        failure = counts["failure_support"]
        divergence = counts["divergence_support"]
        no_followup = counts["no_visible_followup_support"]
        counter_refs = sorted({_clean(x) for x in ((row.get("counterevidence") or {}).get("refs") or []) if _clean(x)})
        alternatives = [dict(x) for x in (row.get("alternative_explanations") or []) if isinstance(x, dict)]
        alternative_text = _clean(row.get("ALTERNATIVE_EXPLANATIONS"))
        context_scope = row.get("context_scope") or []; state = _clean(recurrence.get("admission_state")); trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)}); family_refs = sorted({_clean(x) for x in (row.get("trace_family_refs") or []) if _clean(x)}); upstream_claim_ceiling = _clean(row.get("claim_ceiling"))
        null_summary, null_text, null_hard = _null_contrast_for_row(row)
        if null_hard: return _fail(*null_hard)
        if failure or divergence or counter_refs:
            balance = "Aynı başlangıcın bozulduğu veya farklı sonuca gittiği örnekler de bulunduğu için bu tekrar koşulsuz çalışan bir üstünlük olarak okunmamalı."
        else:
            balance = "Mevcut görünür örneklerde açık bir karşı örnek bağlanmamış olması, bu yolun koşulsuz çalıştığını kanıtlamaz."
        if alternative_text:
            balance += f" Alternatif açıklamalar: {alternative_text}."
        elif alternatives:
            balance += " Bağlı alternatif açıklamalar da bu bulgunun tek açıklama veya nedensel sonuç olarak okunmasını engeller."
        opening = {"ROBUST_RECURRENT_VISIBLE_TRACE": "Aynı görünür süreç, test edilen kapsam içinde güçlü biçimde tekrarlandı.", "RECURRENT_VISIBLE_TRACE": "Aynı görünür süreç maç içinde birden fazla kez tekrarlandı.", "PROXY_CANDIDATE": "Benzer bir görünür süreç tekrar etti, ancak tekrarın gücü koşullara duyarlı görünüyor."}.get(state, "Benzer bir görünür süreç gözlendi; bunu yerleşik bir tekrar olarak adlandırmak için mevcut kanıt sınırlı.")
        evidence = f"Görünür destek {support} örnek; bunların hesaplanabilir bölümünde {success} benzer ilerleme, {failure} başarısız sonlanma ve {divergence} farklılaşan devam bulunuyor."
        if no_followup: evidence += f" {no_followup} örnekte görünür takip yok; bunlar başarısızlık sayılmadı."
        if null_text: evidence += " " + null_text
        context_variations, variation_hard, variation_reviews = _context_variations_for_row(row, deviations)
        if variation_hard: return _fail(*variation_hard)
        reviews.extend(variation_reviews); change_text = " ".join(item["safe_change_tr"] for item in context_variations); story = f"{opening} {evidence} {balance}"
        if change_text: story += " " + change_text
        narratives.append({"narrative_id": f"sequence_story_{idx + 1:03d}", "priority_rank": idx + 1, "source_report_block_id": row.get("analyst_report_block_id"), "source_finding_status": row.get("_source_finding_status"), "source_professional_finding_emitted": row.get("professional_finding_emitted"), "source_claim_output_allowed": row.get("claim_output_allowed"), "source_emission_is_input_eligibility_only": True, "entity_scope": row.get("entity_scope"), "context_scope": context_scope, "trace_family_refs": family_refs, "trace_variant_refs": trace_refs, "headline_tr": opening, "evidence_tr": evidence, "counterweight_tr": balance, "null_contrast_tr": null_text, "null_contrast_summary": null_summary, "change_tr": change_text, "context_variations": context_variations, "safe_meaning_tr": _clean(row.get("SAFE_MEANING")), "analyst_action_tr": "Başarılı, bozulan, farklılaşan ve bağlama göre ayrışan örnekleri aynı video/veri inceleme grubunda karşılaştır.", "story_tr": story, "support": support, "success_support": success, "failure_support": failure, "divergence_support": divergence, "no_visible_followup_support": no_followup, "counterevidence_refs": counter_refs, "counterevidence_ref_count": len(counter_refs), "alternative_explanations": alternatives, "alternative_explanation_count": len(alternatives), "alternative_explanations_tr": alternative_text, "challenge_surface_preserved": True, "admission_state": state, "dependency_summary": dict(row.get("dependency_summary") or {}), "robustness_summary": dict(row.get("robustness_summary") or {}), "forbidden_inference": row.get("FORBIDDEN_INFERENCE") or [], "uncertainty": dict(row.get("uncertainty") or {}), "withdrawal_condition": row.get("withdrawal_condition"), "upstream_claim_ceiling": upstream_claim_ceiling, "claim_ceiling": CLAIM_CEILING, "claim_output_allowed": False, "chronology_direction_claimed": False, "context_change_causality_claimed": False, "tactical_adaptation_claimed": False, "null_contrast_significance_claimed": False, "null_contrast_causality_claimed": False, "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False})

    return {"module_id": MODULE_ID, "status": "REVIEW_REQUIRED" if reviews else "PASS", "decision": "MATCH_LOCAL_SEQUENCE_NARRATIVE_COMPOSED", "narrative_blocks": narratives, "narrative_block_count": len(narratives), "review_hits": sorted(set(reviews)), "hard_block_hits": [], "story_order_basis": "EVIDENCE_STRENGTH_THEN_SUPPORT_NOT_FOOTBALL_CHRONOLOGY", "chronological_story_claimed": False, "context_variation_descriptive_only": True, "context_change_causality_claimed": False, "null_contrast_descriptive_only": True, "statistical_significance_claimed": False, "coach_intention_claimed": False, "causality_claimed": False, "tactical_plan_truth_claimed": False, "lineage_preservation_required": True, "source_emission_is_input_eligibility_only": True, "challenge_surface_preservation_required": True, "numeric_evidence_counts_are_strict_nonnegative_integers": True, "boolean_numeric_evidence_rejected": True, "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "claim_ceiling": CLAIM_CEILING}
