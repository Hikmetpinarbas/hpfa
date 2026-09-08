from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "episode_consequence_projection_v1"
EPISODE_MODULE_ID = "analyst_episode_locator_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
INTERACTION_MODULE_ID = "phase_conditioned_interaction_projection_v1"
CLAIM_CEILING = "EPISODE_VISIBLE_CONSEQUENCE_ASSOCIATION_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _episode_windows(episode_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[str] = []
    windows: list[dict[str, Any]] = []
    rows = episode_payload.get("episode_candidates") or []
    if not isinstance(rows, list):
        return [], ["episode_candidates_invalid"]
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"episode_record_invalid:{position}")
            continue
        episode_id = _clean(row.get("episode_candidate_id"))
        period = _clean(row.get("period_candidate"))
        start = _number(row.get("start_second_candidate"))
        end = _number(row.get("end_second_candidate"))
        if not episode_id or not period or start is None or end is None or end < start:
            blocks.append(f"episode_window_invalid:{position}")
            continue
        windows.append({
            "episode_candidate_id": episode_id,
            "period_candidate": period,
            "start_second_candidate": start,
            "end_second_candidate": end,
        })
    return windows, blocks


def _trace_index(trace_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blocks: list[str] = []
    index: dict[str, dict[str, Any]] = {}
    rows = trace_payload.get("trackable_action_trace_candidates") or []
    if not isinstance(rows, list):
        return {}, ["trackable_action_trace_candidates_invalid"]
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"trace_record_invalid:{position}")
            continue
        trace_id = _clean(row.get("trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in index:
            blocks.append(f"trace_id_invalid_or_duplicate:{position}")
            continue
        index[trace_id] = row
    return index, blocks


def _interaction_index(interaction_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blocks: list[str] = []
    index: dict[str, dict[str, Any]] = {}
    rows = interaction_payload.get("interaction_episode_candidates") or []
    if not isinstance(rows, list):
        return {}, ["interaction_episode_candidates_invalid"]
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"interaction_record_invalid:{position}")
            continue
        episode_id = _clean(row.get("episode_candidate_id"))
        if not episode_id or episode_id in index:
            blocks.append(f"interaction_episode_id_invalid_or_duplicate:{position}")
            continue
        index[episode_id] = row
    return index, blocks


def _matching_episode_ids(trace: dict[str, Any], windows: list[dict[str, Any]]) -> list[str]:
    period = _clean(trace.get("period_candidate"))
    start = _number(trace.get("start_candidate"))
    end = _number(trace.get("end_candidate"))
    if not period or start is None or end is None or end < start:
        return []
    matches: list[str] = []
    for window in windows:
        if window["period_candidate"] != period:
            continue
        if end < window["start_second_candidate"] or start > window["end_second_candidate"]:
            continue
        matches.append(window["episode_candidate_id"])
    return sorted(set(matches))


def build_episode_consequence_projection(
    episode_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    interaction_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    expected = (
        ("episode", episode_payload, EPISODE_MODULE_ID),
        ("trace", trace_payload, TRACE_MODULE_ID),
        ("consequence", consequence_payload, CONSEQUENCE_MODULE_ID),
        ("interaction", interaction_payload, INTERACTION_MODULE_ID),
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

    episode_windows, episode_blocks = _episode_windows(episode_payload)
    trace_by_id, trace_blocks = _trace_index(trace_payload)
    interaction_by_episode, interaction_blocks = _interaction_index(interaction_payload)
    blocks.extend(episode_blocks)
    blocks.extend(trace_blocks)
    blocks.extend(interaction_blocks)

    consequence_rows = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(consequence_rows, list):
        blocks.append("trackable_action_consequence_candidates_invalid")
        consequence_rows = []

    records: list[dict[str, Any]] = []
    seen_anchor_ids: set[str] = set()
    if not blocks:
        for position, row in enumerate(consequence_rows):
            if not isinstance(row, dict):
                blocks.append(f"consequence_record_invalid:{position}")
                continue
            anchor_id = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
            consequence_id = _clean(row.get("trackable_action_consequence_candidate_id"))
            if not anchor_id or anchor_id in seen_anchor_ids:
                blocks.append(f"consequence_anchor_invalid_or_duplicate:{position}")
                continue
            seen_anchor_ids.add(anchor_id)
            trace = trace_by_id.get(anchor_id)
            if trace is None:
                blocks.append(f"consequence_anchor_trace_unknown:{anchor_id}")
                continue

            episode_ids = _matching_episode_ids(trace, episode_windows)
            if len(episode_ids) == 1:
                episode_id = episode_ids[0]
                binding_state = "SINGLE_EPISODE_NAVIGATION_ASSOCIATION"
            elif not episode_ids:
                episode_id = None
                binding_state = "UNBOUND_REVIEW_REQUIRED"
                reviews.append(f"consequence_episode_binding_missing:{anchor_id}")
            else:
                episode_id = None
                binding_state = "AMBIGUOUS_EPISODE_REVIEW_REQUIRED"
                reviews.append(f"consequence_episode_binding_ambiguous:{anchor_id}")

            interaction = interaction_by_episode.get(episode_id or "", {})
            if episode_id and not interaction:
                reviews.append(f"interaction_missing_for_consequence_episode:{episode_id}")

            records.append({
                "episode_consequence_candidate_id": f"ecp_{position:05d}",
                "trackable_action_consequence_candidate_id": consequence_id or None,
                "anchor_trackable_action_trace_candidate_id": anchor_id,
                "episode_candidate_id": episode_id,
                "episode_binding_state": binding_state,
                "interaction_episode_candidate_id": interaction.get("interaction_episode_candidate_id"),
                "team_identity_candidate_id": trace.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": trace.get("actor_identity_candidate_id"),
                "source_role": trace.get("source_role"),
                "action_family_candidates": list(trace.get("action_family_candidates") or []),
                "primary_consequence_candidate": row.get("primary_consequence_candidate"),
                "consequence_record_status": row.get("record_status"),
                "terminal_outcome_support_visible": row.get("terminal_outcome_support_visible") is True,
                "phase_activity_labels": list(interaction.get("phase_activity_labels") or []),
                "process_family_annotation_counts": dict(interaction.get("process_family_annotation_counts") or {}),
                "episode_binding_is_possession_truth": False,
                "episode_binding_is_sequence_truth": False,
                "consequence_candidate_is_causal_truth": False,
                "phase_truth": False,
                "reciprocal_phase_truth": False,
                "interaction_truth": False,
                "absence_is_counterevidence": False,
                "independent_support_vote_count": 0,
                "claim_ceiling": CLAIM_CEILING,
            })

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    visible_records = records if not blocks else []
    bound = [row for row in visible_records if row["episode_candidate_id"]]
    by_episode: dict[str, Counter[str]] = defaultdict(Counter)
    by_actor: dict[str, Counter[str]] = defaultdict(Counter)
    by_team: dict[str, Counter[str]] = defaultdict(Counter)
    for row in bound:
        consequence = _clean(row.get("primary_consequence_candidate")) or "UNKNOWN_CONSEQUENCE_CANDIDATE"
        by_episode[_clean(row.get("episode_candidate_id"))][consequence] += 1
        actor = _clean(row.get("actor_identity_candidate_id"))
        team = _clean(row.get("team_identity_candidate_id"))
        if actor:
            by_actor[actor][consequence] += 1
        if team:
            by_team[team][consequence] += 1

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "episode_consequence_candidates": visible_records,
        "episode_consequence_candidate_count": len(visible_records),
        "bound_episode_consequence_candidate_count": len(bound),
        "unbound_or_ambiguous_episode_consequence_candidate_count": len(visible_records) - len(bound),
        "episode_primary_consequence_candidate_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(by_episode.items())
        },
        "actor_primary_consequence_candidate_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(by_actor.items())
        },
        "team_primary_consequence_candidate_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(by_team.items())
        },
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "episode_binding_is_possession_truth": False,
        "episode_binding_is_sequence_truth": False,
        "consequence_candidate_is_causal_truth": False,
        "phase_truth": False,
        "reciprocal_phase_truth": False,
        "interaction_truth": False,
        "absence_is_counterevidence": False,
        "same_provider_support_is_independent_vote": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
