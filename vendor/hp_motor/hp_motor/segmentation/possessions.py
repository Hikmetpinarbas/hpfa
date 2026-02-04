from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Possession:
    possession_id: str
    team_id: Any
    start_idx: int
    end_idx: int


def segment_possessions(events: List[Dict[str, Any]]) -> List[Possession]:
    """
    Deterministic lite possession segmentation.

    Rules:
    - If possession_id exists: contiguous runs
    - Else: fallback to team_id runs (DEGRADED but stable)
    """
    if not events:
        return []

    possessions: List[Possession] = []

    def _pid(i: int) -> str:
        pid = events[i].get("possession_id")
        if pid in (None, ""):
            return f"fallback_team_{events[i].get('team_id', 'NA')}"
        return str(pid)

    cur_pid = _pid(0)
    cur_team = events[0].get("team_id")
    start = 0

    for i in range(1, len(events)):
        pid = _pid(i)
        if pid != cur_pid:
            possessions.append(
                Possession(
                    possession_id=cur_pid,
                    team_id=cur_team,
                    start_idx=start,
                    end_idx=i - 1,
                )
            )
            cur_pid = pid
            cur_team = events[i].get("team_id")
            start = i

    possessions.append(
        Possession(
            possession_id=cur_pid,
            team_id=cur_team,
            start_idx=start,
            end_idx=len(events) - 1,
        )
    )
    return possessions
