from __future__ import annotations

from collections import Counter
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import (
    assess_construct_comparison,
)

MODULE_ID = "penetration_construct_v1"
PROGRESSION_MODULE_ID = "progression_effectiveness_construct_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "VISIBLE_PROGRESSION_TO_TERMINAL_ACCESS_PROFILE_CANDIDATE_ONLY"
TERMINAL_SUPPORT = {"SHOT_FOLLOW_UP_CANDIDATE", "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"}
ADVERSE = {"OPPONENT_HANDOVER_CANDIDATE"}
REVIEW_OR_UNKNOWN = {
    "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def build_penetration_construct(
    progression_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    guard: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if progression_payload.get("module_id") != PROGRESSION_MODULE_ID:
        blocks.append("progression_module_id_mismatch")
    if consequence_payload.get("module_id") != CONSEQUENCE_MODULE_ID:
        blocks.append("consequence_module_id_mismatch")
    for prefix, payload in (("progression", progression_payload), ("consequence", consequence_payload)):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{prefix}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    progression = progression_payload.get("construct_candidate")
    if not isinstance(progression, dict):
        blocks.append("progression_construct_candidate_missing")
        progression = {}

    progression_refs = progression.get("eligible_progression_trace_candidate_refs") or []
    if not isinstance(progression_refs, list):
        blocks.append("progression_denominator_refs_invalid")
        progression_refs = []
    progression_ids = sorted({_clean(ref) for ref in progression_refs if _clean(ref)})
    if progression.get("eligible_progression_trace_candidate_count") != len(progression_ids):
        blocks.append("progression_denominator_count_mismatch")

    trace_binding = _clean(progression.get("provenance_root"))
    consequence_binding = _clean(consequence_payload.get("match_surface_binding_id"))
    if not trace_binding or trace_binding != consequence_binding:
        blocks.append("match_surface_binding_mismatch")

    consequences = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(consequences, list):
        blocks.append("consequence_inventory_invalid")
        consequences = []
    if consequence_payload.get("trackable_action_consequence_candidate_count") != len(consequences):
        blocks.append("consequence_count_mismatch")

    by_anchor: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(consequences):
        if not isinstance(row, dict):
            blocks.append(f"consequence_record_invalid:{position}")
            continue
        anchor = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        if not anchor or anchor in by_anchor:
            blocks.append(f"consequence_anchor_invalid_or_duplicate:{position}")
            continue
        by_anchor[anchor] = row

    context = {
        "denominator_set_id": f"penetration_evaluable_progression:{trace_binding}",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": _clean(progression.get("entity_scope")) or "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": _clean(progression.get("team_scope")) or "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": _clean(progression.get("period_scope")) or "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_PENETRATION_V1",
        "source_surface_roles": progression.get("source_surface_roles") or ["NO_VISIBLE_SOURCE_ROLE"],
        "required_event_families": ["PASS", "CARRY", "SHOT_OR_TERMINAL_VISIBLE_FOLLOW_UP"],
        "construct_target": "PENETRATION",
        "dependency_group": f"penetration:{trace_binding}",
        "provenance_root": trace_binding,
    }
    guard_result = assess_construct_comparison(context, context, guard)
    if not guard_result.get("comparison_admitted"):
        blocks.append("construct_context_guard_not_admitted")

    evaluable_refs: list[str] = []
    terminal_refs: list[str] = []
    shot_refs: list[str] = []
    terminal_outcome_refs: list[str] = []
    adverse_refs: list[str] = []
    neutral_refs: list[str] = []
    unresolved_refs: list[str] = []
    classifications: Counter[str] = Counter()

    for trace_id in progression_ids:
        row = by_anchor.get(trace_id)
        if row is None:
            unresolved_refs.append(trace_id)
            continue
        consequence_id = _clean(row.get("trackable_action_consequence_candidate_id")) or trace_id
        primary = _clean(row.get("primary_consequence_candidate"))
        status = _clean(row.get("record_status"))
        classifications[primary or "UNKNOWN"] += 1
        if status == "REVIEW_REQUIRED" or not primary or primary in REVIEW_OR_UNKNOWN:
            unresolved_refs.append(consequence_id)
            continue
        evaluable_refs.append(consequence_id)
        if primary in TERMINAL_SUPPORT:
            terminal_refs.append(consequence_id)
            if primary == "SHOT_FOLLOW_UP_CANDIDATE":
                shot_refs.append(consequence_id)
            else:
                terminal_outcome_refs.append(consequence_id)
        elif primary in ADVERSE:
            adverse_refs.append(consequence_id)
        else:
            neutral_refs.append(consequence_id)

    evaluable = len(evaluable_refs)
    if not progression_ids:
        reviews.append("no_progression_denominator_visible")
    if unresolved_refs:
        reviews.append("penetration_followup_coverage_incomplete")
    if evaluable == 0:
        reviews.append("no_penetration_evaluable_progression_visible")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS_CANDIDATE")
    construct = None
    if not blocks:
        construct = {
            "construct_candidate_id": f"pen_{trace_binding[-16:] or 'unbound'}",
            **context,
            "eligible_progression_trace_candidate_count": len(progression_ids),
            "eligible_progression_trace_candidate_refs": progression_ids,
            "penetration_evaluable_progression_candidate_count": evaluable,
            "penetration_followup_coverage_rate_candidate": _ratio(evaluable, len(progression_ids)),
            "visible_terminal_penetration_support_candidate_count": len(terminal_refs),
            "visible_shot_followup_candidate_count": len(shot_refs),
            "visible_terminal_outcome_support_candidate_count": len(terminal_outcome_refs),
            "visible_adverse_handover_candidate_count": len(adverse_refs),
            "visible_nonterminal_continuation_candidate_count": len(neutral_refs),
            "unresolved_or_missing_followup_candidate_count": len(unresolved_refs),
            "terminal_penetration_rate_among_evaluable_candidate": _ratio(len(terminal_refs), evaluable),
            "shot_followup_rate_among_evaluable_candidate": _ratio(len(shot_refs), evaluable),
            "adverse_handover_rate_among_evaluable_candidate": _ratio(len(adverse_refs), evaluable),
            "consequence_classification_counts": dict(sorted(classifications.items())),
            "support_consequence_candidate_refs": sorted(terminal_refs),
            "counterevidence_consequence_candidate_refs": sorted(adverse_refs),
            "neutral_consequence_candidate_refs": sorted(neutral_refs),
            "unresolved_consequence_candidate_refs": sorted(unresolved_refs),
            "box_access_surface_available": False,
            "box_access_rate_candidate": None,
            "box_access_not_inferred_from_shot": True,
            "alternative_explanations": [
                "terminal follow-up may reflect teammate/opponent response rather than progression quality alone",
                "provider annotation coverage may omit visible access that does not receive a terminal label",
                "shot follow-up is a terminal-access surface and must not be treated as complete box-entry coverage",
                "match-local role and game-state mix may alter the progression opportunity set",
            ],
            "uncertainty": "MATCH_LOCAL_VISIBLE_TERMINAL_FOLLOWUP_ONLY_BOX_ACCESS_SURFACE_NOT_YET_ADMITTED",
            "withdrawal_condition": "withdraw finding if progression denominator, temporal consequence admission, provider terminal semantics, provenance/dependency controls, or follow-up coverage fail",
            "analyst_action": "inspect support, adverse and unresolved refs; report terminal penetration only and do not claim complete box access until an admitted box-access surface exists",
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_followup_is_counterevidence": False,
            "penetration_score_emitted": False,
            "penetration_truth": False,
            "territorial_control_truth": False,
            "causal_creation_truth": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "observation_model": OBSERVATION_MODEL,
        "construct_candidate": construct,
        "construct_candidate_count": 1 if construct is not None else 0,
        "construct_context_guard": guard_result,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "penetration_truth": False,
        "box_access_truth": False,
        "territorial_control_truth": False,
        "sequence_truth": False,
        "causal_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "event_only_is_product_ceiling": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
