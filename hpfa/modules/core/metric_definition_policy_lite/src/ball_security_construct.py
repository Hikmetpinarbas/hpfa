from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import (
    assess_construct_comparison,
)

MODULE_ID = "ball_security_construct_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "BALL_SECURITY_PROFILE_CANDIDATE_ONLY"
BALL_USE_FAMILIES = {"PASS", "CARRY", "DRIBBLE"}
POSITIVE_CONSEQUENCES = {
    "SAME_TEAM_CONTINUATION_CANDIDATE",
    "SHOT_FOLLOW_UP_CANDIDATE",
    "TERMINAL_OUTCOME_SUPPORT_CANDIDATE",
    "RESTART_OR_RESET_CANDIDATE",
}
ADVERSE_CONSEQUENCES = {
    "OPPONENT_HANDOVER_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
}
REVIEW_OR_UNKNOWN_CONSEQUENCES = {
    "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
    "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _families(trace: dict[str, Any]) -> set[str]:
    values = {_clean(item) for item in (trace.get("action_family_candidates") or []) if _clean(item)}
    single = _clean(trace.get("action_family_candidate"))
    if single:
        values.add(single)
    return values


def _validate_input(payload: dict[str, Any], module_id: str, prefix: str, blocks: list[str]) -> None:
    if payload.get("module_id") != module_id:
        blocks.append(f"{prefix}_module_id_mismatch")
    if payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append(f"{prefix}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append(f"{prefix}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{prefix}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{prefix}_hard_blocks_present")


def _profiles(
    groups: dict[str, list[str]],
    states: dict[str, tuple[str, str | None, str | None]],
    *,
    entity_key: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entity_id, trace_ids in sorted(groups.items()):
        retained: list[str] = []
        exposed: list[str] = []
        unresolved: list[str] = []
        counts: Counter[str] = Counter()
        for trace_id in trace_ids:
            state, consequence_id, primary = states.get(trace_id, ("UNRESOLVED", None, None))
            if primary:
                counts[primary] += 1
            ref = consequence_id or trace_id
            if state == "RETAINED":
                retained.append(ref)
            elif state == "EXPOSED":
                exposed.append(ref)
            else:
                unresolved.append(ref)
        evaluable = len(retained) + len(exposed)
        rows.append({
            entity_key: entity_id,
            "eligible_ball_use_trace_candidate_count": len(trace_ids),
            "evaluable_ball_security_consequence_candidate_count": evaluable,
            "visible_retained_follow_up_candidate_count": len(retained),
            "visible_adverse_handover_candidate_count": len(exposed),
            "retention_rate_among_evaluable_candidate": _ratio(len(retained), evaluable),
            "loss_exposure_rate_among_evaluable_candidate": _ratio(len(exposed), evaluable),
            "unresolved_or_missing_consequence_candidate_count": len(unresolved),
            "consequence_classification_counts": dict(sorted(counts.items())),
            "support_consequence_candidate_refs": sorted(retained),
            "counterevidence_consequence_candidate_refs": sorted(exposed),
            "unresolved_consequence_candidate_refs": sorted(unresolved),
            "profile_is_player_quality_truth": False,
            "profile_is_team_control_truth": False,
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_consequence_is_counterevidence": False,
        })
    return rows


def build_ball_security_construct(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    guard: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    _validate_input(trace_payload, TRACE_MODULE_ID, "trace", blocks)
    _validate_input(consequence_payload, CONSEQUENCE_MODULE_ID, "consequence", blocks)

    binding = _clean(trace_payload.get("match_surface_binding_id"))
    if not binding or binding != _clean(consequence_payload.get("match_surface_binding_id")):
        blocks.append("match_surface_binding_mismatch")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    consequences = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(traces, list):
        blocks.append("trace_inventory_invalid")
        traces = []
    if not isinstance(consequences, list):
        blocks.append("consequence_inventory_invalid")
        consequences = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_count_mismatch")
    if consequence_payload.get("trackable_action_consequence_candidate_count") != len(consequences):
        blocks.append("consequence_count_mismatch")

    trace_by_id: dict[str, dict[str, Any]] = {}
    ball_use_ids: list[str] = []
    explicit_turnover_ids: list[str] = []
    team_groups: dict[str, list[str]] = defaultdict(list)
    actor_groups: dict[str, list[str]] = defaultdict(list)
    for position, trace in enumerate(traces):
        if not isinstance(trace, dict):
            blocks.append(f"trace_record_invalid:{position}")
            continue
        trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in trace_by_id:
            blocks.append(f"trace_id_invalid_or_duplicate:{position}")
            continue
        trace_by_id[trace_id] = trace
        families = _families(trace)
        if "TURNOVER" in families:
            explicit_turnover_ids.append(trace_id)
        if not (families & BALL_USE_FAMILIES):
            continue
        ball_use_ids.append(trace_id)
        team_id = _clean(trace.get("team_identity_candidate_id"))
        actor_id = _clean(trace.get("actor_identity_candidate_id"))
        if team_id:
            team_groups[team_id].append(trace_id)
        else:
            reviews.append(f"ball_use_trace_team_identity_missing:{trace_id}")
        if actor_id:
            actor_groups[actor_id].append(trace_id)
        else:
            reviews.append(f"ball_use_trace_actor_identity_missing:{trace_id}")

    consequence_by_anchor: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(consequences):
        if not isinstance(row, dict):
            blocks.append(f"consequence_record_invalid:{position}")
            continue
        anchor = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        if not anchor or anchor in consequence_by_anchor:
            blocks.append(f"consequence_anchor_invalid_or_duplicate:{position}")
            continue
        if anchor not in trace_by_id:
            blocks.append(f"consequence_anchor_trace_missing:{anchor}")
            continue
        consequence_by_anchor[anchor] = row

    context = {
        "denominator_set_id": f"ball_use_trace_candidates:{binding}",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_BALL_SECURITY_V1",
        "source_surface_roles": sorted({_clean(row.get("source_role")) for row in traces if isinstance(row, dict) and _clean(row.get("source_role"))}) or ["NO_VISIBLE_SOURCE_ROLE"],
        "required_event_families": sorted(BALL_USE_FAMILIES),
        "construct_target": "BALL_SECURITY",
        "dependency_group": f"ball_security:{binding}",
        "provenance_root": binding,
    }
    guard_result = assess_construct_comparison(context, context, guard)
    if not guard_result.get("comparison_admitted"):
        blocks.append("construct_context_guard_not_admitted")

    states: dict[str, tuple[str, str | None, str | None]] = {}
    retained_refs: list[str] = []
    exposure_refs: list[str] = []
    unresolved_refs: list[str] = []
    counts: Counter[str] = Counter()
    for trace_id in ball_use_ids:
        row = consequence_by_anchor.get(trace_id)
        if row is None:
            unresolved_refs.append(trace_id)
            states[trace_id] = ("UNRESOLVED", None, None)
            continue
        primary = _clean(row.get("primary_consequence_candidate"))
        status = _clean(row.get("record_status"))
        consequence_id = _clean(row.get("trackable_action_consequence_candidate_id")) or trace_id
        counts[primary or "UNKNOWN"] += 1
        if status == "REVIEW_REQUIRED" or primary in REVIEW_OR_UNKNOWN_CONSEQUENCES or not primary:
            unresolved_refs.append(consequence_id)
            states[trace_id] = ("UNRESOLVED", consequence_id, primary or None)
        elif primary in POSITIVE_CONSEQUENCES:
            retained_refs.append(consequence_id)
            states[trace_id] = ("RETAINED", consequence_id, primary)
        elif primary in ADVERSE_CONSEQUENCES:
            exposure_refs.append(consequence_id)
            states[trace_id] = ("EXPOSED", consequence_id, primary)
        else:
            unresolved_refs.append(consequence_id)
            states[trace_id] = ("UNRESOLVED", consequence_id, primary)

    denominator = len(ball_use_ids)
    evaluable = len(retained_refs) + len(exposure_refs)
    if denominator == 0:
        reviews.append("no_ball_use_eligible_trace_candidate_visible")
    if denominator - evaluable > 0:
        reviews.append("ball_security_consequence_coverage_incomplete")

    team_profiles = _profiles(team_groups, states, entity_key="team_identity_candidate_id")
    actor_profiles = _profiles(actor_groups, states, entity_key="actor_identity_candidate_id")
    if sum(row["eligible_ball_use_trace_candidate_count"] for row in team_profiles) != denominator:
        reviews.append("team_ball_use_denominator_reconciliation_incomplete")
    if sum(row["eligible_ball_use_trace_candidate_count"] for row in actor_profiles) != denominator:
        reviews.append("actor_ball_use_denominator_reconciliation_incomplete")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS_CANDIDATE")
    construct = None
    if not blocks:
        construct = {
            "construct_candidate_id": f"bsc_{binding[-16:] or 'unbound'}",
            **context,
            "eligible_ball_use_trace_candidate_count": denominator,
            "eligible_ball_use_trace_candidate_refs": sorted(ball_use_ids),
            "evaluable_ball_security_consequence_candidate_count": evaluable,
            "ball_security_consequence_coverage_rate_candidate": _ratio(evaluable, denominator),
            "visible_retained_follow_up_candidate_count": len(retained_refs),
            "visible_adverse_handover_candidate_count": len(exposure_refs),
            "retention_rate_among_evaluable_candidate": _ratio(len(retained_refs), evaluable),
            "loss_exposure_rate_among_evaluable_candidate": _ratio(len(exposure_refs), evaluable),
            "unresolved_or_missing_consequence_candidate_count": denominator - evaluable,
            "explicit_turnover_trace_candidate_count_outside_denominator": len(explicit_turnover_ids),
            "explicit_turnover_trace_candidate_refs_outside_denominator": sorted(explicit_turnover_ids),
            "explicit_turnover_is_denominator_member": False,
            "consequence_classification_counts": dict(sorted(counts.items())),
            "support_consequence_candidate_refs": sorted(retained_refs),
            "counterevidence_consequence_candidate_refs": sorted(exposure_refs),
            "unresolved_consequence_candidate_refs": sorted(unresolved_refs),
            "team_ball_security_profile_candidates": team_profiles,
            "actor_ball_security_profile_candidates": actor_profiles,
            "team_profile_denominator_reconciles_to_construct": sum(row["eligible_ball_use_trace_candidate_count"] for row in team_profiles) == denominator,
            "actor_profile_denominator_reconciles_to_construct": sum(row["eligible_ball_use_trace_candidate_count"] for row in actor_profiles) == denominator,
            "alternative_explanations": [
                "visible retention may reflect receiver support or opponent response rather than anchor quality alone",
                "provider event-family coverage may omit some ball-control losses",
                "explicit turnover traces are retained as context/counterevidence and are not injected into the ball-use denominator",
                "match-local role, game-state and action mix may alter the opportunity set",
            ],
            "uncertainty": "MATCH_LOCAL_VISIBLE_BALL_USE_CONSEQUENCE_COVERAGE_ONLY_NO_CALIBRATED_BALL_SECURITY_TRUTH",
            "withdrawal_condition": "withdraw comparison or finding if denominator/context alignment, temporal admission, consequence coverage, identity reconciliation, reflection control, or dependency controls fail",
            "analyst_action": "inspect ball-use denominator, retained/adverse/unresolved consequence refs and explicit turnover context before describing ball security or loss exposure",
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_consequence_is_counterevidence": False,
            "ball_security_score_emitted": False,
            "construct_validity_truth": False,
            "player_quality_truth": False,
            "team_control_truth": False,
            "causal_truth": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    return {
        "module_id": MODULE_ID,
        "status": status,
        "construct_candidate": construct,
        "construct_candidate_count": 1 if construct is not None else 0,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "observation_model": OBSERVATION_MODEL,
        "event_only_is_product_ceiling": False,
        "ball_security_truth": False,
        "loss_exposure_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
