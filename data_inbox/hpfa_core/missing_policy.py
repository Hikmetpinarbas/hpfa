from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class PolicyResult:
    status: str  # VALID | UNVALIDATED
    reasons: List[str]


def validate_event_row(row: Dict[str, Any]) -> PolicyResult:
    """
    Event-stream policy (fail-closed, no defaults):
    Required:
      - actor_id
      - team_name
      - start_sec, end_sec
      - half
    """
    reasons: List[str] = []

    def missing(k: str) -> bool:
        v = row.get(k)
        return v is None or (isinstance(v, str) and v.strip() == "")

    required = ["actor_id", "team_name", "start_sec", "end_sec", "half"]
    for k in required:
        if missing(k):
            reasons.append(f"missing:{k}")

    if reasons:
        return PolicyResult(status="UNVALIDATED", reasons=reasons)
    return PolicyResult(status="VALID", reasons=[])


def validate_xlsx_row(row: Dict[str, Any]) -> PolicyResult:
    """
    Player-aggregate policy (XLSX feature store):
    Required:
      - player_name
      - team_name
    """
    reasons: List[str] = []

    def missing(k: str) -> bool:
        v = row.get(k)
        return v is None or (isinstance(v, str) and v.strip() == "")

    for k in ["player_name", "team_name"]:
        if missing(k):
            reasons.append(f"missing:{k}")

    if reasons:
        return PolicyResult(status="UNVALIDATED", reasons=reasons)
    return PolicyResult(status="VALID", reasons=[])
