"""
HSR Ring 3 — Dead Ball Recovery (Fail-Closed)

Rule:
- If an event happens right after DEAD_BALL (prev_state_id == DEAD_BALL),
  then some events are illegal (e.g., TACKLE, INTERCEPTION).
- Also if state_id is DEAD_BALL, illegal events must not exist.

This module does NOT "fix" the event; it vetoes (raises).
"""

from __future__ import annotations

from typing import Any, Dict

ILLEGAL_EVENTS = {"TACKLE", "INTERCEPTION"}

def validate_dead_ball(event: Dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise ValueError("HSR_FAIL_CLOSED:event_not_dict")

    e_type = event.get("event_type")
    if not isinstance(e_type, str) or not e_type.strip():
        raise ValueError("HSR_FAIL_CLOSED:missing_event_type")
    e_type = e_type.strip().upper()

    prev_state = event.get("prev_state_id")
    state = event.get("state_id")

    # Fail-closed: if state fields are missing, veto
    if prev_state is None and state is None:
        raise ValueError("HSR_FAIL_CLOSED:missing_state_fields")

    # Ring 3 triggers on "we are (or were just) in DEAD_BALL"
    dead_ball_context = (prev_state == "DEAD_BALL") or (state == "DEAD_BALL")

    if dead_ball_context and e_type in ILLEGAL_EVENTS:
        raise ValueError(f"HSR_DEAD_BALL_VIOLATION:{e_type}")
