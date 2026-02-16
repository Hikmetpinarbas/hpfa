# Fail-Closed Context / Temporal Validator (Ring 5)
from typing import Dict, Any

COOLDOWN_S = 0.3

def validate_context(event: Dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise ValueError("HSR_FAIL_CLOSED:context:event_not_dict")

    ts = event.get("event_start_time")
    prev_ts = event.get("prev_event_time")
    state = event.get("state_id")
    prev_state = event.get("prev_state_id")
    effect = event.get("possession_effect")

    if ts is None or prev_ts is None or state is None or prev_state is None:
        raise ValueError("HSR_FAIL_CLOSED:context:missing_fields")

    if ts < prev_ts:
        raise ValueError("HSR_CONTEXT_VIOLATION:time_non_monotonic")

    if effect == "START" and not (prev_state == "DEAD_BALL" and state == "CONTROLLED"):
        raise ValueError("HSR_CONTEXT_VIOLATION:start_out_of_dead_ball")

    if prev_state == "DEAD_BALL" and (ts - prev_ts) > COOLDOWN_S and event.get("event_type") in ("TACKLE","INTERCEPTION"):
        raise ValueError("HSR_CONTEXT_VIOLATION:cooldown_breach")
