from enum import Enum
from dataclasses import dataclass


class EpistemicStatus(Enum):
    VALID = "VALID"
    UNVALIDATED = "UNVALIDATED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FALSIFIED = "FALSIFIED"


@dataclass
class Event:
    player_id: int | None
    team_id: int | None
    event_type: str | None
    zone: int | None


def evaluate_epistemic_status(event: Event) -> EpistemicStatus:
    # Class 10 — Identity
    if event.player_id is None or event.team_id is None:
        return EpistemicStatus.UNVALIDATED

    # Class 9 — Context
    if event.zone is None or not (1 <= event.zone <= 24):
        return EpistemicStatus.INCONCLUSIVE

    # Class 7 — Intent
    if event.event_type is None:
        return EpistemicStatus.INCONCLUSIVE

    # VALID
    return EpistemicStatus.VALID
