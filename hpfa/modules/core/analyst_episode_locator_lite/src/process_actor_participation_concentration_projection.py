from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "process_actor_participation_concentration_projection_v1"
UPSTREAM_MODULE_ID = "analyst_episode_process_participation_projection_v1"
CLAIM_CEILING = (
    "OBSERVED_PROCESS_ACTOR_AND_COPARTICIPATION_CONCENTRATION_"
    "WITHIN_DEFINED_PROVIDER_ANNOTATION_UNIVERSE"
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _process_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        _clean(row.get("team_identity_candidate_id")),
        _clean(row.get("process_family_candidate")),
        _clean(row.get("period_candidate")),
        _clean(row.get("start_candidate")),
        _clean(row.get("end_candidate")),
    )


def _process_instance_id(key: tuple[str, str, str, str, str]) -> str:
    raw = json.dumps(key, ensure_ascii=False, separators=(",", ":"))
    return "ppci_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _round(value: float) -> float:
    return round(float(value), 9)


def _distribution_metrics(
    counts: Counter[str],
) -> tuple[dict[str, float], float | None, float | None, float | None]:
    total = sum(counts.values())
    if total <= 0:
        return {}, None, None, None
    shares = {key: value / total for key, value in sorted(counts.items())}
    hhi = sum(value * value for value in shares.values())
    entropy = -sum(value * math.log(value) for value in shares.values() if value > 0)
    effective = math.exp(entropy)
    return (
        {key: _round(value) for key, value in shares.items()},
        _round(hhi),
        _round(entropy),
        _round(effective),
    )


