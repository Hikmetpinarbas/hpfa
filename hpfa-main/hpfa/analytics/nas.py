"""
NAS — Negative Action Spiral (Canonical v1.0.0)
SSOT: hpfa/canon/nas.md

Fail-closed:
- Missing required fields => status=UNVALIDATED (no metric)
- No speculation, no correction

HSR:
- Ring3 dead-ball veto => exclude
- Ring4 physics veto  => exclude
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_FIELDS = [
    "event_start_time",   # ts
    "phase",
    "state_id",
    "action_type",
    "outcome",
    "zone_id",
    "pressure_level",
    "hsr_flags",
]


def _missing_fields(e: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for k in REQUIRED_FIELDS:
        if k not in e:
            missing.append(k)
    # hsr_flags subkeys
    hf = e.get("hsr_flags")
    if isinstance(hf, dict):
        if "ring3_dead_ball_veto" not in hf:
            missing.append("hsr_flags.ring3_dead_ball_veto")
        if "ring4_physics_veto" not in hf:
            missing.append("hsr_flags.ring4_physics_veto")
    else:
        missing.append("hsr_flags")
    return missing


def _norm_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def _norm_str(x: Any) -> Optional[str]:
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return None


@dataclass(frozen=True)
class NASSequence:
    start_ts: float
    end_ts: float
    zone_id: str
    fail_count: int
    avg_pressure: float
    max_pressure: float
    event_ids: List[str]


@dataclass(frozen=True)
class NASResult:
    status: str  # PASS | UNVALIDATED
    reason: str
    nas_sequence_count: int
    sequences: List[NASSequence]


class NASDetector:
    """
    Deterministic NAS detector.
    Input: list of canonical-ish events (dicts).
    Output: NASResult (PASS even if 0 sequences, UNVALIDATED if missing fields prevent evaluation).
    """

    def __init__(self, max_dt_s: float = 0.5, min_fail_count: int = 3) -> None:
        self.max_dt_s = float(max_dt_s)
        self.min_fail_count = int(min_fail_count)

    def evaluate(self, events: List[Dict[str, Any]]) -> NASResult:
        if not isinstance(events, list):
            return NASResult(
                status="UNVALIDATED",
                reason="NAS_FAIL_CLOSED:events_not_list",
                nas_sequence_count=0,
                sequences=[],
            )

        # fail-closed if any event missing required fields
        for i, e in enumerate(events):
            if not isinstance(e, dict):
                return NASResult(
                    status="UNVALIDATED",
                    reason=f"NAS_FAIL_CLOSED:event_not_dict:index={i}",
                    nas_sequence_count=0,
                    sequences=[],
                )
            missing = _missing_fields(e)
            if missing:
                return NASResult(
                    status="UNVALIDATED",
                    reason=f"NAS_FAIL_CLOSED:missing_{missing[0]}",
                    nas_sequence_count=0,
                    sequences=[],
                )

        # Sort by time deterministically (stable)
        def _ts_key(e: Dict[str, Any]) -> float:
            ts = _norm_float(e.get("event_start_time"))
            return ts if ts is not None else 0.0

        events_sorted = sorted(events, key=_ts_key)

        sequences: List[NASSequence] = []

        # Running chain state
        chain_zone: Optional[str] = None
        chain_start_ts: Optional[float] = None
        chain_end_ts: Optional[float] = None
        chain_fail_count: int = 0
        chain_pressures: List[float] = []
        chain_event_ids: List[str] = []
        prev_fail_ts: Optional[float] = None

        def _flush_chain() -> None:
            nonlocal chain_zone, chain_start_ts, chain_end_ts, chain_fail_count, chain_pressures, chain_event_ids, prev_fail_ts
            if chain_zone is not None and chain_start_ts is not None and chain_end_ts is not None:
                if chain_fail_count >= self.min_fail_count:
                    avg_p = sum(chain_pressures) / len(chain_pressures) if chain_pressures else 0.0
                    max_p = max(chain_pressures) if chain_pressures else 0.0
                    sequences.append(
                        NASSequence(
                            start_ts=chain_start_ts,
                            end_ts=chain_end_ts,
                            zone_id=chain_zone,
                            fail_count=chain_fail_count,
                            avg_pressure=avg_p,
                            max_pressure=max_p,
                            event_ids=list(chain_event_ids),
                        )
                    )
            # reset
            chain_zone = None
            chain_start_ts = None
            chain_end_ts = None
            chain_fail_count = 0
            chain_pressures = []
            chain_event_ids = []
            prev_fail_ts = None

        for e in events_sorted:
            ts = _norm_float(e["event_start_time"])
            phase = _norm_str(e["phase"])
            state_id = _norm_str(e["state_id"])
            action_type = _norm_str(e["action_type"])
            outcome = _norm_str(e["outcome"])
            zone_id_raw = e["zone_id"]
            pressure = _norm_float(e["pressure_level"])
            hsr_flags = e["hsr_flags"]

            # We already validated presence; now validate types deterministically
            if ts is None or phase is None or state_id is None or action_type is None or outcome is None or pressure is None:
                return NASResult(
                    status="UNVALIDATED",
                    reason="NAS_FAIL_CLOSED:bad_field_type",
                    nas_sequence_count=0,
                    sequences=[],
                )

            zone_id = str(zone_id_raw)

            r3 = bool(hsr_flags.get("ring3_dead_ball_veto"))
            r4 = bool(hsr_flags.get("ring4_physics_veto"))

            # Hard gates (exclude)
            if phase not in ("DEFENSIVE", "TRANSITION"):
                # ignore but also break chain (scope boundary)
                _flush_chain()
                continue

            if state_id == "DEAD_BALL" or r3:
                _flush_chain()
                continue

            if r4:
                _flush_chain()
                continue

            if outcome.upper() != "FAIL":
                _flush_chain()
                continue

            # This is a qualifying FAIL
            eid = _norm_str(e.get("event_id")) or ""

            if chain_zone is None:
                # start chain
                chain_zone = zone_id
                chain_start_ts = ts
                chain_end_ts = ts
                chain_fail_count = 1
                chain_pressures = [pressure]
                chain_event_ids = [eid] if eid else []
                prev_fail_ts = ts
                continue

            # must match zone and dt constraint
            if zone_id != chain_zone:
                _flush_chain()
                # start new
                chain_zone = zone_id
                chain_start_ts = ts
                chain_end_ts = ts
                chain_fail_count = 1
                chain_pressures = [pressure]
                chain_event_ids = [eid] if eid else []
                prev_fail_ts = ts
                continue

            if prev_fail_ts is None:
                # should not happen; fail-closed
                return NASResult(
                    status="UNVALIDATED",
                    reason="NAS_FAIL_CLOSED:internal_prev_ts_missing",
                    nas_sequence_count=0,
                    sequences=[],
                )

            dt = ts - prev_fail_ts
            if dt > self.max_dt_s:
                _flush_chain()
                # start new
                chain_zone = zone_id
                chain_start_ts = ts
                chain_end_ts = ts
                chain_fail_count = 1
                chain_pressures = [pressure]
                chain_event_ids = [eid] if eid else []
                prev_fail_ts = ts
                continue

            # extend chain
            chain_end_ts = ts
            chain_fail_count += 1
            chain_pressures.append(pressure)
            if eid:
                chain_event_ids.append(eid)
            prev_fail_ts = ts

        # flush final chain
        _flush_chain()

        return NASResult(
            status="PASS",
            reason="OK",
            nas_sequence_count=len(sequences),
            sequences=sequences,
        )
