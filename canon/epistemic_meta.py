"""
Epistemic metadata for canon events produced by the adapter layer.

EpistemicStatus.FACT   — lossless mapping: provider action maps 1-to-1 to a canon action
                         with no information dropped.
EpistemicStatus.SIGNAL — lossy mapping: the canon action is the best available
                         representation but some provider detail is discarded.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class EpistemicStatus(str, Enum):
    FACT = "FACT"
    SIGNAL = "SIGNAL"


@dataclass(frozen=True)
class CanonMeta:
    epistemic_status: EpistemicStatus
    lossy_mapping: bool
    assumption_id: UUID
