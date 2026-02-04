import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class QuarantineItem:
    reason: str
    provider_action: str
    raw_event: Dict[str, Any]
    ts_utc: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def quarantine_unknown(provider_action: str, raw_event: Dict[str, Any], reason: str = "UNMAPPED_ACTION") -> QuarantineItem:
    return QuarantineItem(
        reason=reason,
        provider_action=provider_action,
        raw_event=raw_event,
        ts_utc=now_utc_iso()
    )


def write_quarantine(path: str, items: List[QuarantineItem]) -> None:
    payload = [asdict(x) for x in items]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
