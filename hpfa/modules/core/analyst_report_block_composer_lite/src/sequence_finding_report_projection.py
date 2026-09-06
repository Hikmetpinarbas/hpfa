from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "analyst_report_block_composer_lite_v1"
SOURCE_MODULE_ID = "sequence_safe_finding_binding_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "analyst_report_block_candidate_only"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "source_module_id": SOURCE_MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "SEQUENCE_FINDING_REPORT_PROJECTION_REJECTED",
        "report_blocks": [],
        "report_block_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _state_sentence(state: str, independent: Any) -> str:
    if state == "ROBUST_RECURRENT_VISIBLE_TRACE":
        return (
            "Tekrar, test edilen dayanıklılık aralığında korunuyor ve bağımsız destek açık biçimde kabul edilmiş durumda; "
            "bu yine de taktik plan veya nedensellik kanıtı değildir."
        )
    if state == "RECURRENT_VISIBLE_TRACE":
        if independent == "UNKNOWN":
            return (
                "Tekrar görünür durumda; ancak bağımsız destek henüz yeterince kanıtlanmadığı için bunu daha güçlü bir patern iddiasına yükseltmek doğru değildir."
            )
        return "Tekrar görünür durumda; mevcut kanıt bunu maç içi süreç tekrarı olarak kullanmaya izin veriyor."
    if state == "PROXY_CANDIDATE":
        return "Tekrar işareti var; fakat eşik, sıralama veya bağlam duyarlılığı nedeniyle yorum koşullu tutulmalıdır."
    return "Bu yalnız keşif düzeyinde görünür bir tekrar adayıdır; daha güçlü tekrar ve dayanıklılık kanıtı gerekir."


def compose_sequence_finding_report(source_payload: dict[str, Any]) -> dict[str, Any]:
    """Compose lay-readable Turkish analyst blocks from already-safe sequence findings.

    This projection changes presentation, not evidence strength. It does not discover
    sequences, recompute counts, infer tactics, infer causality or release claims.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    if source_payload.get("module_id") != SOURCE_MODULE_ID:
        blocks.append("source_module_id_mismatch")
    if source_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if source_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("true_action_count_claimed")
    if source_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if source_payload.get("hard_block_hits"):
        blocks.append("source_hard_blocks_present")
    status = _clean(source_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        blocks.append("source_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("source_review_required")
    elif status != "PASS":
        reviews.append(f"source_status_review:{status or 'UNKNOWN'}")
    if blocks:
        return _fail(*blocks)

    report_blocks: list[dict[str, Any]] = []
    for item in source_payload.get("analyst_report_blocks") or []:
        if not isinstance(item, dict):
            continue
        family_refs = [_clean(x) for x in (item.get("trace_family_refs") or []) if _clean(x)]
        if not family_refs:
            reviews.append("sequence_finding_missing_trace_family_ref")
            continue

        recurrence = dict(item.get("recurrence_summary") or {})
        state = _clean(recurrence.get("admission_state"))
        support = int(recurrence.get("observed_support") or 0)
        independent = recurrence.get("independent_support_count", "UNKNOWN")
        trace_variant_refs = sorted({_clean(x) for x in (item.get("trace_variant_refs") or []) if _clean(x)})
        if not trace_variant_refs:
            return _fail(f"sequence_finding_missing_trace_variant_refs:{family_refs[0]}")
        if len(trace_variant_refs) != support:
            return _fail(f"sequence_finding_trace_cohort_support_mismatch:{family_refs[0]}")
        if family_refs[0] not in trace_variant_refs:
            return _fail(f"sequence_finding_anchor_not_in_trace_cohort:{family_refs[0]}")

        success = int(item.get("success_support") or 0)
        failure = int(item.get("failure_support") or 0)
        divergence = int(item.get("divergence_support") or 0)
        no_followup = int(item.get("no_visible_followup_support") or 0)
        if support < success + failure + divergence + no_followup:
            return _fail(f"visible_outcome_partition_exceeds_support:{family_refs[0]}")

        lead = f"Maç içindeki karşılaştırılabilir aynı görünür aksiyon zinciri {support} kez gözlendi."
        outcome = (
            f" Bu örneklerin {success} tanesi aynı görünür ilerleme çizgisini desteklerken, "
            f"{failure} tanesi görünür başarısızlıkla ve {divergence} tanesi farklı bir görünür sonuçla ayrıştı."
        )
        if no_followup:
            outcome += f" {no_followup} örnekte görünür devam aksiyonu yok; bu durum başarısızlık olarak sayılmadı."
        meaning = " " + _state_sentence(state, independent)

        counter = dict(item.get("counterevidence") or {})
        counter_refs = [_clean(x) for x in (counter.get("refs") or []) if _clean(x)]
        if counter_refs:
            meaning += (
                " Aynı aile içinde karşı örnekler bulunduğu için bulgu, sürekli çalışan bir üstünlük olarak değil, belirli örneklerde görülen tekrarlanabilir bir süreç olarak okunmalıdır."
            )

        public_text = lead + outcome + meaning
        forbidden = {_clean(x).lower() for x in (item.get("FORBIDDEN_INFERENCE") or []) if _clean(x)}
        analyst_action = _clean(item.get("ANALYST_ACTION"))
        withdrawal = _clean(item.get("withdrawal_condition"))
        report_blocks.append({
            "report_block_id": "sequence_report_" + _digest(family_refs, trace_variant_refs, state, support)[:24],
            "block_family": "sequence_safe_finding_analyst_reading_candidate",
            "block_language": "tr",
            "report_block_candidate_tr": public_text,
            "what_happened_tr": lead,
            "support_and_counterevidence_tr": outcome.strip(),
            "safe_interpretation_tr": meaning.strip(),
            "analyst_action": analyst_action,
            "withdrawal_condition": withdrawal,
            "trace_family_refs": family_refs,
            "trace_variant_refs": trace_variant_refs,
            "entity_scope": item.get("entity_scope"),
            "context_scope": item.get("context_scope") or [],
            "observed_support": support,
            "independent_support_count": independent,
            "success_support": success,
            "failure_support": failure,
            "divergence_support": divergence,
            "no_visible_followup_support": no_followup,
            "counterevidence_refs": counter_refs,
            "dependency_summary": dict(item.get("dependency_summary") or {}),
            "uncertainty": dict(item.get("uncertainty") or {}),
            "robustness_summary": dict(item.get("robustness_summary") or {}),
            "forbidden_inference": sorted(forbidden),
            "status": "REVIEW_REQUIRED" if status == "REVIEW_REQUIRED" else "SMOKE_PASS",
            "decision": "ANALYST_READING_CANDIDATE_COMPOSED",
            "claim_ceiling": CLAIM_CEILING,
            "claim_output_allowed": False,
            "production_report_allowed": False,
            "final_report_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        })

    return {
        "module_id": MODULE_ID,
        "source_module_id": SOURCE_MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "SMOKE_PASS",
        "decision": "SEQUENCE_FINDING_ANALYST_BLOCKS_COMPOSED",
        "report_blocks": report_blocks,
        "report_block_count": len(report_blocks),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
