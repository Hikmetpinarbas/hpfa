from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "analyst_report_block_composer_lite_v1"
SOURCE_MODULE_ID = "match_story_synthesis_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "analyst_report_block_candidate_only"
SOURCE_CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "source_module_id": SOURCE_MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "MATCH_STORY_REPORT_PROJECTION_REJECTED",
        "report_blocks": [],
        "report_block_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "review_hits": [],
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def compose_match_story_report(source_payload: dict[str, Any]) -> dict[str, Any]:
    """Project entity-level match stories into analyst-readable report block candidates.

    The projection does not discover new football facts or strengthen evidence. It keeps
    process counts nominal, preserves unique trace lineage, and carries the source claim
    ceiling and withdrawal condition into the report candidate.
    """
    hard: list[str] = []
    reviews: list[str] = []
    if source_payload.get("module_id") != SOURCE_MODULE_ID:
        hard.append("source_module_id_mismatch")
    if source_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        hard.append("canonical_event_count_claimed")
    if source_payload.get("true_action_count") != TRUE_ACTION_COUNT:
        hard.append("true_action_count_claimed")
    if source_payload.get("production_release") is True:
        hard.append("production_release_claimed")
    if _clean(source_payload.get("claim_ceiling")) != SOURCE_CLAIM_CEILING:
        hard.append("source_claim_ceiling_mismatch")
    if source_payload.get("chronological_story_claimed") is not False:
        hard.append("source_chronology_lock_breach")
    if source_payload.get("tactical_plan_truth_claimed") is not False:
        hard.append("source_tactical_plan_lock_breach")
    if source_payload.get("coach_intention_claimed") is not False:
        hard.append("source_coach_intention_lock_breach")
    if source_payload.get("causality_claimed") is not False:
        hard.append("source_causality_lock_breach")
    if source_payload.get("hard_block_hits"):
        hard.append("source_hard_blocks_present")

    status = _clean(source_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        hard.append("source_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("source_review_required")
    elif status != "PASS":
        reviews.append(f"source_status_review:{status or 'UNKNOWN'}")
    if hard:
        return _fail(*hard)

    stories = [row for row in (source_payload.get("entity_stories") or []) if isinstance(row, dict)]
    declared = source_payload.get("entity_story_count")
    if not _is_nonnegative_int(declared) or declared != len(stories):
        return _fail("entity_story_count_mismatch")

    report_blocks: list[dict[str, Any]] = []
    seen_entities: set[str] = set()
    for story in stories:
        entity = _clean(story.get("entity_scope"))
        if not entity:
            return _fail("entity_scope_missing")
        if entity in seen_entities:
            return _fail(f"duplicate_entity_story:{entity}")
        seen_entities.add(entity)

        if story.get("chronological_story_claimed") is not False:
            return _fail(f"story_chronology_lock_breach:{entity}")
        if story.get("tactical_plan_truth_claimed") is not False:
            return _fail(f"story_tactical_plan_lock_breach:{entity}")
        if story.get("coach_intention_claimed") is not False:
            return _fail(f"story_coach_intention_lock_breach:{entity}")
        if story.get("causality_claimed") is not False:
            return _fail(f"story_causality_lock_breach:{entity}")
        if story.get("production_release") is not False:
            return _fail(f"story_production_release_lock_breach:{entity}")
        if story.get("canonical_event_count") != CANONICAL_EVENT_COUNT or story.get("true_action_count") != TRUE_ACTION_COUNT:
            return _fail(f"story_count_truth_lock_breach:{entity}")
        if _clean(story.get("claim_ceiling")) != SOURCE_CLAIM_CEILING:
            return _fail(f"story_claim_ceiling_mismatch:{entity}")
        if story.get("nominal_support_is_independent_evidence_count") is not False:
            return _fail(f"story_nominal_support_independence_lock_breach:{entity}")
        if story.get("cross_process_support_independence_proven") is not False:
            return _fail(f"story_cross_process_independence_lock_breach:{entity}")

        source_ids = sorted({_clean(x) for x in (story.get("source_narrative_ids") or []) if _clean(x)})
        trace_refs = sorted({_clean(x) for x in (story.get("unique_trace_refs") or []) if _clean(x)})
        if not source_ids:
            return _fail("source_narrative_ids_missing:" + entity)

        process_count = story.get("process_narrative_count")
        recurrent_count = story.get("recurrent_process_count")
        robust_count = story.get("robust_recurrent_process_count")
        counter_count = story.get("counterevidence_bearing_process_count")
        context_count = story.get("context_sensitive_process_count")
        null_count = story.get("null_evaluated_process_count")
        accounting = {
            "process_narrative_count": process_count,
            "recurrent_process_count": recurrent_count,
            "robust_recurrent_process_count": robust_count,
            "counterevidence_bearing_process_count": counter_count,
            "context_sensitive_process_count": context_count,
            "null_evaluated_process_count": null_count,
        }
        for key, value in accounting.items():
            if not _is_nonnegative_int(value):
                return _fail(f"story_{key}_invalid:{entity}")
        if process_count != len(source_ids):
            return _fail(f"story_process_narrative_count_mismatch:{entity}")
        for key, value in accounting.items():
            if key != "process_narrative_count" and value > process_count:
                return _fail(f"story_{key}_exceeds_process_count:{entity}")
        if robust_count > recurrent_count:
            return _fail(f"story_robust_recurrent_process_count_exceeds_recurrent:{entity}")

        unique_count = story.get("unique_trace_ref_count")
        if not _is_nonnegative_int(unique_count) or unique_count != len(trace_refs):
            return _fail(f"unique_trace_count_mismatch:{entity}")
        nominal_support = story.get("nominal_support_sum")
        if not _is_nonnegative_int(nominal_support) or nominal_support < len(trace_refs):
            return _fail(f"nominal_support_invalid:{entity}")
        withdrawal = _clean(story.get("withdrawal_condition"))
        text = _clean(story.get("story_tr"))
        safe_meaning = _clean(story.get("safe_meaning_tr"))
        if not withdrawal:
            return _fail(f"withdrawal_condition_missing:{entity}")
        if not text or not safe_meaning:
            return _fail(f"story_text_missing:{entity}")

        shared_refs = sorted({_clean(x) for x in (story.get("shared_trace_refs_across_processes") or []) if _clean(x)})
        if shared_refs:
            reviews.append(f"shared_trace_refs_review:{entity}")

        report_blocks.append({
            "report_block_id": "match_story_report_" + _digest(entity, source_ids, trace_refs)[:24],
            "block_family": "match_story_analyst_reading_candidate",
            "block_language": "tr",
            "report_block_candidate_tr": text,
            "safe_meaning_tr": safe_meaning,
            "story_state": _clean(story.get("story_state")),
            "entity_scope": entity,
            "source_narrative_ids": source_ids,
            "process_narrative_count": process_count,
            "recurrent_process_count": recurrent_count,
            "robust_recurrent_process_count": robust_count,
            "counterevidence_bearing_process_count": counter_count,
            "context_sensitive_process_count": context_count,
            "null_evaluated_process_count": null_count,
            "nominal_support_sum": nominal_support,
            "unique_trace_ref_count": unique_count,
            "unique_trace_refs": trace_refs,
            "shared_trace_refs_across_processes": shared_refs,
            "nominal_support_is_independent_evidence_count": False,
            "cross_process_support_independence_proven": False,
            "forbidden_inference": list(story.get("forbidden_inference") or []),
            "withdrawal_condition": withdrawal,
            "upstream_claim_ceiling": SOURCE_CLAIM_CEILING,
            "status": "REVIEW_REQUIRED" if status == "REVIEW_REQUIRED" or shared_refs else "SMOKE_PASS",
            "decision": "MATCH_STORY_ANALYST_READING_CANDIDATE_COMPOSED",
            "claim_output_allowed": False,
            "production_report_allowed": False,
            "final_report_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    return {
        "module_id": MODULE_ID,
        "source_module_id": SOURCE_MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "SMOKE_PASS",
        "decision": "MATCH_STORY_ANALYST_BLOCKS_COMPOSED",
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
