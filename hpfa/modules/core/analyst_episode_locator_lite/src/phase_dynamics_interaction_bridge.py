from __future__ import annotations

from typing import Any

MODULE_ID = "phase_dynamics_interaction_bridge_v1"
INTERACTION_MODULE_ID = "phase_conditioned_interaction_projection_v1"
DYNAMICS_MODULE_ID = "observed_match_dynamics_projection_v1"
CLAIM_CEILING = "PHASE_DYNAMICS_INTERACTION_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def build_phase_dynamics_interaction_bridge(
    interaction_payload: dict[str, Any],
    dynamics_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    expected = (
        ("interaction", interaction_payload, INTERACTION_MODULE_ID),
        ("dynamics", dynamics_payload, DYNAMICS_MODULE_ID),
    )
    for name, payload, module_id in expected:
        if payload.get("module_id") != module_id:
            blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")

    interactions = interaction_payload.get("interaction_episode_candidates") or []
    dynamics = dynamics_payload.get("observed_match_dynamics_candidates") or []
    if not isinstance(interactions, list) or not isinstance(dynamics, list):
        blocks.append("bridge_inputs_invalid")
        interactions = []
        dynamics = []

    dynamics_by_episode: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(dynamics):
        if not isinstance(row, dict):
            blocks.append(f"dynamics_record_invalid:{position}")
            continue
        episode_id = _clean(row.get("episode_candidate_id"))
        if not episode_id or episode_id in dynamics_by_episode:
            blocks.append(f"dynamics_episode_id_invalid_or_duplicate:{position}")
            continue
        dynamics_by_episode[episode_id] = row

    records: list[dict[str, Any]] = []
    seen_interaction_episode_ids: set[str] = set()
    if not blocks:
        for position, interaction in enumerate(interactions):
            if not isinstance(interaction, dict):
                blocks.append(f"interaction_record_invalid:{position}")
                continue
            episode_id = _clean(interaction.get("episode_candidate_id"))
            if not episode_id or episode_id in seen_interaction_episode_ids:
                blocks.append(f"interaction_episode_id_invalid_or_duplicate:{position}")
                continue
            seen_interaction_episode_ids.add(episode_id)
            dynamics_row = dynamics_by_episode.get(episode_id)
            if dynamics_row is None:
                reviews.append(f"dynamics_missing_for_interaction_episode:{episode_id}")
                dynamics_row = {}

            records.append({
                "phase_dynamics_interaction_candidate_id": f"pdi_{position:04d}",
                "episode_candidate_id": episode_id,
                "interaction_episode_candidate_id": interaction.get("interaction_episode_candidate_id"),
                "phase_state_candidate_id": interaction.get("phase_state_candidate_id"),
                "phase_activity_labels": list(interaction.get("phase_activity_labels") or []),
                "actor_identity_candidate_ids": list(interaction.get("actor_identity_candidate_ids") or []),
                "team_identity_candidate_ids": list(interaction.get("team_identity_candidate_ids") or []),
                "process_family_annotation_counts": dict(interaction.get("process_family_annotation_counts") or {}),
                "activity_rate_per_minute_candidate": dynamics_row.get("activity_rate_per_minute_candidate"),
                "activity_regime_candidate": dynamics_row.get("activity_regime_candidate"),
                "episode_activity_rate_delta_candidate": dynamics_row.get("episode_activity_rate_delta_candidate"),
                "terminal_turnover_recovery_activity_count_candidate": dynamics_row.get("terminal_turnover_recovery_activity_count_candidate"),
                "multi_actor_visible": interaction.get("multi_actor_visible") is True,
                "multi_team_visible": interaction.get("multi_team_visible") is True,
                "provenance_roots": list(interaction.get("provenance_roots") or []),
                "dependency_groups": list(interaction.get("dependency_groups") or []),
                "independence_groups": [],
                "independent_support_vote_count": 0,
                "phase_truth": False,
                "reciprocal_phase_truth": False,
                "interaction_truth": False,
                "tempo_truth": False,
                "momentum_truth": False,
                "control_truth": False,
                "rhythm_truth": False,
                "phase_rupture_truth": False,
                "possession_truth": False,
                "sequence_truth": False,
                "causal_truth": False,
                "tactical_plan_truth": False,
                "absence_is_counterevidence": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    for episode_id in sorted(set(dynamics_by_episode) - seen_interaction_episode_ids):
        reviews.append(f"interaction_missing_for_dynamics_episode:{episode_id}")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "phase_dynamics_interaction_candidates": records if not blocks else [],
        "phase_dynamics_interaction_candidate_count": 0 if blocks else len(records),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "donor_adaptation": {
            "hp_motor_phase_tagger": "ADAPTED_AS_PHASE_ACTIVITY_CONTEXT_ONLY",
            "hp_motor_tempo_moments": "ADAPTED_AS_EPISODE_ACTIVITY_DYNAMICS_ONLY",
            "hp_engine_tempo_momentum": "REHABILITATED_WITHOUT_MOMENTUM_CONTROL_TRUTH",
        },
        "phase_truth": False,
        "reciprocal_phase_truth": False,
        "interaction_truth": False,
        "tempo_truth": False,
        "momentum_truth": False,
        "control_truth": False,
        "rhythm_truth": False,
        "phase_rupture_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "causal_truth": False,
        "tactical_plan_truth": False,
        "absence_is_counterevidence": False,
        "same_provider_support_is_independent_vote": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
