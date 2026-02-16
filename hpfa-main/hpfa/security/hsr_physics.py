"""
HSR Ring 4 — Physics & Kinematics (Fail-Closed)

Contract (tests):
- Speed violation => "HSR_PHYSICS_VIOLATION"
- Missing xy => "HSR_FAIL_CLOSED:physics:missing_xy"
- Nonpositive dt => "HSR_FAIL_CLOSED:physics:nonpositive_dt"

Stateful ring:
- First call stores (t,x,y)
- Next calls compute dt, distance, speed
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PhysicsRing:
    max_speed_mps: float = 12.0
    prev_t: Optional[float] = None
    prev_x: Optional[float] = None
    prev_y: Optional[float] = None


def _num(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def validate_physics(event: Dict[str, Any], ring: PhysicsRing) -> None:
    if not isinstance(event, dict):
        raise ValueError("HSR_FAIL_CLOSED:physics:event_not_dict")
    if not isinstance(ring, PhysicsRing):
        raise ValueError("HSR_FAIL_CLOSED:physics:ring_not_physicsring")

    t = _num(event.get("event_start_time"))
    x = _num(event.get("x"))
    y = _num(event.get("y"))

    # Fail-closed: missing core fields
    if x is None or y is None:
        raise ValueError("HSR_FAIL_CLOSED:physics:missing_xy")
    if t is None:
        raise ValueError("HSR_FAIL_CLOSED:physics:missing_time")

    # First observation seeds the ring
    if ring.prev_t is None:
        ring.prev_t = t
        ring.prev_x = x
        ring.prev_y = y
        return

    # Fail-closed: prev fields must exist if prev_t exists
    if ring.prev_x is None or ring.prev_y is None:
        raise ValueError("HSR_FAIL_CLOSED:physics:missing_prev_xy")

    dt = t - ring.prev_t
    if dt <= 0:
        raise ValueError("HSR_FAIL_CLOSED:physics:nonpositive_dt")

    dx = x - ring.prev_x
    dy = y - ring.prev_y
    dist = (dx * dx + dy * dy) ** 0.5
    speed = dist / dt

    if speed > float(ring.max_speed_mps):
        raise ValueError(f"HSR_PHYSICS_VIOLATION:speed={speed:.2f}")

    # Commit
    ring.prev_t = t
    ring.prev_x = x
    ring.prev_y = y
