from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID


class EpistemicStatus(str, Enum):
    FACT = "fact"
    OPINION = "opinion"
    HYPOTHESIS = "hypothesis"
    SIGNAL = "signal"


@dataclass(frozen=True)
class CanonMeta:
    epistemic_status: EpistemicStatus
    lossy_mapping: bool
    assumption_id: Optional[UUID] = None
    human_override: bool = False
