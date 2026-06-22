#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, List, Optional

PASS_MARKERS = (
    "pass", "passes", "cross", "crosses", "assist", "key_pass", "chances_created", "chance_created"
)
FINISH_MARKERS = (
    "shot", "shots", "goal", "goals", "free_kick_shot", "chance", "chances"
)
CONTEST_MARKERS = (
    "duel", "duels", "challenge", "challenges", "tackle", "tackles", "aerial", "foul", "fouls"
)
CARRY_MARKERS = (
    "carry", "carries", "dribble", "dribbles", "dribbling"
)
GAIN_MARKERS = (
    "recover", "recoveries", "interception", "interceptions", "tackle_won", "tackles_successful"
)
NEGATIVE_MARKERS = (
    "lost_ball", "lost_balls", "bad_ball_control", "mistake", "mistakes"
)


def norm(v: Any) -> str:
    return str(v or "").strip().lower().replace(" ", "_").replace("-", "_")


def num(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


def kind(e: Dict[str, Any]) -> str:
    return norm(e.get("event_type") or e.get("action") or e.get("type") or e.get("code"))


def side(e: Dict[str, Any]) -> str:
    return str(e.get("team_id") or e.get("team") or "").strip()


def has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def start_x(e: Dict[str, Any]) -> Optional[float]:
    return num(e.get("start_x") or e.get("x") or e.get("pos_x"))


def end_x(e: Dict[str, Any]) -> Optional[float]:
    value = num(e.get("end_x"))
    return value if value is not None else start_x(e)


def tsec(e: Dict[str, Any]) -> Optional[float]:
    for key in ("time_seconds", "t_game_sec", "seconds", "start"):
        value = num(e.get(key))
        if value is not None:
            return value

    minute = num(e.get("minute"))
    second = num(e.get("second"))
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

    xs = [start_x(r) for r in rows]
    xs = [x for x in xs if x is not None]

    if len(xs) >= 2:
        return float(xs[-1] - xs[0])

    a = start_x(rows[0])
    b = end_x(rows[-1])
    return 0.0 if a is None or b is None else float(b - a)


def coordinate_scale(rows: List[Dict[str, Any]]) -> str:
    for row in rows:
        value = str(row.get("coordinate_scale") or "").strip()
        if value:
            return value
    return "105x68"


def normalize_x(x: float, scale: str) -> float:
    scale_norm = scale.lower().replace("_", "").replace("-", "")

    if scale_norm in {"105x68", "0105", "0to105"}:
        return (x / 105.0) * 100.0

    if scale_norm in {"100x100", "0100", "0to100"}:
        return x

    if scale_norm in {"120x80", "0120", "0to120"}:
        return (x / 120.0) * 100.0

    return (x / 105.0) * 100.0 if 0.0 <= x <= 105.0 else x


def zone6(e: Dict[str, Any], end: bool = False, scale: str = "105x68") -> int:
    x = end_x(e) if end else start_x(e)
    if x is None:
        return -1

    nx = normalize_x(x, scale)
    if nx < 0.0 or nx > 100.0:
        return -1

    return min(5, int((nx / 100.0) * 6))


def action_counts(kinds: List[str]) -> Dict[str, int]:
    return {
        "passes": sum(1 for k in kinds if has_any(k, PASS_MARKERS)),
        "shots": sum(1 for k in kinds if has_any(k, FINISH_MARKERS)),
        "duels": sum(1 for k in kinds if has_any(k, CONTEST_MARKERS)),
        "carries": sum(1 for k in kinds if has_any(k, CARRY_MARKERS)),
        "recoveries": sum(1 for k in kinds if has_any(k, GAIN_MARKERS)),
        "negative_events": sum(1 for k in kinds if has_any(k, NEGATIVE_MARKERS)),
    }


def label_type(a: int, b: int, c: int, d: int, e: int, n: int, dx: float, seconds: float) -> str:
    if b > 0:
        return "end_product_sequence"
    if e > 0 and dx >= 8.0:
        return "gain_to_advance_sequence"
    if n > 0:
        return "loss_or_error_sequence"
    if dx >= 15.0 and (a + d) >= 1:
        return "direct_advance_sequence"
    if a >= 3 and seconds >= 5.0:
        return "long_ball_circulation_sequence"
    if c >= 2:
        return "contest_cluster_sequence"
    return "recycle_or_build_sequence"


def build_features(rows: List[Dict[str, Any]], sequence_id: str, chain_id: str, reason: str) -> Dict[str, Any]:
    kinds = [kind(r) for r in rows]
    counts = action_counts(kinds)

    a = counts["passes"]
    b = counts["shots"]
    c = counts["duels"]
    d = counts["carries"]
    e = counts["recoveries"]
    n = counts["negative_events"]

    seconds = dur(rows)
    dx = x_delta(rows)
    scale = coordinate_scale(rows)

    first = rows[0] if rows else {}
    last = rows[-1] if rows else {}

    return {
        "sequence_id": sequence_id,
        "possession_id": chain_id,
        "team_id": side(first) if rows else "",
        "start_event_index": int(first.get("event_index", 0)) if rows else 0,
        "end_event_index": int(last.get("event_index", 0)) if rows else 0,
        "event_count": len(rows),
        "surface_row_count": len(rows),
        "duration": round(seconds, 3),
        "passes": a,
        "shots": b,
        "duels": c,
        "carries": d,
        "recoveries": e,
        "progression_x": round(dx, 3),
        "coordinate_scale": scale,
        "half": first.get("half") or first.get("period") or "",
        "period_scope": first.get("period_scope") or "",
        "score_state": first.get("score_state") or "",
        "red_card_state": first.get("red_card_state") or "",
        "numerical_state": first.get("numerical_state") or "",
        "start_zone": zone6(first, False, scale) if rows else -1,
        "end_zone": zone6(last, True, scale) if rows else -1,
        "terminal_event_type": kind(last) if rows else "",
        "boundary_reason": reason,
        "transition_flag": bool(e > 0 or reason.startswith("team_switch")),
        "sequence_type": label_type(a, b, c, d, e, n, dx, seconds),
        "claim_safety": "EVIDENCE_ONLY",
        "degraded_flags": [],
    }
