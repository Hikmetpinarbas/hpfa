# CANON_SHA256 = "<BURAYA_HASHI_YAPISTIR>"
"""
HPFA Possession State Machine — Canonical v1.0.0

Single Source of Truth:
  - hpfa/canon/possession_state_machine.md

Fail-closed principles:
  - Missing required keys => ERROR (veto state)
  - Unknown event => UNVALIDATED (no transition)
  - Undefined transition => ERROR (no transition)
  - PASS/DRIBBLE missing/fail outcome => UNVALIDATED (canon table doesn't define)
  - DEAD_BALL => possession_id MUST be None

Scramble Buffer:
  - <= scramble_buffer_s gap in "loose/contested" moments should not create a new possession on team change

Atomic Unification:
  - same timestamp + same team_id => treated as one atom:
    no state change, no possession change (just annotate)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class HPFAState(str, Enum):
    CONTROLLED = "CONTROLLED"
    CONTESTED = "CONTESTED"
    DEAD_BALL = "DEAD_BALL"
    UNVALIDATED = "UNVALIDATED"
    ERROR = "ERROR"


class PossessionEffect(str, Enum):
    START = "START"
    CONTINUE = "CONTINUE"
    END = "END"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class SMResult:
    state: HPFAState
    effect: PossessionEffect
    possession_id: Optional[str]
    team_id: Optional[str]
    reason: str


def _norm_str(x: Any) -> Optional[str]:
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return None


def _norm_ts(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def _norm_event_type(x: Any) -> Optional[str]:
    s = _norm_str(x)
    return s.upper() if s else None


def _norm_team_id(x: Any) -> Optional[str]:
    # Deterministic but flexible: str/int accepted
    if isinstance(x, (int, float)):
        return str(int(x)) if float(x).is_integer() else str(x)
    return _norm_str(x)


def _norm_outcome(x: Any) -> Optional[str]:
    s = _norm_str(x)
    if not s:
        return None
    s = s.lower()
    if s in ("success", "fail", "failed", "failure"):
        return "success" if s == "success" else "fail"
    return None


class PossessionStateMachine:
    """
    Deterministic state machine implementing canon rules.

    Required event keys (fail-closed if missing):
      - event_type (str)
      - team_id (str|int)
      - event_start_time (float|int|numeric str)
    Optional:
      - outcome ("success"|"fail") for PASS/DRIBBLE
    """

    def __init__(self, scramble_buffer_s: float = 0.5) -> None:
        self.scramble_buffer_s = float(scramble_buffer_s)

        self.state: HPFAState = HPFAState.DEAD_BALL
        self.possession_id: Optional[str] = None
        self.team_id: Optional[str] = None

        self.last_ts: Optional[float] = None
        self.last_team_id: Optional[str] = None

        # deterministic possession id counter (no uuid)
        self._pos_counter: int = 0

    def _new_possession_id(self) -> str:
        self._pos_counter += 1
        return f"p{self._pos_counter:06d}"

    def update(self, event: Dict[str, Any]) -> Tuple[Dict[str, Any], SMResult]:
        # Fail-closed: must be dict
        if not isinstance(event, dict):
            res = SMResult(
                state=HPFAState.ERROR,
                effect=PossessionEffect.NEUTRAL,
                possession_id=self.possession_id,
                team_id=self.team_id,
                reason="fail_closed:event_not_dict",
            )
            out = {"state_id": res.state.value, "possession_id": res.possession_id}
            return out, res

        e_type = _norm_event_type(event.get("event_type"))
        team_id = _norm_team_id(event.get("team_id"))
        ts = _norm_ts(event.get("event_start_time"))
        outcome = _norm_outcome(event.get("outcome"))

        prev_state = self.state
        prev_pos_id = self.possession_id
        prev_team = self.team_id

        # fail-closed on missing critical fields
        if e_type is None or team_id is None or ts is None:
            res = SMResult(
                state=HPFAState.ERROR,
                effect=PossessionEffect.NEUTRAL,
                possession_id=prev_pos_id,
                team_id=prev_team,
                reason="fail_closed:missing_required_keys",
            )
            out = dict(event)
            out.update(
                {
                    "prev_state_id": prev_state.value,
                    "state_id": res.state.value,
                    "possession_effect": res.effect.value,
                    "possession_id": res.possession_id,
                    "sm_reason": res.reason,
                    "logic_version": "v1.0.0",
                }
            )
            # keep last_ts/last_team_id unchanged on fail-closed
            return out, res

        # Atomic unification: same timestamp + same team as last event => no transitions
        if self.last_ts is not None and self.last_team_id is not None:
            if ts == self.last_ts and team_id == self.last_team_id:
                res = SMResult(
                    state=prev_state,
                    effect=PossessionEffect.NEUTRAL,
                    possession_id=prev_pos_id,
                    team_id=prev_team,
                    reason="atomic_unify:same_ts_same_team",
                )
                out = dict(event)
                out.update(
                    {
                        "prev_state_id": prev_state.value,
                        "state_id": res.state.value,
                        "possession_effect": res.effect.value,
                        "possession_id": res.possession_id,
                        "sm_reason": res.reason,
                        "logic_version": "v1.0.0",
                    }
                )
                self.last_ts = ts
                self.last_team_id = team_id
                return out, res

        # Canonical transition decision
        new_state, effect, reason = self._transition(prev_state, e_type, outcome)

        # Possession management + scramble buffer
        new_pos_id = prev_pos_id
        new_team = prev_team

        # Invariant: DEAD_BALL => possession_id must be None
        if new_state == HPFAState.DEAD_BALL:
            new_pos_id = None
            new_team = None

        elif effect == PossessionEffect.START:
            # START only with CONTROLLED per canon invariant
            if new_state != HPFAState.CONTROLLED:
                new_state = HPFAState.ERROR
                effect = PossessionEffect.NEUTRAL
                reason = "invariant_violation:start_not_controlled"
            else:
                # Scramble buffer: if team changes but within buffer and we are coming out of CONTESTED, keep existing
                if (
                    prev_team is not None
                    and team_id != prev_team
                    and prev_state in (HPFAState.CONTESTED,)
                    and self.last_ts is not None
                    and (ts - self.last_ts) <= self.scramble_buffer_s
                ):
                    new_pos_id = prev_pos_id
                    new_team = prev_team
                    effect = PossessionEffect.NEUTRAL
                    reason = f"scramble_buffer:hold_possession_dt={ts - self.last_ts:.3f}"
                else:
                    new_pos_id = self._new_possession_id()
                    new_team = team_id

        elif effect == PossessionEffect.CONTINUE:
            # CONTINUE requires existing possession and CONTROLLED
            if new_state != HPFAState.CONTROLLED:
                new_state = HPFAState.ERROR
                effect = PossessionEffect.NEUTRAL
                reason = "invariant_violation:continue_not_controlled"
            if new_pos_id is None:
                new_pos_id = self._new_possession_id()
                new_team = team_id
                reason = f"{reason}|autostart_missing_possession"

        else:
            # NEUTRAL: keep possession by default unless dead_ball already handled
            if new_team is None and new_pos_id is not None:
                new_state = HPFAState.ERROR
                effect = PossessionEffect.NEUTRAL
                reason = "fail_closed:possession_without_team"

        # Commit state
        self.state = new_state
        self.possession_id = new_pos_id
        self.team_id = new_team
        self.last_ts = ts
        self.last_team_id = team_id

        res = SMResult(
            state=new_state,
            effect=effect,
            possession_id=new_pos_id,
            team_id=new_team,
            reason=reason,
        )

        out = dict(event)
        out.update(
            {
                "prev_state_id": prev_state.value,
                "state_id": res.state.value,
                "possession_effect": res.effect.value,
                "possession_id": res.possession_id,
                "sm_reason": res.reason,
                "logic_version": "v1.0.0",
            }
        )
        return out, res

    def _transition(
        self, prev_state: HPFAState, e_type: str, outcome: Optional[str]
    ) -> Tuple[HPFAState, PossessionEffect, str]:
        # ANY -> DEAD_BALL on OUT/FOUL
        if e_type in ("OUT", "FOUL"):
            return HPFAState.DEAD_BALL, PossessionEffect.END, f"transition:any+{e_type}->DEAD_BALL"

        # ANY -> CONTESTED on LOOSE_BALL
        if e_type == "LOOSE_BALL":
            return HPFAState.CONTESTED, PossessionEffect.NEUTRAL, "transition:any+LOOSE_BALL->CONTESTED_NEUTRAL"

        # DEAD_BALL -> CONTROLLED START on RESTART_*
        if e_type.startswith("RESTART_"):
            return HPFAState.CONTROLLED, PossessionEffect.START, f"transition:DEAD_BALL+{e_type}->CONTROLLED_START"

        # CONTROLLED -> CONTROLLED CONTINUE on PASS/DRIBBLE success
        if e_type in ("PASS", "DRIBBLE"):
            if outcome == "success":
                if prev_state == HPFAState.CONTROLLED:
                    return (
                        HPFAState.CONTROLLED,
                        PossessionEffect.CONTINUE,
                        f"transition:CONTROLLED+{e_type}_success->CONTROLLED_CONTINUE",
                    )
                # not defined by canon => ERROR
                return HPFAState.ERROR, PossessionEffect.NEUTRAL, f"undefined_transition:{prev_state.value}+{e_type}_success"

            # Canon v1.0.0: fail or missing outcome NOT defined -> UNVALIDATED (fail-closed, no speculation)
            return HPFAState.UNVALIDATED, PossessionEffect.NEUTRAL, f"unvalidated:{prev_state.value}+{e_type}_missing_or_fail"

        # TACKLE rules
        if e_type == "TACKLE":
            if prev_state == HPFAState.CONTROLLED:
                return HPFAState.CONTESTED, PossessionEffect.NEUTRAL, "transition:CONTROLLED+TACKLE->CONTESTED_NEUTRAL"
            if prev_state == HPFAState.CONTESTED:
                return HPFAState.CONTESTED, PossessionEffect.NEUTRAL, "transition:CONTESTED+TACKLE->CONTESTED_NEUTRAL"
            return HPFAState.ERROR, PossessionEffect.NEUTRAL, f"undefined_transition:{prev_state.value}+TACKLE"

        # INTERCEPTION rules
        if e_type == "INTERCEPTION":
            if prev_state in (HPFAState.CONTROLLED, HPFAState.CONTESTED):
                return HPFAState.CONTROLLED, PossessionEffect.START, f"transition:{prev_state.value}+INTERCEPTION->CONTROLLED_START"
            return HPFAState.ERROR, PossessionEffect.NEUTRAL, f"undefined_transition:{prev_state.value}+INTERCEPTION"

        # Unknown event => UNVALIDATED (fail-closed but non-crashing)
        return HPFAState.UNVALIDATED, PossessionEffect.NEUTRAL, f"unknown_event:{e_type}"
