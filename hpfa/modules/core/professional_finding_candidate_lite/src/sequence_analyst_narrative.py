from __future__ import annotations

from typing import Any

MODULE_ID = "sequence_analyst_narrative_lite_v1"
UPSTREAM_MODULE_ID = "sequence_safe_finding_binding_lite_v1"
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


def compose_sequence_analyst_narrative(binding_payload: dict[str, Any]) -> dict[str, Any]:
    """Compose readable match-local story blocks from already admitted safe findings.

    This layer ranks and connects findings; it does not discover new football facts.
    Exact upstream evidence lineage is preserved so readable prose stays auditable.
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
            "safe_meaning_tr": _clean(row.get("SAFE_MEANING")),
            "analyst_action_tr": "Başarılı, bozulan ve farklılaşan örnekleri aynı video/veri inceleme grubunda karşılaştır.",
            "story_tr": f"{opening} {evidence} {balance}",
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
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "tactical_plan_truth_claimed": False,
        "lineage_preservation_required": True,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
