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

    status = "PASS" if profiles and not unresolved_team_labels else (
        "REVIEW_REQUIRED" if profiles else "NOT_AVAILABLE"
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "binding_state": "PLAYER_VISIBLE_PROCESS_PARTICIPATION_BY_SCORE_STATE",
        "profile_count": len(profiles),
        "profiles": profiles,
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
