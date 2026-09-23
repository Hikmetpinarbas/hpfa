from __future__ import annotations

from collections import Counter
from typing import Any


MODULE_ID = "score_state_visible_process_outcome_context_v1"
CLAIM_CEILING = "MATCH_LOCAL_SCORE_STATE_VISIBLE_PROCESS_OUTCOME_CONTEXT_ONLY"


def _float_candidate(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_identity_text(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def build_score_state_visible_process_outcome_context(
    game_state_context: dict[str, Any],
    identity_payload: dict[str, Any],
    process_development_signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind admitted process development signatures to visible score-state segments.

    This surface is descriptive only. It reports match-local process/outcome
    composition under visible score states and never promotes score state to a
    causal explanation, tactical-intention truth, dominance, momentum or risk appetite.
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

    signatures = [
        row for row in (process_development_signatures or [])
        if isinstance(row, dict)
    ]
    profiles: list[dict[str, Any]] = []
    unresolved_team_labels: set[str] = set()

    for segment in game_state_context.get("score_state_segments", []) or []:
        if not isinstance(segment, dict):
            continue
        start = _float_candidate(segment.get("start_second_candidate"))
        end = _float_candidate(segment.get("end_second_candidate"))
        if start is None or end is None or end < start:
            continue
        duration = max(0.0, end - start)
        score_state = segment.get("score_state_candidate") or {}

        for team_label in score_state:
            team_id = alias_to_team_id.get(_normalize_identity_text(team_label))
            if not team_id:
                unresolved_team_labels.add(str(team_label))
                continue

            rows = []
            for signature in signatures:
                if str(signature.get("team_identity_candidate_id") or "") != team_id:
                    continue
                process_start = _float_candidate(signature.get("process_start_candidate"))
                if process_start is None:
                    continue
                if start <= process_start < end or (duration == 0 and process_start == start):
                    rows.append(signature)

            family_counts: Counter[str] = Counter(
                str(row.get("process_family_candidate") or "UNKNOWN")
                for row in rows
            )
            eligible_n = len(rows)
            shot_n = sum(row.get("shot_present_annotation_candidate") is True for row in rows)
            loss_n = sum(bool(row.get("visible_loss_transition_candidate_present")) for row in rows)
            recovery_n = sum(bool(row.get("visible_recovery_transition_candidate_present")) for row in rows)

            def share(value: int) -> float | None:
                return round(value / eligible_n, 6) if eligible_n else None

            def rate10(value: int) -> float | None:
                return round((value / duration) * 600.0, 6) if duration > 0 else None

            profiles.append({
                "team_identity_candidate_id": team_id,
                "team_label": team_label,
                "score_state_candidate": score_state,
                "segment_start_second_candidate": start,
                "segment_end_second_candidate": end,
                "segment_duration_second_candidate": duration,
                "eligible_visible_process_n": eligible_n,
                "process_family_counts": dict(sorted(family_counts.items())),
                "shot_ending_process_n": shot_n,
                "visible_loss_process_n": loss_n,
                "visible_recovery_process_n": recovery_n,
                "shot_ending_share_candidate": share(shot_n),
                "visible_loss_share_candidate": share(loss_n),
                "visible_recovery_share_candidate": share(recovery_n),
                "eligible_visible_process_rate_per_10_minutes": rate10(eligible_n),
                "shot_ending_process_rate_per_10_minutes": rate10(shot_n),
                "visible_loss_process_rate_per_10_minutes": rate10(loss_n),
                "visible_recovery_process_rate_per_10_minutes": rate10(recovery_n),
                "rate_denominator_is_score_state_exposure_time": True,
                "share_denominator_is_visible_admitted_process_count": True,
                "outcome_categories_are_mutually_exclusive": False,
                "zero_process_count_is_process_absence_truth": False,
                "score_state_is_causal_explanation": False,
                "score_state_profile_is_risk_appetite_truth": False,
                "score_state_profile_is_tactical_adaptation_truth": False,
                "score_state_profile_is_dominance_truth": False,
                "creates_independent_support": False,
            })

    if not signatures:
        status = "NOT_AVAILABLE"
    elif profiles and unresolved_team_labels:
        status = "REVIEW_REQUIRED"
    elif profiles:
        status = "PASS"
    else:
        status = "NOT_AVAILABLE"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "binding_state": "SCORE_STATE_TO_VISIBLE_PROCESS_OUTCOME_CONTEXT",
        "profile_count": len(profiles),
        "profiles": profiles,
        "unresolved_team_labels": sorted(unresolved_team_labels),
        "hard_block_hits": [],
        "review_hits": (
            ["score_state_team_identity_unresolved"]
            if unresolved_team_labels
            else []
        ),
        "claim_ceiling": CLAIM_CEILING,
        "score_state_is_causal_explanation": False,
        "score_state_profile_is_risk_appetite_truth": False,
        "score_state_profile_is_tactical_adaptation_truth": False,
        "score_state_profile_is_dominance_truth": False,
        "creates_independent_support": False,
    }
