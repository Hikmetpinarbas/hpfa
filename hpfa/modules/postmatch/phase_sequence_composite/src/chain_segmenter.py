#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List, Tuple


def _team(e: Dict[str, Any]) -> str:
    return str(e.get("team_id") or e.get("team") or "").strip()


def _id(e: Dict[str, Any]) -> str:
    return str(
        e.get("possession_id")
        or e.get("possession")
        or e.get("chain_id")
        or e.get("sequence_root_id")
        or ""
    ).strip()


def _ctx(e: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    return (
        str(e.get("half") or e.get("period") or "").strip(),
        str(e.get("period_scope") or "").strip(),
        str(e.get("score_state") or "").strip(),
        str(e.get("red_card_state") or "").strip(),
        str(e.get("numerical_state") or "").strip(),
    )


def _boundary_reason(prev: Dict[str, Any], cur: Dict[str, Any]) -> str:
    if str(prev.get("half") or prev.get("period") or "") != str(cur.get("half") or cur.get("period") or ""):
        return "half_change"
    if str(prev.get("period_scope") or "") != str(cur.get("period_scope") or ""):
        return "period_scope_change"
    if str(prev.get("score_state") or "") != str(cur.get("score_state") or ""):
        return "score_state_change"
    if str(prev.get("red_card_state") or "") != str(cur.get("red_card_state") or ""):
        return "red_card_state_change"
    if str(prev.get("numerical_state") or "") != str(cur.get("numerical_state") or ""):
        return "numerical_state_change"
    return "possession_key_change"


def segment_chains(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not events:
        return []

    has_id = any(_id(e) for e in events)
    authority = "EXPLICIT_POSSESSION_ID" if has_id else "FALLBACK_TEAM_RUN"
    degraded_flags = [] if has_id else ["missing_explicit_possession_id"]

    out: List[Dict[str, Any]] = []
    emitted_counts: Dict[str, int] = {}

    cur = (_id(events[0]) if has_id and _id(events[0]) else _team(events[0])) or "NA"
    team = _team(events[0])
    context = _ctx(events[0])
    start = 0
    last_reason = "start_of_match"

    def emit(end_index: int, reason: str) -> None:
        emitted_index = emitted_counts.get(str(cur), 0)
        emitted_counts[str(cur)] = emitted_index + 1
        emitted_id = str(cur) if emitted_index == 0 else f"{cur}_part_{emitted_index}"

        first = events[start]
        out.append({
            "possession_id": emitted_id,
            "source_possession_key": str(cur),
            "team_id": team,
            "start_event_index": start,
            "end_event_index": end_index,
            "event_count": end_index - start + 1,
            "surface_row_count": end_index - start + 1,
            "possession_authority": authority,
            "boundary_reason": reason,
            "half": first.get("half") or first.get("period") or "",
            "period_scope": first.get("period_scope") or "",
            "score_state": first.get("score_state") or "",
            "red_card_state": first.get("red_card_state") or "",
            "numerical_state": first.get("numerical_state") or "",
            "coordinate_scale": first.get("coordinate_scale") or "105x68",
            "degraded_flags": list(degraded_flags),
            "claim_safety": "EVIDENCE_ONLY",
        })

    for i in range(1, len(events)):
        key = (_id(events[i]) if has_id and _id(events[i]) else _team(events[i])) or "NA"
        ctx = _ctx(events[i])

        if key != cur or ctx != context:
            reason = _boundary_reason(events[i - 1], events[i])
            emit(i - 1, reason)

            cur = key
            team = _team(events[i])
            context = ctx
            start = i
            last_reason = reason

    emit(len(events) - 1, "end_of_match" if last_reason == "start_of_match" else last_reason)
    return out