def _fail_closed(hard_blocks: list[str], review_hits: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "process_actor_concentration_profiles": [],
        "process_actor_concentration_profile_count": 0,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "projection_creates_new_evidence": False,
        "projection_reconstructs_processes": False,
        "action_weighted_concentration_produced": False,
        "recipient_relation_used": False,
        "next_passer_receiver_heuristic_used": False,
        "high_actor_concentration_is_player_indispensability_truth": False,
        "low_actor_concentration_is_tactical_flexibility_truth": False,
        "dyad_coparticipation_is_pass_relation_truth": False,
        "process_persistence_or_personnel_effect_claimed": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_process_actor_participation_concentration_projection(
    process_participation_payload: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if process_participation_payload.get("module_id") != UPSTREAM_MODULE_ID:
        hard_blocks.append("process_participation_module_id_mismatch")
    if process_participation_payload.get("status") == "FAIL_CLOSED":
        hard_blocks.append("process_participation_upstream_fail_closed")
    if process_participation_payload.get("canonical_event_count") != "UNKNOWN":
        hard_blocks.append("canonical_event_count_claimed")
    if process_participation_payload.get("true_action_count") != "UNKNOWN":
        hard_blocks.append("true_action_count_claimed")
    if process_participation_payload.get("production_release") is True:
        hard_blocks.append("production_release_claimed")
    if process_participation_payload.get("annotation_count_is_action_count") is not False:
        hard_blocks.append("annotation_count_action_count_lock_missing")
    if process_participation_payload.get("annotation_count_is_independent_support_count") is not False:
        hard_blocks.append("annotation_independence_lock_missing")
    if process_participation_payload.get("reflection_adds_independent_vote") is not False:
        hard_blocks.append("reflection_independence_lock_missing")
    if process_participation_payload.get("absence_is_counterevidence") is not False:
        hard_blocks.append("absence_counterevidence_lock_missing")

    rows = process_participation_payload.get("process_participation_candidates")
    if not isinstance(rows, list):
        hard_blocks.append("process_participation_candidates_invalid")
        rows = []
    if process_participation_payload.get("process_participation_candidate_count") != len(rows):
        hard_blocks.append("process_participation_candidate_count_mismatch")

    if hard_blocks:
        return _fail_closed(hard_blocks, review_hits)

    contexts_by_key: dict[
        tuple[str, str, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    participation_by_key: dict[
        tuple[str, str, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)

    invalid_row_count = 0
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            invalid_row_count += 1
            review_hits.append(f"process_participation_record_invalid:{position}")
            continue
        role = _clean(row.get("semantic_role"))
        key = _process_key(row)
        if not all(key):
            review_hits.append(
                "process_interval_signature_incomplete:"
                + (_clean(row.get("process_participation_candidate_id")) or str(position))
            )
            continue
        if role == "CONTEXT_INTERVAL":
            contexts_by_key[key].append(row)
        elif role == "PARTICIPATION_INTERVAL":
            actor_id = _clean(row.get("actor_identity_candidate_id"))
            if not actor_id:
                review_hits.append(
                    "participation_actor_missing:"
                    + (_clean(row.get("process_participation_candidate_id")) or str(position))
                )
                continue
            participation_by_key[key].append(row)

    context_keys = set(contexts_by_key)
    participation_keys = set(participation_by_key)
    participant_only_keys = sorted(participation_keys - context_keys)
    context_only_keys = sorted(context_keys - participation_keys)

    if participant_only_keys:
        review_hits.append("participation_intervals_without_matching_context_interval")
    if context_only_keys:
        review_hits.append("context_intervals_without_actor_participation_observation")

    duplicate_context_annotation_count = sum(
        max(0, len(rows_for_key) - 1) for rows_for_key in contexts_by_key.values()
    )

    duplicate_actor_annotation_within_process_suppressed = 0
    family_keys: dict[
        tuple[str, str], list[tuple[str, str, str, str, str]]
    ] = defaultdict(list)
    process_actor_sets: dict[tuple[str, str, str, str, str], set[str]] = {}
    process_participation_ids: dict[
        tuple[str, str, str, str, str], list[str]
    ] = {}
    process_dependency_states: dict[
        tuple[str, str, str, str, str], list[str]
    ] = {}

    for key in sorted(context_keys):
        team_id, process_family, _, _, _ = key
        family_keys[(team_id, process_family)].append(key)
        participant_rows = participation_by_key.get(key) or []
        actor_ids = [
            _clean(row.get("actor_identity_candidate_id")) for row in participant_rows
        ]
        actor_ids = [value for value in actor_ids if value]
        unique_actor_ids = set(actor_ids)
        duplicate_actor_annotation_within_process_suppressed += max(
            0, len(actor_ids) - len(unique_actor_ids)
        )
        process_actor_sets[key] = unique_actor_ids
        process_participation_ids[key] = sorted(
            {
                _clean(row.get("process_participation_candidate_id"))
                for row in participant_rows
                if _clean(row.get("process_participation_candidate_id"))
            }
        )
        process_dependency_states[key] = [
            _clean(row.get("reflection_dependency_state")) or "UNKNOWN"
            for row in participant_rows
        ]

    profiles: list[dict[str, Any]] = []
    for (team_id, process_family), keys in sorted(family_keys.items()):
        actor_observable_keys = [key for key in keys if process_actor_sets.get(key)]
        actor_counts: Counter[str] = Counter()
        dyad_counts: Counter[str] = Counter()
        dependency_states: Counter[str] = Counter()
        support_process_ids: list[str] = []
        support_participation_ids: list[str] = []

        for key in actor_observable_keys:
            actors = sorted(process_actor_sets[key])
            actor_counts.update(actors)
            support_process_ids.append(_process_instance_id(key))
            support_participation_ids.extend(process_participation_ids.get(key) or [])
            dependency_states.update(process_dependency_states.get(key) or [])
            for index, actor_a in enumerate(actors):
                for actor_b in actors[index + 1 :]:
                    dyad_counts[f"{actor_a}|{actor_b}"] += 1

        actor_observable_count = len(actor_observable_keys)
        eligible_context_count = len(keys)
        actor_incidence_count = sum(actor_counts.values())
        dyad_incidence_count = sum(dyad_counts.values())

        actor_shares, actor_hhi, actor_entropy, effective_actor_count = (
            _distribution_metrics(actor_counts)
        )
        dyad_shares, dyad_hhi, dyad_entropy, effective_dyad_count = (
            _distribution_metrics(dyad_counts)
        )

        actor_presence_rates = (
            {
                actor: _round(count / actor_observable_count)
                for actor, count in sorted(actor_counts.items())
            }
            if actor_observable_count
            else {}
        )
        dyad_presence_rates = (
            {
                dyad: _round(count / actor_observable_count)
                for dyad, count in sorted(dyad_counts.items())
            }
            if actor_observable_count
            else {}
        )

        ranked_actors = sorted(
            actor_counts.items(), key=lambda item: (-item[1], item[0])
        )
        ranked_dyads = sorted(
            dyad_counts.items(), key=lambda item: (-item[1], item[0])
        )
        top_actor_id = ranked_actors[0][0] if ranked_actors else None
        top_dyad_id = ranked_dyads[0][0] if ranked_dyads else None
        top_two_actors = [actor for actor, _ in ranked_actors[:2]]

        profiles.append(
            {
                "team_identity_candidate_id": team_id,
                "process_family_candidate": process_family,
                "process_instance_identity_basis": (
                    "EXACT_PROVIDER_REVIEWED_CONTEXT_INTERVAL_SIGNATURE:"
                    "team+process_family+period+start+end"
                ),
                "eligible_context_process_count": eligible_context_count,
                "actor_observable_process_count": actor_observable_count,
                "actor_participation_observation_missing_process_count": (
                    eligible_context_count - actor_observable_count
                ),
                "actor_observation_coverage_numerator": actor_observable_count,
                "actor_observation_coverage_denominator": eligible_context_count,
                "actor_observation_coverage_rate": (
                    _round(actor_observable_count / eligible_context_count)
                    if eligible_context_count
                    else None
                ),
                "actor_participation_definition": (
                    "ONE_ACTOR_ONE_VOTE_PER_PROCESS_INSTANCE"
                ),
                "action_weighted_concentration_produced": False,
                "actor_process_participation_incidence_count": actor_incidence_count,
                "unique_actor_count": len(actor_counts),
                "actor_process_counts": dict(sorted(actor_counts.items())),
                "actor_process_presence_rates": actor_presence_rates,
                "actor_participation_shares": actor_shares,
                "top1_actor_identity_candidate_id": top_actor_id,
                "top1_actor_process_presence_rate": (
                    actor_presence_rates.get(top_actor_id) if top_actor_id else None
                ),
                "top1_actor_participation_share": (
                    actor_shares.get(top_actor_id) if top_actor_id else None
                ),
                "top2_actor_identity_candidate_ids": top_two_actors,
                "top2_actor_combined_participation_share": (
                    _round(
                        sum(actor_shares.get(actor, 0.0) for actor in top_two_actors)
                    )
                    if top_two_actors
                    else None
                ),
                "actor_hhi": actor_hhi,
                "actor_entropy": actor_entropy,
                "effective_actor_count": effective_actor_count,
                "dyad_semantics": (
                    "UNDIRECTED_ACTOR_CO_PARTICIPATION_WITHIN_SAME_"
                    "ADMITTED_PROCESS_INSTANCE"
                ),
                "dyad_is_pass_relation_truth": False,
                "recipient_relation_used": False,
                "next_passer_receiver_heuristic_used": False,
                "dyad_process_coparticipation_incidence_count": dyad_incidence_count,
                "unique_dyad_count": len(dyad_counts),
                "dyad_process_counts": dict(sorted(dyad_counts.items())),
                "dyad_process_presence_rates": dyad_presence_rates,
                "dyad_participation_shares": dyad_shares,
                "top_dyad_actor_pair": (
                    top_dyad_id.split("|") if top_dyad_id else []
                ),
                "top_dyad_process_presence_rate": (
                    dyad_presence_rates.get(top_dyad_id) if top_dyad_id else None
                ),
                "top_dyad_participation_share": (
                    dyad_shares.get(top_dyad_id) if top_dyad_id else None
                ),
                "dyad_hhi": dyad_hhi,
                "dyad_entropy": dyad_entropy,
                "effective_dyad_count": effective_dyad_count,
                "reflection_dependency_state_counts": dict(
                    sorted(dependency_states.items())
                ),
                "sample_support_state": (
                    "DESCRIPTIVE_PROCESS_UNIVERSE_ONLY_INDEPENDENCE_UNPROVEN"
                    if actor_observable_count
                    else "NO_ACTOR_OBSERVABLE_PROCESS_INSTANCE"
                ),
                "independent_support_vote_count": 0,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
                "supporting_process_instance_ids": sorted(support_process_ids),
                "supporting_process_participation_candidate_ids": sorted(
                    set(support_participation_ids)
                ),
                "profile_definition_uses_terminal_outcome": False,
                "process_instance_is_physical_possession_truth": False,
                "process_instance_count_is_true_process_count": False,
                "high_actor_concentration_is_player_indispensability_truth": False,
                "low_actor_concentration_is_tactical_flexibility_truth": False,
                "same_process_different_actor_set_is_functional_equivalence_truth": False,
                "process_family_is_tactical_plan_truth": False,
                "process_family_is_coach_intention_truth": False,
                "absence_is_counterevidence": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    if process_participation_payload.get("status") == "REVIEW_REQUIRED":
        review_hits.append("upstream_process_participation_review_required")
    if invalid_row_count:
        review_hits.append("invalid_process_participation_records_present")

    status = "REVIEW_REQUIRED" if review_hits else "PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "process_actor_concentration_profiles": profiles,
        "process_actor_concentration_profile_count": len(profiles),
        "eligible_context_process_instance_count": len(context_keys),
        "actor_observable_process_instance_count": sum(
            1 for key in context_keys if process_actor_sets.get(key)
        ),
        "participant_only_process_signature_count": len(participant_only_keys),
        "context_only_process_signature_count": len(context_only_keys),
        "duplicate_context_annotation_count_suppressed": (
            duplicate_context_annotation_count
        ),
        "duplicate_actor_annotation_within_process_suppressed": (
            duplicate_actor_annotation_within_process_suppressed
        ),
        "process_instance_identity_basis": (
            "EXACT_PROVIDER_REVIEWED_CONTEXT_INTERVAL_SIGNATURE:"
            "team+process_family+period+start+end"
        ),
        "process_instance_identity_is_physical_possession_truth": False,
        "projection_creates_new_evidence": False,
        "projection_reconstructs_processes": False,
        "action_weighted_concentration_produced": False,
        "recipient_relation_used": False,
        "next_passer_receiver_heuristic_used": False,
        "high_actor_concentration_is_player_indispensability_truth": False,
        "low_actor_concentration_is_tactical_flexibility_truth": False,
        "dyad_coparticipation_is_pass_relation_truth": False,
        "process_persistence_or_personnel_effect_claimed": False,
        "same_process_different_actor_set_is_functional_equivalence_truth": False,
        "selected_process_universe_is_whole_match_attacking_game": False,
        "independent_support_vote_count": 0,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
        "absence_is_counterevidence": False,
        "hard_block_hits": [],
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
