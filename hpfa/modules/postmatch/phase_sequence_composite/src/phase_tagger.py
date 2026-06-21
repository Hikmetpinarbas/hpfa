#!/usr/bin/env python3
"""HPFA Phase Tagger V1.

Rule-based, event-only phase evidence labels.
This module emits evidence labels only. It does not emit report-language claims.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

P1 = "P1_BUILDUP"
P2 = "P2_PROGRESSION"
P3 = "P3_FINALIZATION"
P4 = "P4_NEG_TRANSITION"
P5 = "P5_ORG_DEFENSE"
P6 = "P6_POS_TRANSITION"

FINAL_ACTIONS = {"shot", "goal", "miss", "save", "attempt"}
DEF_ACTIONS = {"tackle", "interception", "clearance", "block", "pressure", "foul", "duel", "challenge"}
TURNOVER_OUTCOMES = {"incomplete", "fail", "failed", "lost", "turnover", "out", "unsuccessful"}
ON_BALL_TYPES = {"pass", "carry", "dribble", "shot", "cross", "throw_in", "free_kick", "corner", "goal_kick"}


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    text = text.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return text.replace("-", "_").replace(" ", "_")


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"na", "nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def get_event_type(event: Dict[str, Any]) -> str:
    return norm_text(event.get("event_type") or event.get("action") or event.get("type") or event.get("code"))


def get_outcome(event: Dict[str, Any]) -> str:
    return norm_text(event.get("outcome") or event.get("result"))


def get_team(event: Dict[str, Any]) -> str:
    return str(event.get("team_id") or event.get("team") or "").strip()


def get_time_seconds(event: Dict[str, Any]) -> Optional[float]:
    for key in ("time_seconds", "t_game_sec", "seconds", "start"):
        value = to_float(event.get(key))
        if value is not None:
            return value
    minute = to_float(event.get("minute"))
    second = to_float(event.get("second"))
    if minute is not None or second is not None:
        return float((minute or 0.0) * 60.0 + (second or 0.0))
    return None


def get_x(event: Dict[str, Any]) -> Optional[float]:
    return to_float(event.get("start_x") or event.get("x") or event.get("pos_x"))


def get_end_x(event: Dict[str, Any]) -> Optional[float]:
    value = to_float(event.get("end_x"))
    return value if value is not None else get_x(event)


def normalize_x_to_100(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    if 0.0 <= x <= 105.0:
        return (x / 105.0) * 100.0
    if 0.0 <= x <= 120.0:
        return (x / 120.0) * 100.0
    if 0.0 <= x <= 100.0:
        return x
    return None


def zone_bucket(x: Optional[float]) -> str:
    nx = normalize_x_to_100(x)
    if nx is None:
        return "unknown_zone"
    if nx <= 35.0:
        return "own_third"
    if nx <= 70.0:
        return "mid_third"
    return "att_third"


def zone_phase(x: Optional[float]) -> str:
    zone = zone_bucket(x)
    if zone == "own_third":
        return P1
    if zone == "mid_third":
        return P2
    if zone == "att_third":
        return P3
    return P2


def is_progressive_movement(event: Dict[str, Any]) -> bool:
    sx = normalize_x_to_100(get_x(event))
    ex = normalize_x_to_100(get_end_x(event))
    if sx is None or ex is None:
        return False
    return (ex - sx) >= 10.0


def tag_phase_event(event: Dict[str, Any], previous_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event_type = get_event_type(event)
    outcome = get_outcome(event)
    team = get_team(event)
    previous_team = get_team(previous_event or {})

    evidence_tags: List[str] = []
    degraded_flags: List[str] = []
    confidence = 0.35

    if not team:
        degraded_flags.append("missing_team")
    if get_x(event) is None:
        degraded_flags.append("missing_x")
    if get_time_seconds(event) is None:
        degraded_flags.append("missing_time")

    if previous_team and team and previous_team != team:
        phase_id = P6
        confidence = 0.55
        evidence_tags.append("team_switch")
    elif any(token in event_type for token in FINAL_ACTIONS):
        phase_id = P3
        confidence = 0.85
        evidence_tags.append("final_action")
    elif any(token in event_type for token in DEF_ACTIONS):
        phase_id = P5
        confidence = 0.55
        evidence_tags.append("defensive_action")
    elif any(token in outcome for token in TURNOVER_OUTCOMES):
        phase_id = P4
        confidence = 0.55
        evidence_tags.append("turnover_outcome")
    elif event_type in ON_BALL_TYPES and is_progressive_movement(event):
        phase_id = P2
        confidence = 0.70
        evidence_tags.append("progressive_movement")
    else:
        phase_id = zone_phase(get_end_x(event) or get_x(event))
        confidence = 0.55 if phase_id != P2 else 0.45
        evidence_tags.append("zone_inference")

    if "missing_x" in degraded_flags and phase_id in {P1, P2, P3}:
        confidence = min(confidence, 0.40)
        evidence_tags.append("confidence_cap_missing_x")

    return {
        "phase_id": phase_id,
        "phase_confidence": round(float(confidence), 3),
        "evidence_tags": evidence_tags,
        "degraded_flags": degraded_flags,
        "claim_safety": "EVIDENCE_ONLY",
    }


def tag_phases(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tagged: List[Dict[str, Any]] = []
    previous: Optional[Dict[str, Any]] = None
    for idx, event in enumerate(events):
        phase = tag_phase_event(event, previous_event=previous)
        enriched = dict(event)
        enriched.update(
            {
                "event_index": idx,
                "phase_id": phase["phase_id"],
                "phase_confidence": phase["phase_confidence"],
                "phase_evidence_tags": phase["evidence_tags"],
                "phase_degraded_flags": phase["degraded_flags"],
                "claim_safety": "EVIDENCE_ONLY",
            }
        )
        tagged.append(enriched)
        previous = event
    return tagged
