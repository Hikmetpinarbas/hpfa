from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "safe_finding_match_story_projection_lite_v1"
UPSTREAM_MODULE_ID = "sequence_safe_finding_binding_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "DEFEASIBLE_MATCH_LOCAL_MATCH_STORY_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "MATCH_STORY_PROJECTION_REJECTED",
        "match_story_candidates": [],
        "match_story_candidate_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_safe_finding_match_story_candidates(binding_payload: dict[str, Any]) -> dict[str, Any]:
    """Project already-emitted safe findings into analyst-facing match-story candidates.

    This is a presentation projection only. It does not rediscover evidence, order
    football episodes, create recurrence, or upgrade tactical/causal meaning.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    if binding_payload.get("module_id") != UPSTREAM_MODULE_ID:
        blocks.append("upstream_module_id_mismatch")
    if binding_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if binding_payload.get("true_action_count") != TRUE_ACTION_COUNT:
        blocks.append("true_action_count_claimed")
    if binding_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if binding_payload.get("hard_block_hits"):
        blocks.append("upstream_hard_blocks_present")
    upstream_status = _clean(binding_payload.get("status")).upper()
    if upstream_status == "FAIL_CLOSED":
        blocks.append("upstream_fail_closed")
    elif upstream_status == "REVIEW_REQUIRED":
        reviews.append("upstream_review_required")
    elif upstream_status != "PASS":
        reviews.append(f"upstream_status_review:{upstream_status or 'UNKNOWN'}")

    if blocks:
        return _fail(*blocks)

    rows = [row for row in (binding_payload.get("analyst_report_blocks") or []) if isinstance(row, dict)]
    if reviews:
        return {
            "module_id": MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "decision": "SAFE_FINDING_MATCH_STORY_ABSTAINED_PENDING_UPSTREAM_REVIEW",
            "match_story_candidates": [],
            "match_story_candidate_count": 0,
            "non_emitting_finding_rows_skipped": len(rows),
            "hard_block_hits": [],
            "review_hits": sorted(set(reviews)),
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    stories: list[dict[str, Any]] = []
    skipped = 0

    for row in rows:
        finding_status = _clean(row.get("finding_status")).upper()
        if finding_status != "EMIT":
            skipped += 1
            continue

        finding_id = _clean(row.get("analyst_report_block_id"))
        safe_meaning = _clean(row.get("SAFE_MEANING"))
        where_when = _clean(row.get("WHERE_WHEN"))
        support = _clean(row.get("SUPPORT"))
        counter = _clean(row.get("COUNTEREVIDENCE"))
        alternatives = _clean(row.get("ALTERNATIVE_EXPLANATIONS"))
        structured_alternatives = [item for item in (row.get("alternative_explanations") or []) if isinstance(item, dict)]
        analyst_action = _clean(row.get("ANALYST_ACTION"))
        withdrawal = _clean(row.get("withdrawal_condition"))
        forbidden = sorted({_clean(x).lower() for x in (row.get("FORBIDDEN_INFERENCE") or []) if _clean(x)})

        if row.get("professional_finding_emitted") is not True or row.get("claim_output_allowed") is not True:
            reviews.append(f"emit_row_without_claim_gate:{finding_id or 'UNKNOWN'}")
            continue
        if not finding_id or not safe_meaning or not where_when or not support or not counter or not alternatives or not withdrawal:
            reviews.append(f"emit_row_story_surface_incomplete:{finding_id or 'UNKNOWN'}")
            continue
        required_forbidden = {"causality", "coach intention", "dominance", "team shape", "true pressure geometry"}
        if not required_forbidden.issubset(set(forbidden)):
            reviews.append(f"emit_row_forbidden_inference_surface_incomplete:{finding_id}")
            continue

        story_text = f"{safe_meaning} {where_when} {counter} {alternatives}"
        stories.append(
            {
                "match_story_candidate_id": "msc_" + _digest(finding_id, safe_meaning, counter, alternatives)[:24],
                "source_professional_finding_ref": finding_id,
                "entity_scope": row.get("entity_scope"),
                "context_scope": row.get("context_scope") or [],
                "match_story_candidate_text": story_text,
                "story_support": support,
                "story_counterevidence": counter,
                "story_alternative_explanations": alternatives,
                "story_alternative_explanation_objects": structured_alternatives,
                "analyst_action": analyst_action,
                "withdrawal_condition": withdrawal,
                "story_order_is_football_chronology_truth": False,
                "story_is_possession_truth": False,
                "story_is_tactical_phase_truth": False,
                "story_is_formation_or_shape_truth": False,
                "story_is_true_pressure_truth": False,
                "story_is_coach_intention_truth": False,
                "story_is_dominance_truth": False,
                "story_is_causality_truth": False,
                "story_is_stable_team_tendency_truth": False,
                "professional_finding_emitted": True,
                "claim_output_allowed": True,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "true_action_count": TRUE_ACTION_COUNT,
                "production_release": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    status = "REVIEW_REQUIRED" if reviews else "PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "SAFE_FINDING_MATCH_STORY_CANDIDATES_BUILT",
        "match_story_candidates": stories,
        "match_story_candidate_count": len(stories),
        "non_emitting_finding_rows_skipped": skipped,
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
