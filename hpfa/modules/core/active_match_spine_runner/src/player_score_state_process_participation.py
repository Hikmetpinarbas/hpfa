from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


MODULE_ID = "player_score_state_process_participation_v1"
CLAIM_CEILING = "MATCH_LOCAL_PLAYER_SCORE_STATE_VISIBLE_PROCESS_PARTICIPATION_COUNTS_ONLY"


def _float_candidate(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_identity_text(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _process_key(row: dict[str, Any]) -> tuple[str, str, str, float, float] | None:
    team_id = str(row.get("team_identity_candidate_id") or "").strip()
    family = str(row.get("process_family_candidate") or "").strip()
    period = str(row.get("period_candidate") or "").strip() or "UNKNOWN"
    start = _float_candidate(row.get("start_candidate"))
    end = _float_candidate(row.get("end_candidate"))
    if not team_id or not family or start is None or end is None or end < start:
        return None
    return (team_id, family, period, start, end)


def build_player_score_state_process_participation(
    game_state_context: dict[str, Any],
    identity_payload: dict[str, Any],
    process_participation_payload: dict[str, Any],
) -> dict[str, Any]:
    """Count visible player process participation inside visible score-state segments.

    Counts are participation traces only. Team score-state duration is retained as
    team context and is never promoted to player exposure. No per-10/per-90 player
    rates are emitted without separately admitted on-pitch exposure.
    """
    alias_to_team_id: dict[str, str] = {}
    for row in identity_payload.get("team_identity_candidates", []) or []:
        if not isinstance(row, dict):
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if not team_id:
            continue
        for alias in row.get("team_aliases_raw", []) or []:
            key = _normalize_identity_text(alias)
            if key:
                alias_to_team_id[key] = team_id

    raw = [
        row
        for row in (process_participation_payload.get("process_participation_candidates") or [])
        if isinstance(row, dict)
    ]

    contexts: dict[tuple[str, str, str, float, float], dict[str, Any]] = {}
    participants: dict[tuple[str, str, str, float, float], set[str]] = defaultdict(set)
    for row in raw:
        key = _process_key(row)
        if key is None:
            continue
        role = str(row.get("semantic_role") or "")
        if role == "CONTEXT_INTERVAL":
            existing = contexts.get(key)
            if existing is None or (
                existing.get("shot_present_annotation_candidate") is not True
                and row.get("shot_present_annotation_candidate") is True
            ):
                contexts[key] = row
        elif role == "PARTICIPATION_INTERVAL":
            actor_id = str(row.get("actor_identity_candidate_id") or "").strip()
            if actor_id:
                participants[key].add(actor_id)

    actor_labels: dict[str, str] = {}
    for row in identity_payload.get("actor_identity_candidates", []) or []:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_identity_candidate_id") or "").strip()
        if not actor_id:
            continue
        aliases = [
            str(value).strip()
            for value in (row.get("actor_aliases_raw") or [])
            if str(value).strip()
        ]
        actor_labels[actor_id] = aliases[0] if aliases else actor_id

    profile_index: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved_team_labels: set[str] = set()
    process_without_participant_n = 0

    for segment in game_state_context.get("score_state_segments", []) or []:
        if not isinstance(segment, dict):
            continue
        start = _float_candidate(segment.get("start_second_candidate"))
        end = _float_candidate(segment.get("end_second_candidate"))
        if start is None or end is None or end < start:
            continue
        score_state = segment.get("score_state_candidate") or {}

        for team_label in score_state:
            team_id = alias_to_team_id.get(_normalize_identity_text(team_label))
            if not team_id:
                unresolved_team_labels.add(str(team_label))
                continue

            for key, context in contexts.items():
                context_team_id, family, _, process_start, _ = key
                if context_team_id != team_id:
                    continue
                if not (start <= process_start < end or (start == end and process_start == start)):
                    continue

                actor_ids = sorted(participants.get(key, set()))
                if not actor_ids:
                    process_without_participant_n += 1
                    continue

                shot = context.get("shot_present_annotation_candidate") is True
                for actor_id in actor_ids:
                    score_key = repr(sorted((str(k), int(v)) for k, v in score_state.items()))
                    profile_key = (actor_id, score_key)
                    profile = profile_index.setdefault(
                        profile_key,
                        {
                            "actor_identity_candidate_id": actor_id,
                            "actor_label_candidate": actor_labels.get(actor_id, actor_id),
                            "team_identity_candidate_id": team_id,
                            "team_label": team_label,
                            "score_state_candidate": dict(score_state),
                            "score_segment_start_second_candidate": start,
                            "score_segment_end_second_candidate": end,
                            "team_score_state_duration_second_candidate": max(0.0, end - start),
                            "visible_process_participation_n": 0,
                            "shot_ending_process_participation_n": 0,
                            "process_family_counts": Counter(),
                        },
                    )
                    profile["visible_process_participation_n"] += 1
                    if shot:
                        profile["shot_ending_process_participation_n"] += 1
                    profile["process_family_counts"][family] += 1

    profiles: list[dict[str, Any]] = []
    for profile in profile_index.values():
        counts = profile.pop("process_family_counts")
        profile["process_family_counts"] = dict(sorted(counts.items()))
        profile["player_exposure_admitted"] = False
        profile["player_rate_output_allowed"] = False
        profile["team_score_state_duration_is_player_exposure"] = False
        profile["visible_participation_is_causal_credit"] = False
        profile["visible_participation_is_tactical_role_truth"] = False
        profile["zero_participation_is_non_participation_truth"] = False
        profile["creates_independent_support"] = False
        profile["claim_ceiling"] = CLAIM_CEILING
        profiles.append(profile)

    profiles.sort(
        key=lambda row: (
            str(row.get("team_identity_candidate_id") or ""),
            float(row.get("score_segment_start_second_candidate") or 0.0),
            -int(row.get("visible_process_participation_n") or 0),
            str(row.get("actor_label_candidate") or ""),
        )
    )

    profiles_by_actor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in profiles:
        actor_id = str(profile.get("actor_identity_candidate_id") or "").strip()
        if actor_id:
            profiles_by_actor[actor_id].append(profile)

    function_hypothesis_review_candidates: list[dict[str, Any]] = []
    for actor_id, actor_profiles in sorted(profiles_by_actor.items()):
        score_state_keys = {
            repr(sorted((str(k), int(v)) for k, v in (row.get("score_state_candidate") or {}).items()))
            for row in actor_profiles
            if row.get("score_state_candidate")
        }
        family_signatures = [
            tuple(
                sorted(
                    (str(family), int(count or 0))
                    for family, count in (row.get("process_family_counts") or {}).items()
                    if int(count or 0) > 0
                )
            )
            for row in actor_profiles
        ]
        observed_families = sorted({family for values in family_signatures for family, _ in values})
        process_mix_varies = len(score_state_keys) >= 2 and len(set(family_signatures)) >= 2
        review_state = (
            "MATCH_LOCAL_FUNCTION_CONTEXT_VARIATION_REVIEW_CANDIDATE"
            if process_mix_varies
            else "INSUFFICIENT_MULTI_CONTEXT_VARIATION_FOR_REVIEW"
        )
        function_hypothesis_review_candidates.append({
            "actor_identity_candidate_id": actor_id,
            "actor_label_candidate": actor_profiles[0].get("actor_label_candidate"),
            "team_identity_candidate_id": actor_profiles[0].get("team_identity_candidate_id"),
            "observed_score_state_context_n": len(score_state_keys),
            "observed_process_family_n": len(observed_families),
            "observed_process_family_candidates": observed_families,
            "process_mix_varies_across_observed_score_states": process_mix_varies,
            "review_state": review_state,
            "creates_new_evidence": False,
            "can_authorize_emit": False,
            "can_authorize_player_value_claim": False,
            "stable_role_truth": False,
            "causal_contribution_truth": False,
            "off_ball_role_truth": False,
            "player_quality_truth": False,
            "counter_scenario_candidates": [
                "PLAYER_EXPOSURE_DIFFERS_ACROSS_SCORE_STATES_AND_IS_NOT_ADMITTED_HERE",
                "TEAM_PROCESS_OPPORTUNITY_MIX_MAY_DIFFER_ACROSS_SCORE_STATES",
                "OPPONENT_OR_MATCH_CONTEXT_MAY_ACCOUNT_FOR_VISIBLE_PROCESS_MIX_DIFFERENCE",
                "SHARED_PROCESS_DEPENDENCE_MAY_REDUCE_EFFECTIVE_SUPPORT",
            ],
            "hypothesis_target": "VISIBLE_PROCESS_FAMILY_COMPOSITION_VARIES_ACROSS_OBSERVED_SCORE_STATES",
            "hypothesis_falsifier_conditions": [
                "ELIGIBLE_CONTEXT_REVIEW_SHOWS_COMPARABLE_VISIBLE_PROCESS_MIX_ACROSS_SCORE_STATES",
            ],
            "invalidation_conditions": [
                "ACTOR_IDENTITY_BINDING_INVALIDATED",
                "SCORE_STATE_BINDING_INVALIDATED",
                "PROCESS_FAMILY_SEMANTIC_BINDING_INVALIDATED",
            ],
            "falsifier_is_invalidator": False,
            "absence_is_falsifier": False,
            "withdrawal_conditions": [
                "FEWER_THAN_TWO_ADMITTED_SCORE_STATE_CONTEXTS_REMAIN",
                "PLAYER_EXPOSURE_IS_REQUIRED_FOR_RATE_INTERPRETATION",
                "PROCESS_PARTICIPATION_BINDING_IS_INVALIDATED",
                "COMPARABLE_CONTEXT_REVIEW_REMOVES_VISIBLE_FUNCTION_DIFFERENCE",
            ],
            "analyst_action": (
                "Compare the actor's visible process-family participation across admitted score-state contexts, "
                "then inspect opportunity mix, consequence context, dependency and exposure limitations before any "
                "player-value, stable-role, off-ball or causal interpretation."
            ),
            "claim_ceiling": "MATCH_LOCAL_CONTEXT_CONDITIONED_PLAYER_FUNCTION_REVIEW_CANDIDATE_ONLY",
        })

    status = "PASS" if profiles and not unresolved_team_labels else (
        "REVIEW_REQUIRED" if profiles else "NOT_AVAILABLE"
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "binding_state": "PLAYER_VISIBLE_PROCESS_PARTICIPATION_BY_SCORE_STATE",
        "profile_count": len(profiles),
        "profiles": profiles,
        "function_hypothesis_review_candidate_count": len(function_hypothesis_review_candidates),
        "function_hypothesis_review_candidates": function_hypothesis_review_candidates,
        "unresolved_team_labels": sorted(unresolved_team_labels),
        "process_without_visible_participant_n": process_without_participant_n,
        "hard_block_hits": [],
        "review_hits": (
            ["score_state_team_identity_unresolved"]
            if unresolved_team_labels
            else []
        ),
        "claim_ceiling": CLAIM_CEILING,
        "player_exposure_admitted": False,
        "player_rate_output_allowed": False,
        "team_score_state_duration_is_player_exposure": False,
        "visible_participation_is_causal_credit": False,
        "visible_participation_is_tactical_role_truth": False,
        "zero_participation_is_non_participation_truth": False,
        "creates_independent_support": False,
    }
