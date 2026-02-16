"""
HSR Ring — NAS (Negative Action Spiral)
Fail-closed, deterministic.

Rule:
- Same team, within a rolling window of N events (default 3)
- If all are failed outcomes -> NAS TRIGGER
- Missing fields -> FAIL-CLOSED
"""
from __future__ import annotations
from collections import deque
from typing import Any, Dict, Deque

class NASRing:
    def __init__(self, window_events: int = 3) -> None:
        self.window_events = int(window_events)
        self._hist: Dict[str, Deque[str]] = {}

    def update(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(event, dict):
            raise ValueError("NAS_FAIL_CLOSED:event_not_dict")

        team = event.get("team_id")
        outcome = event.get("outcome")
        state = event.get("state_id")

        if team is None or state is None:
            raise ValueError("NAS_FAIL_CLOSED:missing_required_fields")

        # Only evaluate during active play
        if state not in ("CONTROLLED", "CONTESTED"):
            event.update({"nas_flag": False})
            return event

        # Normalize outcome
        if outcome is None:
            event.update({"nas_flag": False})
            return event

        o = str(outcome).lower()
        if o not in ("success", "fail"):
            raise ValueError("NAS_FAIL_CLOSED:invalid_outcome")

        dq = self._hist.setdefault(str(team), deque(maxlen=self.window_events))
        dq.append(o)

        if len(dq) == self.window_events and all(x == "fail" for x in dq):
            event.update({
                "nas_flag": True,
                "nas_level": self.window_events,
                "nas_reason": f"{self.window_events}_consecutive_failures"
            })
        else:
            event.update({"nas_flag": False})

        return event
