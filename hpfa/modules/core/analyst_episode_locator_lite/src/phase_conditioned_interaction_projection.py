from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "phase_conditioned_interaction_projection_v1"
PROCESS_MODULE_ID = "analyst_episode_process_participation_projection_v1"
EPISODE_MODULE_ID = "analyst_episode_locator_lite_v1"
RICH_MODULE_ID = "rich_multiformat_analysis_lattice_v1"
CLAIM_CEILING = "PHASE_CONDITIONED_INTERACTION_EPISODE_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _episode_position_index(episode_payload: dict[str, Any]) -> tuple[dict[str, int], list[str]]:
    blocks: list[str] = []
    index: dict[str, int] = {}
    episodes = episode_payload.get("episode_candidates") or []
    if not isinstance(episodes, list):
        return {}, ["episode_candidates_invalid"]
    for position, episode in enumerate(episodes):
        if not isinstance(episode, dict):
            blocks.append(f"episode_record_invalid:{position}")
            continue
        episode_id = _clean(episode.get("episode_candidate_id"))
        if not episode_id or episode_id in index:
            blocks.append(f"episode_id_invalid_or_duplicate:{position}")
            continue
        index[episode_id] = position
    return index, blocks


def _phase_index(rich_payload: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], list[str]]:
    blocks: list[str] = []
    index: dict[int, dict[str, Any]] = {}
    rows = rich_payload.get("phase_state_candidates") or []
    if not isinstance(rows, list):
        return {}, ["phase_state_candidates_invalid"]
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"phase_state_candidate_invalid:{position}")
            continue
        episode_index = row.get("episode_index")
        if not isinstance(episode_index, int) or episode_index < 0 or episode_index in index:
            blocks.append(f"phase_episode_index_invalid_or_duplicate:{position}")
            continue
        index[episode_index] = row
    return index, blocks


def build_phase_conditioned_interactions(
    process_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    rich_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if process_payload.get("module_id") != PROCESS_MODULE_ID:
        blocks.append("process_module_id_mismatch")
    if episode_payload.get("module_id") != EPISODE_MODULE_ID:
        blocks.append("episode_module_id_mismatch")
    if rich_payload.get("module_id") != RICH_MODULE_ID:
        blocks.append("rich_module_id_mismatch")

    for name, payload in (
        ("process", process_payload),
        ("episode", episode_payload),
        ("rich", rich_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")

    episode_position, episode_blocks = _episode_position_index(episode_payload)
    phase_by_position, phase_blocks = _phase_index(rich_payload)
    blocks.extend(episode_blocks)
    blocks.extend(phase_blocks)

    process_rows = process_payload.get("process_participation_candidates") or []
    if not isinstance(process_rows, list):
        blocks.append("process_participation_candidates_invalid")
        process_rows = []

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not blocks:
        for position, row in enumerate(process_rows):
            if not isinstance(row, dict):
                blocks.append(f"process_participation_candidate_invalid:{position}")
                continue
            episode_id = _clean(row.get("episode_candidate_id"))
            if not episode_id:
                reviews.append(f"process_candidate_without_episode:{position}")
                continue
            if episode_id not in episode_position:
                blocks.append(f"process_episode_reference_unknown:{episode_id}")
                continue
            grouped[episode_id].append(row)

    records: list[dict[str, Any]] = []
    if not blocks:
        for episode_id, rows in sorted(grouped.items(), key=lambda item: episode_position[item[0]]):
            position = episode_position[episode_id]
            phase = phase_by_position.get(position)
            if not phase:
                reviews.append(f"phase_state_missing_for_episode:{episode_id}")
                phase_labels: list[str] = []
                phase_state_candidate_id = None
            else:
                labels = phase.get("labels") or []
                phase_labels = sorted({_clean(label) for label in labels if _clean(label)})
                phase_state_candidate_id = phase.get("phase_state_candidate_id")

            actor_ids = sorted({
                _clean(row.get("actor_identity_candidate_id"))
                for row in rows
                if _clean(row.get("actor_identity_candidate_id"))
            })
            team_ids = sorted({
                _clean(row.get("team_identity_candidate_id"))
                for row in rows
                if _clean(row.get("team_identity_candidate_id"))
            })
            family_counts = Counter(
                _clean(row.get("process_family_candidate"))
                for row in rows
                if _clean(row.get("process_family_candidate"))
            )
            shot_family_counts = Counter(
                _clean(row.get("process_family_candidate"))
                for row in rows
                if row.get("shot_present_annotation_candidate") is True
                and _clean(row.get("process_family_candidate"))
            )
            dependency_groups = sorted({
                _clean(row.get("dependency_group"))
                for row in rows
                if _clean(row.get("dependency_group"))
            })
            provenance_roots = sorted({
                _clean(row.get("provenance_root"))
                for row in rows
                if _clean(row.get("provenance_root"))
            })

            records.append({
                "interaction_episode_candidate_id": f"iec_{position:04d}",
                "episode_candidate_id": episode_id,
                "phase_state_candidate_id": phase_state_candidate_id,
                "phase_activity_labels": phase_labels,
                "actor_identity_candidate_ids": actor_ids,
                "team_identity_candidate_ids": team_ids,
                "process_family_annotation_counts": dict(sorted(family_counts.items())),
                "shot_present_process_family_annotation_counts": dict(sorted(shot_family_counts.items())),
                "participant_annotation_count": len(rows),
                "multi_actor_visible": len(actor_ids) > 1,
                "multi_team_visible": len(team_ids) > 1,
                "provenance_roots": provenance_roots,
                "dependency_groups": dependency_groups,
                "independence_groups": [],
                "independent_support_vote_count": 0,
                "phase_truth": False,
                "reciprocal_phase_truth": False,
                "interaction_truth": False,
                "possession_truth": False,
                "sequence_truth": False,
                "causal_truth": False,
                "tactical_plan_truth": False,
                "absence_is_counterevidence": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "interaction_episode_candidates": records,
        "interaction_episode_candidate_count": len(records),
        "multi_actor_episode_candidate_count": sum(1 for row in records if row["multi_actor_visible"]),
        "multi_team_episode_candidate_count": sum(1 for row in records if row["multi_team_visible"]),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "phase_truth": False,
        "reciprocal_phase_truth": False,
        "interaction_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "causal_truth": False,
        "tactical_plan_truth": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
