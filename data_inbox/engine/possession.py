from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List


# -----------------------------
# Canonical Enums
# -----------------------------
class PossessionState(str, Enum):
    NO_POSSESSION = "NO_POSSESSION"
    CONTROLLED = "CONTROLLED"
    CONTESTED = "CONTESTED"
    DEAD_BALL = "DEAD_BALL"
    UNVALIDATED = "UNVALIDATED"


class EpistemicStatus(str, Enum):
    VALID = "VALID"
    UNVALIDATED = "UNVALIDATED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FALSIFIED = "FALSIFIED"


class EventType(str, Enum):
    RESTART = "RESTART"
    PASS = "PASS"
    SHOT = "SHOT"
    INTERCEPTION = "INTERCEPTION"
    TACKLE = "TACKLE"
    OUT = "OUT"
    FOUL = "FOUL"
    OFFSIDE = "OFFSIDE"
    UNKNOWN = "UNKNOWN"


# SHOT outcomes (canonical)
class ShotOutcome(str, Enum):
    GOAL = "GOAL"
    SAVED = "SAVED"
    OFF_TARGET = "OFF_TARGET"
    UNKNOWN = "UNKNOWN"


# PASS / other outcomes (canonical)
class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass
class CanonEvent:
    """
    Minimal canonical event representation for possession engine.

    Required for fail-closed identity:
      - player_id (int|None)
      - team_id   (int|None)

    Required for state machine:
      - event_type (EventType)
      - outcome (Outcome) or shot_outcome (ShotOutcome) for SHOT
      - qualifiers: provider-specific flags -> normalized keys
          * GK_HOLDS (bool) (only meaningful for SHOT SAVED)
          * WON_BALL (bool) (for TACKLE)
          * WINNER_TEAM_ID (int) (for INTERCEPTION, optional)
    """
    event_id: str
    team_id: Optional[int]
    player_id: Optional[int]
    event_type: EventType

    # General outcome
    outcome: Outcome = Outcome.UNKNOWN

    # Shot-specific outcome
    shot_outcome: ShotOutcome = ShotOutcome.UNKNOWN

    qualifiers: Dict[str, Any] = field(default_factory=dict)

    # Epistemic status comes from upstream validator
    epistemic: EpistemicStatus = EpistemicStatus.VALID


