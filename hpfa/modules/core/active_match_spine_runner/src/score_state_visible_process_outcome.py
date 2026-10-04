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


def bind_process_variant_board_score_state_context(
    game_state_context: dict[str, Any],
    identity_payload: dict[str, Any],
    process_development_signatures: list[dict[str, Any]],
    process_motif_family_candidates: list[dict[str, Any]],
    process_variant_board: dict[str, Any],
) -> dict[str, Any]:
    """Attach relative score-state context to existing recurrent process-variant rows.

    This is descriptive match-local context only. It does not turn score state into
    a causal explanation, tactical adaptation, intention, or quality claim.
    """
    from copy import deepcopy

    result = deepcopy(process_variant_board or {})
    rows = [row for row in (result.get("rows") or []) if isinstance(row, dict)]
    if not rows:
        return result

    aliases_by_team: dict[str, set[str]] = {}
    for row in identity_payload.get("team_identity_candidates", []) or []:
        if not isinstance(row, dict):
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if not team_id:
            continue
        aliases = {
            _normalize_identity_text(value)
            for value in (row.get("team_aliases_raw") or [])
            if _normalize_identity_text(value)
        }
        aliases_by_team[team_id] = aliases

    signature_by_id = {
        str(row.get("process_development_signature_id") or ""): row
        for row in (process_development_signatures or [])
        if isinstance(row, dict) and str(row.get("process_development_signature_id") or "")
    }
    motif_members = {
        str(row.get("process_motif_family_candidate_id") or ""): [
            str(value)
            for value in (row.get("member_process_development_signature_ids") or [])
            if str(value)
        ]
        for row in (process_motif_family_candidates or [])
        if isinstance(row, dict) and str(row.get("process_motif_family_candidate_id") or "")
    }
    segments = [
        row for row in (game_state_context.get("score_state_segments") or [])
        if isinstance(row, dict)
    ]

    for row in rows:
        motif_id = str(row.get("process_motif_family_candidate_id") or "")
        team_id = str(row.get("team_identity_candidate_id") or "")
        members = [signature_by_id[value] for value in motif_members.get(motif_id, []) if value in signature_by_id]
        counts: Counter[str] = Counter()
        unresolved_n = 0
        aliases = aliases_by_team.get(team_id, set())
        for member in members:
            start = _float_candidate(member.get("process_start_candidate"))
            if start is None:
                unresolved_n += 1
                continue
            segment = None
            for candidate in segments:
                seg_start = _float_candidate(candidate.get("start_second_candidate"))
                seg_end = _float_candidate(candidate.get("end_second_candidate"))
                if seg_start is None or seg_end is None:
                    continue
                duration = max(0.0, seg_end - seg_start)
                if seg_start <= start < seg_end or (duration == 0 and start == seg_start):
                    segment = candidate
                    break
            if segment is None:
                unresolved_n += 1
                continue
            score = segment.get("score_state_candidate") or {}
            if not isinstance(score, dict) or len(score) < 2:
                unresolved_n += 1
                continue
            own_key = next(
                (key for key in score if _normalize_identity_text(key) in aliases),
                None,
            )
            if own_key is None:
                unresolved_n += 1
                continue
            own_score = _float_candidate(score.get(own_key))
            opponent_scores = [
                _float_candidate(value) for key, value in score.items() if key != own_key
            ]
            opponent_scores = [value for value in opponent_scores if value is not None]
            if own_score is None or len(opponent_scores) != 1:
                unresolved_n += 1
                continue
            opponent_score = opponent_scores[0]
            if own_score > opponent_score:
                counts["LEADING"] += 1
            elif own_score < opponent_score:
                counts["TRAILING"] += 1
            else:
                counts["DRAW"] += 1

        bound_n = sum(counts.values())
        row["visible_score_state_context"] = {
            "member_process_n": len(members),
            "bound_member_process_n": bound_n,
            "unresolved_member_process_n": unresolved_n,
            "relative_score_state_counts": dict(sorted(counts.items())),
            "binding_basis": "PROCESS_START_WITHIN_ADMITTED_VISIBLE_SCORE_STATE_SEGMENT",
            "score_state_context_is_causal_explanation": False,
            "score_state_context_is_tactical_adaptation_truth": False,
            "score_state_context_is_risk_appetite_truth": False,
            "score_state_context_can_increase_claim_ceiling": False,
            "creates_independent_support": False,
            "claim_ceiling": "MATCH_LOCAL_PROCESS_VARIANT_VISIBLE_SCORE_STATE_CONTEXT_ONLY",
        }
    result["rows"] = rows
    result["score_state_context_bound"] = True
    result["score_state_context_is_causal_explanation"] = False
    result["score_state_context_is_tactical_adaptation_truth"] = False
    return result
