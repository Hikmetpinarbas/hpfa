from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from hp_motor.segmentation.possessions import Possession


@dataclass
class Sequence:
    sequence_id: str
    possession_id: str
    team_id: Any
    start_idx: int
    end_idx: int
    phase: str
    set_piece_state: str


def segment_sequences(
    events: List[Dict[str, Any]],
    possessions: List[Possession],
) -> List[Sequence]:
    """
    Lite sequence segmentation:
    - Each possession split by phase OR set-piece change
    """
    sequences: List[Sequence] = []

    for p in possessions:
        start = p.start_idx
        cur_phase = events[start].get("phase", "P1_ATTACK_BUILD")
        cur_sp = events[start].get("set_piece_state", "open_play")
        seq_idx = 0

        for i in range(p.start_idx + 1, p.end_idx + 1):
            ph = events[i].get("phase", cur_phase)
            sp = events[i].get("set_piece_state", cur_sp)

            if ph != cur_phase or sp != cur_sp:
                sequences.append(
                    Sequence(
                        sequence_id=f"{p.possession_id}_seq_{seq_idx}",
                        possession_id=p.possession_id,
                        team_id=p.team_id,
                        start_idx=start,
                        end_idx=i - 1,
                        phase=cur_phase,
                        set_piece_state=cur_sp,
                    )
                )
                seq_idx += 1
                start = i
                cur_phase = ph
                cur_sp = sp

        sequences.append(
            Sequence(
                sequence_id=f"{p.possession_id}_seq_{seq_idx}",
                possession_id=p.possession_id,
                team_id=p.team_id,
                start_idx=start,
                end_idx=p.end_idx,
                phase=cur_phase,
                set_piece_state=cur_sp,
            )
        )

    return sequences
