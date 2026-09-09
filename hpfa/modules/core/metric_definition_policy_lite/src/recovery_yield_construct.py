from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import assess_construct_comparison

MODULE_ID = "recovery_yield_construct_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
EPISODE_CONSEQUENCE_MODULE_ID = "episode_consequence_projection_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "RECOVERY_YIELD_PROFILE_CANDIDATE_ONLY"
RECOVERY_FAMILIES = {"RECOVERY", "INTERCEPTION"}
POSITIVE_CONSEQUENCES = {
    "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
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


def _validate(payload: dict[str, Any], module_id: str, prefix: str, blocks: list[str]) -> None:
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


def _profile(trace_ids: list[str], states: dict[str, tuple[str, str | None, str | None]]) -> dict[str, Any]:
    positive: list[str] = []
    adverse: list[str] = []
    unresolved: list[str] = []
    counts: Counter[str] = Counter()
    for trace_id in trace_ids:
        state, ref, primary = states.get(trace_id, ("UNRESOLVED", None, None))
        if primary:
            counts[primary] += 1
        ref = ref or trace_id
        if state == "YIELD":
            positive.append(ref)
        elif state == "ADVERSE":
            adverse.append(ref)
        else:
            unresolved.append(ref)
    evaluable = len(positive) + len(adverse)
    return {
        "eligible_recovery_trace_candidate_count": len(trace_ids),
        "evaluable_recovery_consequence_candidate_count": evaluable,
        "visible_same_team_yield_candidate_count": len(positive),
        "visible_adverse_post_recovery_handover_candidate_count": len(adverse),
        "recovery_yield_rate_among_evaluable_candidate": _ratio(len(positive), evaluable),
        "post_recovery_exposure_rate_among_evaluable_candidate": _ratio(len(adverse), evaluable),
        "unresolved_or_missing_consequence_candidate_count": len(unresolved),
        "consequence_classification_counts": dict(sorted(counts.items())),
        "support_consequence_candidate_refs": sorted(positive),
        "counterevidence_consequence_candidate_refs": sorted(adverse),
        "unresolved_consequence_candidate_refs": sorted(unresolved),
        "profile_is_recovery_quality_truth": False,
        "profile_is_possession_gain_truth": False,
        "same_provider_reflection_adds_independent_vote": False,
        "independent_support_vote_count": 0,
        "missing_consequence_is_counterevidence": False,
    }


def _profiles(
    groups: dict[str, list[str]],
    states: dict[str, tuple[str, str | None, str | None]],
    entity_key: str,
) -> list[dict[str, Any]]:
    return [
        {entity_key: entity_id, **_profile(trace_ids, states)}
        for entity_id, trace_ids in sorted(groups.items())
    ]


def _episode_context_index(
    payload: dict[str, Any] | None,
    blocks: list[str],
) -> dict[str, dict[str, Any]]:
    if payload is None:
        return {}
    _validate(payload, EPISODE_CONSEQUENCE_MODULE_ID, "episode_consequence", blocks)
    rows = payload.get("episode_consequence_candidates") or []
    if not isinstance(rows, list):
        blocks.append("episode_consequence_candidates_invalid")
        return {}
    index: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"episode_consequence_record_invalid:{position}")
            continue
        anchor = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        if not anchor or anchor in index:
            blocks.append(f"episode_consequence_anchor_invalid_or_duplicate:{position}")
            continue
        index[anchor] = row
    return index


