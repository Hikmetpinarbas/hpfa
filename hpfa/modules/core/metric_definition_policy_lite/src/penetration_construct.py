from __future__ import annotations

from collections import Counter
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import (
    assess_construct_comparison,
)

MODULE_ID = "penetration_construct_v1"
PROGRESSION_MODULE_ID = "progression_effectiveness_construct_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
EPISODE_CONSEQUENCE_MODULE_ID = "episode_consequence_projection_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "VISIBLE_PROGRESSION_TO_TERMINAL_ACCESS_AND_EPISODE_RECURRENCE_PROFILE_CANDIDATE_ONLY"
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


def _episode_context_for_terminal_refs(
    terminal_refs: list[str], episode_payload: dict[str, Any] | None
) -> tuple[dict[str, Any], list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    empty = {
        "episode_context_surface_available": False,
        "terminal_support_episode_binding_coverage_rate_candidate": None,
        "terminal_support_episode_bound_candidate_count": 0,
        "terminal_support_episode_candidate_count": 0,
        "terminal_support_episode_candidate_refs": [],
        "visible_terminal_penetration_recurrence_candidate": None,
        "phase_activity_terminal_support_counts": {},
        "process_family_terminal_support_counts": {},
        "recurrence_is_intention_truth": False,
        "recurrence_is_tactical_pattern_truth": False,
    }
    if episode_payload is None:
        return empty, blocks, reviews
    if episode_payload.get("module_id") != EPISODE_CONSEQUENCE_MODULE_ID:
        return empty, ["episode_consequence_module_id_mismatch"], reviews
    if episode_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("episode_consequence_canonical_event_count_claimed")
    if episode_payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append("episode_consequence_true_action_count_claimed")
    if episode_payload.get("production_release") is True:
        blocks.append("episode_consequence_production_release_claimed")
    if episode_payload.get("hard_block_hits"):
        blocks.append("episode_consequence_hard_blocks_present")
    rows = episode_payload.get("episode_consequence_candidates") or []
    if not isinstance(rows, list):
        blocks.append("episode_consequence_inventory_invalid")
        rows = []
    if episode_payload.get("episode_consequence_candidate_count") != len(rows):
        blocks.append("episode_consequence_count_mismatch")
    if blocks:
        return empty, sorted(set(blocks)), reviews

    by_consequence: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"episode_consequence_record_invalid:{position}")
            continue
        consequence_id = _clean(row.get("trackable_action_consequence_candidate_id"))
        if not consequence_id:
            continue
        if consequence_id in by_consequence:
            duplicates.add(consequence_id)
            continue
        by_consequence[consequence_id] = row
    if duplicates:
        blocks.extend(f"episode_consequence_id_duplicate:{item}" for item in sorted(duplicates))
        return empty, sorted(set(blocks)), reviews

    bound_refs: list[str] = []
    episode_ids: set[str] = set()
    phase_counts: Counter[str] = Counter()
    process_counts: Counter[str] = Counter()
    for ref in terminal_refs:
        row = by_consequence.get(ref)
        if row is None:
            reviews.append(f"terminal_support_episode_context_missing:{ref}")
            continue
        if _clean(row.get("episode_binding_state")) != "SINGLE_EPISODE_NAVIGATION_ASSOCIATION":
            reviews.append(f"terminal_support_episode_context_not_single:{ref}")
            continue
        episode_id = _clean(row.get("episode_candidate_id"))
        if not episode_id:
            reviews.append(f"terminal_support_episode_id_missing:{ref}")
            continue
        bound_refs.append(ref)
        episode_ids.add(episode_id)
        for label in row.get("phase_activity_labels") or []:
            cleaned = _clean(label)
            if cleaned:
                phase_counts[cleaned] += 1
        process_map = row.get("process_family_annotation_counts") or {}
        if isinstance(process_map, dict):
            for family, count in process_map.items():
                cleaned = _clean(family)
                try:
                    numeric = int(count)
                except (TypeError, ValueError):
                    continue
                if cleaned and numeric > 0:
                    process_counts[cleaned] += numeric

    coverage = _ratio(len(bound_refs), len(terminal_refs))
    if not terminal_refs:
        recurrence: bool | None = None
    elif len(bound_refs) == len(terminal_refs):
        recurrence = len(episode_ids) >= 2
    else:
        recurrence = None
        reviews.append("terminal_support_episode_context_coverage_incomplete")

    return {
        "episode_context_surface_available": True,
        "terminal_support_episode_binding_coverage_rate_candidate": coverage,
        "terminal_support_episode_bound_candidate_count": len(bound_refs),
        "terminal_support_episode_candidate_count": len(episode_ids),
        "terminal_support_episode_candidate_refs": sorted(episode_ids),
        "visible_terminal_penetration_recurrence_candidate": recurrence,
        "phase_activity_terminal_support_counts": dict(sorted(phase_counts.items())),
        "process_family_terminal_support_counts": dict(sorted(process_counts.items())),
        "recurrence_is_intention_truth": False,
        "recurrence_is_tactical_pattern_truth": False,
    }, sorted(set(blocks)), sorted(set(reviews))


def build_penetration_construct(
    progression_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    guard: dict[str, Any],
    episode_consequence_payload: dict[str, Any] | None = None,
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

    episode_context, episode_blocks, episode_reviews = _episode_context_for_terminal_refs(
        terminal_refs, episode_consequence_payload
    )
    blocks.extend(episode_blocks)
    reviews.extend(episode_reviews)

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
            **episode_context,
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
                "repeated terminal support across navigation episodes may reflect repeated context exposure rather than tactical intention",
            ],
            "uncertainty": "MATCH_LOCAL_VISIBLE_TERMINAL_FOLLOWUP_WITH_NAVIGATION_EPISODE_RECURRENCE_CANDIDATE_ONLY_BOX_ACCESS_NOT_ADMITTED",
            "withdrawal_condition": "withdraw finding if progression denominator, temporal consequence admission, episode binding, provider terminal semantics, provenance/dependency controls, or follow-up coverage fail",
            "analyst_action": "inspect support, adverse and unresolved refs plus distinct episode/context recurrence; report repeated terminal access only as observed recurrence and do not claim complete box access or tactical intention",
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_followup_is_counterevidence": False,
            "penetration_score_emitted": False,
            "penetration_truth": False,
            "territorial_control_truth": False,
            "causal_creation_truth": False,
            "recurrence_truth": False,
            "tactical_pattern_truth": False,
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
        "recurrence_truth": False,
        "tactical_pattern_truth": False,
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
