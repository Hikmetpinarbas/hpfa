#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List


def _team(e: Dict[str, Any]) -> str:
    return str(e.get('team_id') or e.get('team') or '').strip()


def _id(e: Dict[str, Any]) -> str:
    return str(e.get('chain_id') or e.get('sequence_root_id') or '').strip()


def segment_chains(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not events:
        return []
    has_id = any(_id(e) for e in events)
    mode = 'EXPLICIT_ID' if has_id else 'TEAM_RUN'
    flags = [] if has_id else ['no_explicit_chain_id']
    out: List[Dict[str, Any]] = []
    cur = (_id(events[0]) if has_id and _id(events[0]) else _team(events[0])) or 'NA'
    team = _team(events[0])
    start = 0
    for i in range(1, len(events)):
        key = (_id(events[i]) if has_id and _id(events[i]) else _team(events[i])) or 'NA'
        if key != cur:
            out.append({'chain_id': str(cur), 'team_id': team, 'start_event_index': start, 'end_event_index': i-1, 'event_count': i-start, 'mode': mode, 'flags': list(flags), 'boundary': 'EVIDENCE_ONLY'})
            cur = key
            team = _team(events[i])
            start = i
    out.append({'chain_id': str(cur), 'team_id': team, 'start_event_index': start, 'end_event_index': len(events)-1, 'event_count': len(events)-start, 'mode': mode, 'flags': list(flags), 'boundary': 'EVIDENCE_ONLY'})
    return out