def _context_profiles(
    groups: dict[str, list[str]],
    states: dict[str, tuple[str, str | None, str | None]],
    context_key: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, trace_ids in sorted(groups.items()):
        rows.append({
            context_key: label,
            **_profile(sorted(set(trace_ids)), states),
            "context_profile_is_phase_truth": False,
            "context_profile_is_tactical_plan_truth": False,
            "context_profile_is_causal_truth": False,
            "context_profile_denominator_is_additive_across_labels": False,
        })
    return rows


def build_recovery_yield_construct(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    guard: dict[str, Any],
    episode_consequence_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    _validate(trace_payload, TRACE_MODULE_ID, "trace", blocks)
    _validate(consequence_payload, CONSEQUENCE_MODULE_ID, "consequence", blocks)
    episode_context_by_anchor = _episode_context_index(episode_consequence_payload, blocks)

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
    recovery_ids: list[str] = []
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
        if not (_families(trace) & RECOVERY_FAMILIES):
            continue
        recovery_ids.append(trace_id)
        team_id = _clean(trace.get("team_identity_candidate_id"))
        actor_id = _clean(trace.get("actor_identity_candidate_id"))
        if team_id:
            team_groups[team_id].append(trace_id)
        else:
            reviews.append(f"recovery_trace_team_identity_missing:{trace_id}")
        if actor_id:
            actor_groups[actor_id].append(trace_id)
        else:
            reviews.append(f"recovery_trace_actor_identity_missing:{trace_id}")

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
        "denominator_set_id": f"recovery_interception_trace_candidates:{binding}",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_RECOVERY_YIELD_V1",
        "source_surface_roles": sorted({
            _clean(row.get("source_role"))
            for row in traces
            if isinstance(row, dict) and _clean(row.get("source_role"))
        }) or ["NO_VISIBLE_SOURCE_ROLE"],
        "required_event_families": sorted(RECOVERY_FAMILIES),
        "construct_target": "RECOVERY_YIELD",
        "dependency_group": f"recovery_yield:{binding}",
        "provenance_root": binding,
    }
    if not assess_construct_comparison(context, context, guard).get("comparison_admitted"):
        blocks.append("construct_context_guard_not_admitted")

    states: dict[str, tuple[str, str | None, str | None]] = {}
    positive_refs: list[str] = []
    adverse_refs: list[str] = []
    unresolved_refs: list[str] = []
    counts: Counter[str] = Counter()
    for trace_id in recovery_ids:
        row = consequence_by_anchor.get(trace_id)
        if row is None:
            unresolved_refs.append(trace_id)
            states[trace_id] = ("UNRESOLVED", None, None)
            continue
        primary = _clean(row.get("primary_consequence_candidate"))
        status = _clean(row.get("record_status"))
        ref = _clean(row.get("trackable_action_consequence_candidate_id")) or trace_id
        counts[primary or "UNKNOWN"] += 1
        if status == "REVIEW_REQUIRED" or primary in REVIEW_OR_UNKNOWN_CONSEQUENCES or not primary:
            unresolved_refs.append(ref)
            states[trace_id] = ("UNRESOLVED", ref, primary or None)
        elif primary in POSITIVE_CONSEQUENCES:
            positive_refs.append(ref)
            states[trace_id] = ("YIELD", ref, primary)
        elif primary in ADVERSE_CONSEQUENCES:
            adverse_refs.append(ref)
            states[trace_id] = ("ADVERSE", ref, primary)
        else:
            unresolved_refs.append(ref)
            states[trace_id] = ("UNRESOLVED", ref, primary)

    denominator = len(recovery_ids)
    evaluable = len(positive_refs) + len(adverse_refs)
    if denominator == 0:
        reviews.append("no_recovery_eligible_trace_candidate_visible")
    if denominator - evaluable > 0:
        reviews.append("recovery_yield_consequence_coverage_incomplete")

    team_profiles = _profiles(team_groups, states, "team_identity_candidate_id")
    actor_profiles = _profiles(actor_groups, states, "actor_identity_candidate_id")
    if sum(row["eligible_recovery_trace_candidate_count"] for row in team_profiles) != denominator:
        reviews.append("team_recovery_denominator_reconciliation_incomplete")
    if sum(row["eligible_recovery_trace_candidate_count"] for row in actor_profiles) != denominator:
        reviews.append("actor_recovery_denominator_reconciliation_incomplete")

    phase_groups: dict[str, list[str]] = defaultdict(list)
    process_groups: dict[str, list[str]] = defaultdict(list)
    context_bound_ids: list[str] = []
    context_unbound_ids: list[str] = []
    if episode_consequence_payload is not None and not blocks:
        for trace_id in recovery_ids:
            row = episode_context_by_anchor.get(trace_id)
            if (
                row is None
                or _clean(row.get("episode_binding_state")) != "SINGLE_EPISODE_NAVIGATION_ASSOCIATION"
                or not _clean(row.get("episode_candidate_id"))
            ):
                context_unbound_ids.append(trace_id)
                continue
            context_bound_ids.append(trace_id)
            for label in row.get("phase_activity_labels") or []:
                cleaned = _clean(label)
                if cleaned:
                    phase_groups[cleaned].append(trace_id)
            process_counts = row.get("process_family_annotation_counts") or {}
            if isinstance(process_counts, dict):
                for family, count in process_counts.items():
                    cleaned = _clean(family)
                    if cleaned and isinstance(count, (int, float)) and count > 0:
                        process_groups[cleaned].append(trace_id)
            else:
                reviews.append(f"recovery_context_process_counts_invalid:{trace_id}")
        if context_unbound_ids:
            reviews.append("recovery_episode_context_coverage_incomplete")

    phase_context_profiles = _context_profiles(phase_groups, states, "phase_activity_label_candidate")
    process_context_profiles = _context_profiles(process_groups, states, "process_family_annotation_candidate")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS_CANDIDATE")
    construct = None
    if not blocks:
        construct = {
            "construct_candidate_id": f"ryc_{binding[-16:] or 'unbound'}",
            **context,
            "eligible_recovery_trace_candidate_count": denominator,
            "eligible_recovery_trace_candidate_refs": sorted(recovery_ids),
            "evaluable_recovery_consequence_candidate_count": evaluable,
            "recovery_consequence_coverage_rate_candidate": _ratio(evaluable, denominator),
            "visible_same_team_yield_candidate_count": len(positive_refs),
            "visible_adverse_post_recovery_handover_candidate_count": len(adverse_refs),
            "recovery_yield_rate_among_evaluable_candidate": _ratio(len(positive_refs), evaluable),
            "post_recovery_exposure_rate_among_evaluable_candidate": _ratio(len(adverse_refs), evaluable),
            "unresolved_or_missing_consequence_candidate_count": denominator - evaluable,
            "consequence_classification_counts": dict(sorted(counts.items())),
            "support_consequence_candidate_refs": sorted(positive_refs),
            "counterevidence_consequence_candidate_refs": sorted(adverse_refs),
            "unresolved_consequence_candidate_refs": sorted(unresolved_refs),
            "team_recovery_yield_profile_candidates": team_profiles,
            "actor_recovery_yield_profile_candidates": actor_profiles,
            "team_profile_denominator_reconciles_to_construct": sum(
                row["eligible_recovery_trace_candidate_count"] for row in team_profiles
            ) == denominator,
            "actor_profile_denominator_reconciles_to_construct": sum(
                row["eligible_recovery_trace_candidate_count"] for row in actor_profiles
            ) == denominator,
            "episode_context_conditioning_supplied": episode_consequence_payload is not None,
            "episode_context_bound_recovery_trace_candidate_count": len(context_bound_ids),
            "episode_context_unbound_recovery_trace_candidate_count": len(context_unbound_ids),
            "episode_context_binding_coverage_rate_candidate": _ratio(len(context_bound_ids), denominator),
            "episode_context_bound_recovery_trace_candidate_refs": sorted(context_bound_ids),
            "episode_context_unbound_recovery_trace_candidate_refs": sorted(context_unbound_ids),
            "phase_activity_context_recovery_yield_profile_candidates": phase_context_profiles,
            "process_family_context_recovery_yield_profile_candidates": process_context_profiles,
            "context_profile_denominators_are_marginal_not_additive": True,
            "context_annotation_is_recovery_cause_truth": False,
            "phase_context_is_phase_truth": False,
            "process_context_is_tactical_plan_truth": False,
            "episode_binding_is_possession_truth": False,
            "episode_binding_is_sequence_truth": False,
            "alternative_explanations": [
                "visible post-recovery continuation may reflect teammate support and opponent response rather than anchor quality alone",
                "provider recovery/interception coverage may be selective or reflective across surfaces",
                "match-local role, game-state and action mix may alter the recovery opportunity set",
                "episode phase/process annotations are co-visible context candidates, not causes or tactical-plan truth",
                "a visible recovery annotation does not establish possession gain or control truth",
            ],
            "uncertainty": "MATCH_LOCAL_VISIBLE_RECOVERY_CONSEQUENCE_AND_EPISODE_CONTEXT_COVERAGE_ONLY_NO_CALIBRATED_RECOVERY_YIELD_TRUTH",
            "withdrawal_condition": "withdraw comparison or finding if denominator/context alignment, temporal admission, consequence coverage, episode-context binding, identity reconciliation, reflection control, or dependency controls fail",
            "analyst_action": "inspect recovery/interception denominator, positive/adverse/unresolved consequence refs, actor/team reconciliation and marginal episode phase/process context profiles before describing recovery yield",
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_consequence_is_counterevidence": False,
            "missing_episode_context_is_counterevidence": False,
            "recovery_yield_score_emitted": False,
            "construct_validity_truth": False,
            "recovery_quality_truth": False,
            "possession_gain_truth": False,
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
        "recovery_yield_truth": False,
        "possession_gain_truth": False,
        "phase_truth": False,
        "tactical_plan_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
