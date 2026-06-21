#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List, Optional

GROUPS = {
    'pass_like': {'pass', 'cross', 'cutback', 'switch_pass'},
    'finish_like': {'shot', 'goal', 'attempt'},
    'contest_like': {'duel', 'aerial_duel', 'tackle', 'challenge'},
    'carry_like': {'carry', 'dribble', 'progressive_run'},
    'gain_like': {'recovery', 'interception', 'tackle_won', 'ball_recovery'}
}


def norm(v: Any) -> str:
    return str(v or '').strip().lower().replace(' ', '_').replace('-', '_')


def num(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == '':
            return None
        return float(v)
    except Exception:
        return None


def kind(e: Dict[str, Any]) -> str:
    return norm(e.get('event_type') or e.get('action') or e.get('type') or e.get('code'))


def side(e: Dict[str, Any]) -> str:
    return str(e.get('team_id') or e.get('team') or '').strip()


def start_x(e: Dict[str, Any]) -> Optional[float]:
    return num(e.get('start_x') or e.get('x') or e.get('pos_x'))


def end_x(e: Dict[str, Any]) -> Optional[float]:
    value = num(e.get('end_x'))
    return value if value is not None else start_x(e)


def tsec(e: Dict[str, Any]) -> Optional[float]:
    for key in ('time_seconds', 't_game_sec', 'seconds', 'start'):
        value = num(e.get(key))
        if value is not None:
            return value
    minute = num(e.get('minute'))
    second = num(e.get('second'))
    if minute is not None or second is not None:
        return (minute or 0.0) * 60.0 + (second or 0.0)
    return None


def dur(rows: List[Dict[str, Any]]) -> float:
    vals = [tsec(r) for r in rows]
    vals = [v for v in vals if v is not None]
    return 0.0 if len(vals) < 2 else float(max(vals) - min(vals))


def x_delta(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    a = start_x(rows[0])
    b = end_x(rows[-1])
    return 0.0 if a is None or b is None else float(b - a)


def zone6(e: Dict[str, Any], end: bool = False) -> int:
    x = end_x(e) if end else start_x(e)
    if x is None:
        return -1
    nx = (x / 105.0) * 100.0 if 0.0 <= x <= 105.0 else x
    if nx < 0.0 or nx > 100.0:
        return -1
    return min(5, int((nx / 100.0) * 6))


def group_count(kinds: List[str], group: str) -> int:
    items = GROUPS[group]
    return sum(1 for k in kinds if k in items)


def label_type(a: int, b: int, c: int, d: int, e: int, dx: float, seconds: float) -> str:
    if b > 0 and dx >= 12.0:
        return 'end_product_sequence'
    if e > 0 and dx >= 15.0:
        return 'gain_to_advance_sequence'
    if dx >= 20.0 and seconds <= 15.0 and (a + d) >= 2:
        return 'direct_advance_sequence'
    if a >= 4 and seconds >= 10.0:
        return 'long_ball_circulation_sequence'
    if c >= 2 and seconds <= 10.0:
        return 'contest_cluster_sequence'
    return 'recycle_or_build_sequence'


def build_features(rows: List[Dict[str, Any]], sequence_id: str, chain_id: str, reason: str) -> Dict[str, Any]:
    kinds = [kind(r) for r in rows]
    a = group_count(kinds, 'pass_like')
    b = group_count(kinds, 'finish_like')
    c = group_count(kinds, 'contest_like')
    d = group_count(kinds, 'carry_like')
    e = group_count(kinds, 'gain_like')
    seconds = dur(rows)
    dx = x_delta(rows)
    return {
        'sequence_id': sequence_id,
        'chain_id': chain_id,
        'team_id': side(rows[0]) if rows else '',
        'start_event_index': int(rows[0].get('event_index', 0)) if rows else 0,
        'end_event_index': int(rows[-1].get('event_index', 0)) if rows else 0,
        'event_count': len(rows),
        'duration': round(seconds, 3),
        'passes': a,
        'shots': b,
        'duels': c,
        'carries': d,
        'recoveries': e,
        'progression_x': round(dx, 3),
        'start_zone': zone6(rows[0], False) if rows else -1,
        'end_zone': zone6(rows[-1], True) if rows else -1,
        'terminal_event_type': kind(rows[-1]) if rows else '',
        'boundary_reason': reason,
        'transition_flag': bool(e > 0 or reason.startswith('team_switch')),
        'sequence_type': label_type(a, b, c, d, e, dx, seconds),
        'boundary': 'EVIDENCE_ONLY',
        'flags': []
    }
