#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List


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


def segment_chains(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not events:
        return []

    has_id = any(_id(e) for e in events)
    authority = "EXPLICIT_POSSESSION_ID" if has_id else "FALLBACK_TEAM_RUN"
    degraded_flags = [] if has_id else ["missing_explicit_possession_id"]

    out: List[Dict[str, Any]] = []

    cur = (_id(events[0]) if has_id and _id(events[0]) else _team(events[0])) or "NA"
    team = _team(events[0])
    start = 0

    def emit(end_index: int) -> None:
        out.append({
            "possession_id": str(cur),
            "team_id": team,
            "start_event_index": start,
            "end_event_index": end_index,
            "event_count": end_index - start + 1,
            "possession_authority": authority,
            "degraded_flags": list(degraded_flags),
            "claim_safety": "EVIDENCE_ONLY",
        })

    for i in range(1, len(events)):
        key = (_id(events[i]) if has_id and _id(events[i]) else _team(events[i])) or "NA"
        if key != cur:
            emit(i - 1)
            cur = key
            team = _team(events[i])
            start = i

    emit(len(events) - 1)
    return out
