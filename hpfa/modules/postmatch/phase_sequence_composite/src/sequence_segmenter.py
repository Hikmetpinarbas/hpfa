#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List

try:
    from .sequence_features import build_features, kind
except ImportError:
    from sequence_features import build_features, kind

BREAK_KINDS = {'shot', 'foul', 'out', 'offside', 'corner', 'throw_in', 'goal_kick', 'free_kick', 'penalty', 'kick_off'}


def split_sequences(events: List[Dict[str, Any]], chains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for chain in chains:
        start = int(chain['start_event_index'])
        end = int(chain['end_event_index'])
        rows = events[start:end + 1]
        if not rows:
            continue
        current_phase = rows[0].get('phase_id')
        current_restart = rows[0].get('set_piece_state') or 'open_play'
        seq_start = 0
        seq_no = 0
        for rel_index in range(1, len(rows)):
            row = rows[rel_index]
            reason = ''
            if row.get('phase_id') != current_phase:
                reason = 'phase_change'
            elif (row.get('set_piece_state') or 'open_play') != current_restart:
                reason = 'restart_change'
            elif kind(row) in BREAK_KINDS:
                reason = 'break_event'
            if reason:
                part = rows[seq_start:rel_index]
                if part:
                    out.append(build_features(part, f"{chain['possession_id']}_seq_{seq_no}", chain['possession_id'], reason))
                    seq_no += 1
                seq_start = rel_index
                current_phase = row.get('phase_id')
                current_restart = row.get('set_piece_state') or 'open_play'
        part = rows[seq_start:]
        if part:
            out.append(build_features(part, f"{chain['possession_id']}_seq_{seq_no}", chain['possession_id'], 'end_of_chain'))
    return out