@dataclass
class PossessionFrame:
    event_id: str
    state_before: PossessionState
    state_after: PossessionState

    possession_id_before: Optional[int]
    possession_id_after: Optional[int]

    possessing_team_before: Optional[int]
    possessing_team_after: Optional[int]

    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PossessionEngine:
    """
    HPFA Possession State Machine v0.1 (fail-closed)

    Key invariants:
      - Identity missing => UNVALIDATED, possession_id=NULL, excluded from downstream
      - UNKNOWN/MISSING event => UNVALIDATED, possession_id=NULL
      - CONTESTED unresolved => contested_count increases; does not auto-end
    """
    scramble_timeout_events: int = 5

    # Runtime state
    state: PossessionState = PossessionState.NO_POSSESSION
    possession_id: Optional[int] = None
    possessing_team_id: Optional[int] = None
    contested_count: int = 0

    def _new_possession(self, team_id: Optional[int]) -> None:
        if team_id is None:
            # fail-closed: cannot assign possession without team
            self.possession_id = None
            self.possessing_team_id = None
            return
        self.possession_id = 1 if self.possession_id is None else (self.possession_id + 1)
        self.possessing_team_id = team_id
        self.contested_count = 0

    def step(self, ev: CanonEvent) -> PossessionFrame:
        sb = self.state
        pid_b = self.possession_id
        team_b = self.possessing_team_id

        flags: Dict[str, Any] = {}

        # -----------------------------
        # FAIL-CLOSED: Identity gate
        # -----------------------------
        if ev.player_id is None or ev.team_id is None:
            self.state = PossessionState.UNVALIDATED
            self.possession_id = None
            self.possessing_team_id = None
            flags["fail_closed"] = "MISSING_IDENTITY"
            return PossessionFrame(
                event_id=ev.event_id,
                state_before=sb,
                state_after=self.state,
                possession_id_before=pid_b,
                possession_id_after=self.possession_id,
                possessing_team_before=team_b,
                possessing_team_after=self.possessing_team_id,
                flags=flags,
            )

        # -----------------------------
        # FAIL-CLOSED: Epistemic gate
        # -----------------------------
        # If upstream marked UNVALIDATED/FALSIFIED, we do not propagate possession.
        if ev.epistemic in (EpistemicStatus.UNVALIDATED, EpistemicStatus.FALSIFIED):
            self.state = PossessionState.UNVALIDATED
            self.possession_id = None
            self.possessing_team_id = None
            flags["fail_closed"] = f"EPISTEMIC_{ev.epistemic}"
            return PossessionFrame(
                event_id=ev.event_id,
                state_before=sb,
                state_after=self.state,
                possession_id_before=pid_b,
                possession_id_after=self.possession_id,
                possessing_team_before=team_b,
                possessing_team_after=self.possessing_team_id,
                flags=flags,
            )

        # -----------------------------
        # UNKNOWN/MISSING event_type
        # -----------------------------
        if ev.event_type == EventType.UNKNOWN:
            self.state = PossessionState.UNVALIDATED
            self.possession_id = None
            self.possessing_team_id = None
            flags["fail_closed"] = "UNKNOWN_EVENT_TYPE"
            return PossessionFrame(
                event_id=ev.event_id,
                state_before=sb,
                state_after=self.state,
                possession_id_before=pid_b,
                possession_id_after=self.possession_id,
                possessing_team_before=team_b,
                possessing_team_after=self.possessing_team_id,
                flags=flags,
            )

        # -----------------------------
        # State machine
        # -----------------------------
        # Helper: ensure we have a possession when entering controlled
        def ensure_possession(team_id: int) -> None:
            if self.possession_id is None or self.possessing_team_id != team_id:
                self._new_possession(team_id)

        # NO_POSSESSION
        if self.state == PossessionState.NO_POSSESSION:
            if ev.event_type == EventType.RESTART and ev.outcome == Outcome.SUCCESS:
                self.state = PossessionState.CONTROLLED
                ensure_possession(ev.team_id)
            else:
                # remain fail-closed conservative
                self.state = PossessionState.UNVALIDATED
                self.possession_id = None
                self.possessing_team_id = None
                flags["fail_closed"] = "NO_POSSESSION_NON_RESTART"
            return self._frame(ev, sb, pid_b, team_b, flags)

        # DEAD_BALL
        if self.state == PossessionState.DEAD_BALL:
            if ev.event_type == EventType.RESTART and ev.outcome == Outcome.SUCCESS:
                self.state = PossessionState.CONTROLLED
                ensure_possession(ev.team_id)
            elif ev.event_type in (EventType.OUT, EventType.FOUL, EventType.OFFSIDE):
                # stays dead ball; possession does not change until restart
                self.state = PossessionState.DEAD_BALL
            else:
                # conservative: dead ball only transitions on restart or dead-ball events
                flags["warn"] = "DEAD_BALL_UNEXPECTED_EVENT"
            return self._frame(ev, sb, pid_b, team_b, flags)

        # UNVALIDATED
        if self.state == PossessionState.UNVALIDATED:
            # Only a valid restart can restore
            if ev.event_type == EventType.RESTART and ev.outcome == Outcome.SUCCESS:
                self.state = PossessionState.CONTROLLED
                ensure_possession(ev.team_id)
            else:
                self.possession_id = None
                self.possessing_team_id = None
            return self._frame(ev, sb, pid_b, team_b, flags)

        # CONTROLLED
        if self.state == PossessionState.CONTROLLED:
            ensure_possession(self.possessing_team_id or ev.team_id)

            # PASS
            if ev.event_type == EventType.PASS:
                if ev.outcome == Outcome.SUCCESS:
                    self.state = PossessionState.CONTROLLED
                elif ev.outcome == Outcome.FAIL:
                    self.state = PossessionState.CONTESTED
                    self.contested_count = 0
                else:
                    # outcome unknown -> fail-closed UNVALIDATED
                    self.state = PossessionState.UNVALIDATED
                    self.possession_id = None
                    self.possessing_team_id = None
                    flags["fail_closed"] = "CONTROLLED_OUTCOME_UNKNOWN"

            # SHOT
            elif ev.event_type == EventType.SHOT:
                if ev.shot_outcome == ShotOutcome.GOAL:
                    self.state = PossessionState.DEAD_BALL
                    # possession ends at restart; keep current id until restart
                elif ev.shot_outcome == ShotOutcome.OFF_TARGET:
                    self.state = PossessionState.DEAD_BALL
                elif ev.shot_outcome == ShotOutcome.SAVED:
                    gk_holds = bool(ev.qualifiers.get("GK_HOLDS", False))
                    if gk_holds:
                        # GK control -> new possession for GK team_id (event team is GK team by assumption)
                        self.state = PossessionState.CONTROLLED
                        self._new_possession(ev.team_id)
                    else:
                        self.state = PossessionState.CONTESTED
                        self.contested_count = 0
                else:
                    self.state = PossessionState.UNVALIDATED
                    self.possession_id = None
                    self.possessing_team_id = None
                    flags["fail_closed"] = "SHOT_OUTCOME_UNKNOWN"

            # OUT/FOUL/OFFSIDE forces dead ball
            elif ev.event_type in (EventType.OUT, EventType.FOUL, EventType.OFFSIDE):
                self.state = PossessionState.DEAD_BALL

            # INTERCEPTION/TACKLE while controlled is treated as contested unless explicit winner
            elif ev.event_type in (EventType.INTERCEPTION, EventType.TACKLE):
                # If provider already states winner, jump to controlled new possession
                winner = ev.qualifiers.get("WINNER_TEAM_ID")
                if isinstance(winner, int):
                    self.state = PossessionState.CONTROLLED
                    self._new_possession(winner)
                else:
                    self.state = PossessionState.CONTESTED
                    self.contested_count = 0

            else:
                flags["warn"] = f"CONTROLLED_UNHANDLED_{ev.event_type}"

            return self._frame(ev, sb, pid_b, team_b, flags)

        # CONTESTED
        if self.state == PossessionState.CONTESTED:
            # contested chain
            self.contested_count += 1
            if self.contested_count >= self.scramble_timeout_events:
                flags["scramble_timeout"] = True
                # stays contested; no forced end (per spec)
                self.contested_count = self.scramble_timeout_events

            # Interception success -> new possession
            if ev.event_type == EventType.INTERCEPTION and ev.outcome == Outcome.SUCCESS:
                winner = ev.qualifiers.get("WINNER_TEAM_ID", ev.team_id)
                self.state = PossessionState.CONTROLLED
                self._new_possession(int(winner))

            # Tackle with WON_BALL
            elif ev.event_type == EventType.TACKLE:
                won = ev.qualifiers.get("WON_BALL")
                if won is True:
                    self.state = PossessionState.CONTROLLED
                    self._new_possession(ev.team_id)
                elif won is False:
                    self.state = PossessionState.CONTESTED
                else:
                    # unknown tackle resolution -> epistemically INCONCLUSIVE, but possession engine marks contested
                    flags["scramble_flag"] = True
                    self.state = PossessionState.CONTESTED

            # Pass success during contested: treat as control establishment (same team)
            elif ev.event_type == EventType.PASS and ev.outcome == Outcome.SUCCESS:
                self.state = PossessionState.CONTROLLED
                self._new_possession(ev.team_id)

            # Dead ball triggers
            elif ev.event_type in (EventType.OUT, EventType.FOUL, EventType.OFFSIDE):
                self.state = PossessionState.DEAD_BALL

            # Unknown outcome handling
            elif ev.outcome == Outcome.UNKNOWN and ev.event_type != EventType.SHOT:
                flags["scramble_flag"] = True
                # remain contested; no possession change

            return self._frame(ev, sb, pid_b, team_b, flags)

        # fallback fail-closed
        self.state = PossessionState.UNVALIDATED
        self.possession_id = None
        self.possessing_team_id = None
        flags["fail_closed"] = "UNREACHABLE_STATE"
        return self._frame(ev, sb, pid_b, team_b, flags)

    def _frame(self, ev: CanonEvent, sb: PossessionState, pid_b: Optional[int], team_b: Optional[int], flags: Dict[str, Any]) -> PossessionFrame:
        return PossessionFrame(
            event_id=ev.event_id,
            state_before=sb,
            state_after=self.state,
            possession_id_before=pid_b,
            possession_id_after=self.possession_id,
            possessing_team_before=team_b,
            possessing_team_after=self.possessing_team_id,
            flags=flags,
        )


def simulate(events: List[CanonEvent], scramble_timeout_events: int = 5) -> List[PossessionFrame]:
    pe = PossessionEngine(scramble_timeout_events=scramble_timeout_events)
    out: List[PossessionFrame] = []
    for ev in events:
        out.append(pe.step(ev))
    return out
