from __future__ import annotations

from collections import Counter
from typing import Any

MODULE_ID = "match_story_synthesis_lite_v1"
UPSTREAM_MODULE_ID = "sequence_analyst_narrative_lite_v1"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "MATCH_STORY_SYNTHESIS_REJECTED",
        "entity_stories": [],
        "entity_story_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "review_hits": [],
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _story_state(*, recurrent: int, robust: int, context_sensitive: int, challenged: int) -> str:
    if context_sensitive and recurrent:
        return "RECURRENT_PROCESS_SET_WITH_CONTEXT_VARIATION"
    if robust and challenged:
        return "ROBUST_PROCESS_SET_WITH_VISIBLE_COUNTEREVIDENCE"
    if recurrent and challenged:
        return "RECURRENT_PROCESS_SET_WITH_VISIBLE_COUNTEREVIDENCE"
    if recurrent:
        return "RECURRENT_PROCESS_SET_VISIBLE"
    return "DISCOVERY_LEVEL_PROCESS_SET"


def synthesize_match_story(narrative_payload: dict[str, Any]) -> dict[str, Any]:
    """Synthesize existing safe narrative blocks into entity-level match-local process stories.

    This is a synthesis layer, not a discovery or chronology engine. It combines already
    admitted narrative evidence, exposes balance/change/counterevidence, and explicitly
    keeps nominal support separate from independent evidence.
    """
    hard: list[str] = []
    reviews: list[str] = []

    if narrative_payload.get("module_id") != UPSTREAM_MODULE_ID:
        hard.append("narrative_module_id_mismatch")
    if narrative_payload.get("canonical_event_count") != "UNKNOWN":
        hard.append("canonical_event_count_claimed")
    if narrative_payload.get("true_action_count") != "UNKNOWN":
        hard.append("true_action_count_claimed")
    if narrative_payload.get("production_release") is True:
        hard.append("production_release_claimed")
    if narrative_payload.get("hard_block_hits"):
        hard.append("narrative_hard_blocks_present")
    if narrative_payload.get("chronological_story_claimed") is not False:
        hard.append("upstream_chronology_lock_missing")
    if narrative_payload.get("coach_intention_claimed") is not False:
        hard.append("upstream_coach_intention_lock_missing")
    if narrative_payload.get("causality_claimed") is not False:
        hard.append("upstream_causality_lock_missing")
    if narrative_payload.get("tactical_plan_truth_claimed") is not False:
        hard.append("upstream_tactical_plan_lock_missing")

    status = _clean(narrative_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        hard.append("narrative_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("narrative_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"narrative_status_review:{status or 'UNKNOWN'}")
    if hard:
        return _fail(*hard)

    rows = [row for row in (narrative_payload.get("narrative_blocks") or []) if isinstance(row, dict)]
    declared = narrative_payload.get("narrative_block_count")
    if not _is_nonnegative_int(declared) or declared != len(rows):
        return _fail("narrative_block_count_mismatch")

    seen_ids: set[str] = set()
    by_entity: dict[str, list[dict[str, Any]]] = {}
    all_trace_owners: dict[str, set[str]] = {}

    for row in rows:
        narrative_id = _clean(row.get("narrative_id"))
        if not narrative_id:
            return _fail("narrative_id_missing")
        if narrative_id in seen_ids:
            return _fail(f"duplicate_narrative_id:{narrative_id}")
        seen_ids.add(narrative_id)

        if row.get("claim_output_allowed") is not False:
            return _fail(f"narrative_claim_output_lock_breach:{narrative_id}")
        if row.get("production_release") is not False:
            return _fail(f"narrative_production_release_lock_breach:{narrative_id}")
        if row.get("canonical_event_count") != "UNKNOWN" or row.get("true_action_count") != "UNKNOWN":
            return _fail(f"narrative_count_truth_lock_breach:{narrative_id}")
        if row.get("chronology_direction_claimed") is not False:
            return _fail(f"narrative_row_chronology_lock_breach:{narrative_id}")
        if row.get("context_change_causality_claimed") is not False:
            return _fail(f"narrative_row_context_causality_lock_breach:{narrative_id}")
        if row.get("tactical_adaptation_claimed") is not False:
            return _fail(f"narrative_row_adaptation_lock_breach:{narrative_id}")
        if row.get("null_contrast_significance_claimed") is not False:
            return _fail(f"narrative_row_significance_lock_breach:{narrative_id}")

        entity = _clean(row.get("entity_scope")) or "MATCH_LOCAL_ENTITY_SCOPE_CANDIDATE"
        trace_refs = sorted({_clean(x) for x in (row.get("trace_variant_refs") or []) if _clean(x)})
        if not trace_refs:
            return _fail(f"narrative_trace_refs_missing:{narrative_id}")
        support = row.get("support")
        if not _is_nonnegative_int(support) or support != len(trace_refs):
            return _fail(f"narrative_support_trace_mismatch:{narrative_id}")

        priority_rank = row.get("priority_rank")
        if not _is_nonnegative_int(priority_rank):
            return _fail(f"narrative_priority_rank_invalid:{narrative_id}")

        outcome_keys = (
            "success_support",
            "failure_support",
            "divergence_support",
            "no_visible_followup_support",
        )
        outcome_values: list[int] = []
        for key in outcome_keys:
            value = row.get(key)
            if not _is_nonnegative_int(value):
                return _fail(f"narrative_{key}_invalid:{narrative_id}")
            if value > support:
                return _fail(f"narrative_{key}_exceeds_support:{narrative_id}")
            outcome_values.append(value)
        if sum(outcome_values) > support:
            return _fail(f"narrative_outcome_support_exceeds_trace_support:{narrative_id}")

        counter_count = row.get("counterevidence_ref_count")
        if not _is_nonnegative_int(counter_count) or counter_count > support:
            return _fail(f"narrative_counterevidence_ref_count_invalid:{narrative_id}")

        for ref in trace_refs:
            all_trace_owners.setdefault(ref, set()).add(narrative_id)
        by_entity.setdefault(entity, []).append(row)

    shared_trace_refs = sorted(ref for ref, owners in all_trace_owners.items() if len(owners) > 1)
    if shared_trace_refs:
        reviews.append("trace_refs_shared_across_narrative_blocks_independence_not_proven")

    entity_stories: list[dict[str, Any]] = []
    for entity, entity_rows in sorted(by_entity.items()):
        entity_rows = sorted(entity_rows, key=lambda r: r["priority_rank"])
        state_counts = Counter(_clean(row.get("admission_state")) or "UNKNOWN" for row in entity_rows)
        robust = state_counts.get("ROBUST_RECURRENT_VISIBLE_TRACE", 0)
        recurrent = robust + state_counts.get("RECURRENT_VISIBLE_TRACE", 0)
        proxy = state_counts.get("PROXY_CANDIDATE", 0)
        discovery = state_counts.get("DISCOVERY_ONLY", 0)

        challenged_rows = [
            row for row in entity_rows
            if row["failure_support"] > 0
            or row["divergence_support"] > 0
            or row["counterevidence_ref_count"] > 0
        ]
        context_sensitive_rows = []
        no_visible_context_difference_rows = []
        null_evaluated_rows = []
        null_above_median_rows = []

        for row in entity_rows:
            variations = [x for x in (row.get("context_variations") or []) if isinstance(x, dict)]
            effects = {_clean(x.get("effect_descriptor")) for x in variations}
            if any(effect and effect != "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION" for effect in effects):
                context_sensitive_rows.append(row)
            elif "NO_VISIBLE_DISTRIBUTION_DIFFERENCE_CURRENT_RESOLUTION" in effects:
                no_visible_context_difference_rows.append(row)

            null_summary = row.get("null_contrast_summary") if isinstance(row.get("null_contrast_summary"), dict) else {}
            null_state = _clean(null_summary.get("state"))
            if null_state and null_state != "NOT_EVALUATED":
                null_evaluated_rows.append(row)
                if "ABOVE" in null_state and "MEDIAN" in null_state:
                    null_above_median_rows.append(row)

        nominal_support = sum(row["support"] for row in entity_rows)
        unique_trace_refs = sorted({
            ref
            for row in entity_rows
            for ref in (_clean(x) for x in (row.get("trace_variant_refs") or []))
            if ref
        })
        success = sum(row["success_support"] for row in entity_rows)
        failure = sum(row["failure_support"] for row in entity_rows)
        divergence = sum(row["divergence_support"] for row in entity_rows)
        no_followup = sum(row["no_visible_followup_support"] for row in entity_rows)

        state = _story_state(
            recurrent=recurrent,
            robust=robust,
            context_sensitive=len(context_sensitive_rows),
            challenged=len(challenged_rows),
        )

        headline = entity_rows[0]
        headline_text = _clean(headline.get("headline_tr")) or "Görünür süreç adayları bulundu."
        balance_parts = [
            f"{len(entity_rows)} süreç anlatısı",
            f"{recurrent} tekrar eden",
            f"{robust} robust tekrar",
            f"{len(challenged_rows)} karşı örnek/bozulma taşıyan",
            f"{len(context_sensitive_rows)} bağlama göre ayrışan",
        ]
        if null_evaluated_rows:
            balance_parts.append(f"{len(null_evaluated_rows)} null karşılaştırmalı")
        if null_above_median_rows:
            balance_parts.append(f"{len(null_above_median_rows)} null medyanının üzerinde tekrar gösteren")

        story_tr = (
            f"{headline_text} Bu entity için " + ", ".join(balance_parts) + ". "
            f"Toplam görünür süreç desteği nominal olarak {nominal_support}; benzersiz trace referansı {len(unique_trace_refs)}. "
            f"Sonuç dengesinde {success} benzer ilerleme, {failure} başarısız sonlanma, {divergence} farklılaşan devam ve {no_followup} görünür takip olmayan örnek bulunuyor. "
        )
        if context_sensitive_rows:
            story_tr += (
                "Aynı süreç ailelerinin bazıları admitted bağlamlar arasında farklı görünür dağılım gösteriyor; "
                "bu yalnız bağlamsal varyasyon kanıtıdır, neden veya taktik adaptasyon kanıtı değildir. "
            )
        if challenged_rows:
            story_tr += (
                "Karşı örnekler bulunduğu için hiçbir süreç koşulsuz çalışan üstünlük olarak sunulmadı. "
            )
        else:
            story_tr += (
                "Açık karşı örnek bağlanmamış olması süreçlerin koşulsuz çalıştığını kanıtlamaz. "
            )
        story_tr += (
            "Bu sentez kronolojik maç hikâyesi, teknik direktör niyeti, taktik plan gerçeği veya nedensellik iddiası değildir."
        )

        entity_stories.append({
            "entity_scope": entity,
            "story_state": state,
            "headline_source_narrative_id": headline.get("narrative_id"),
            "source_narrative_ids": [row.get("narrative_id") for row in entity_rows],
            "process_narrative_count": len(entity_rows),
            "robust_recurrent_process_count": robust,
            "recurrent_process_count": recurrent,
            "proxy_process_count": proxy,
            "discovery_process_count": discovery,
            "counterevidence_bearing_process_count": len(challenged_rows),
            "context_sensitive_process_count": len(context_sensitive_rows),
            "no_visible_context_difference_process_count": len(no_visible_context_difference_rows),
            "null_evaluated_process_count": len(null_evaluated_rows),
            "null_above_median_process_count": len(null_above_median_rows),
            "nominal_support_sum": nominal_support,
            "unique_trace_ref_count": len(unique_trace_refs),
            "unique_trace_refs": unique_trace_refs,
            "success_support_sum_nominal": success,
            "failure_support_sum_nominal": failure,
            "divergence_support_sum_nominal": divergence,
            "no_visible_followup_support_sum_nominal": no_followup,
            "nominal_support_is_independent_evidence_count": False,
            "cross_process_support_independence_proven": False,
            "shared_trace_refs_across_processes": sorted(
                ref for ref in unique_trace_refs if len(all_trace_owners.get(ref, set())) > 1
            ),
            "story_tr": story_tr,
            "safe_meaning_tr": (
                "Bu entity için admitted görünür süreçlerin tekrar, sonuç dengesi, karşı örnek ve bağlamsal varyasyon profili birlikte özetlenmiştir."
            ),
            "forbidden_inference": [
                "football chronology from narrative priority",
                "coach intention",
                "tactical plan truth",
                "causality",
                "dominance",
                "team shape",
                "nominal support as independent evidence",
                "absence of counterevidence as confirmation",
            ],
            "withdrawal_condition": (
                "Recompute or downgrade if any source narrative, exact trace cohort, dependency state, counterevidence, context variation, null contrast or upstream claim ceiling changes."
            ),
            "chronological_story_claimed": False,
            "tactical_plan_truth_claimed": False,
            "coach_intention_claimed": False,
            "causality_claimed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "MATCH_LOCAL_PROCESS_STORY_SYNTHESIZED",
        "entity_stories": entity_stories,
        "entity_story_count": len(entity_stories),
        "source_narrative_block_count": len(rows),
        "review_hits": sorted(set(reviews)),
        "hard_block_hits": [],
        "story_order_basis": "UPSTREAM_EVIDENCE_PRIORITY_NOT_FOOTBALL_CHRONOLOGY",
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
