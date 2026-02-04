from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from uuid import UUID

from canon.epistemic_meta import CanonMeta, EpistemicStatus
from adapters.engine.mapping_contract import load_action_map, MappingEntry
from adapters.engine.quarantine import QuarantineItem, quarantine_unknown


@dataclass
class CanonEvent:
    action: str
    meta: CanonMeta
    payload: Dict[str, Any]


def adapt_engine_events(
    engine_events: List[Dict[str, Any]],
    action_map_path: str
) -> Tuple[List[CanonEvent], List[QuarantineItem]]:
    amap = load_action_map(action_map_path)

    canon_events: List[CanonEvent] = []
    quarantine: List[QuarantineItem] = []

    for ev in engine_events:
        provider_action = str(ev.get("action", "")).strip()
        if not provider_action:
            quarantine.append(quarantine_unknown(provider_action="__MISSING__", raw_event=ev, reason="MISSING_ACTION"))
            continue

        entry = amap.get(provider_action)
        if entry is None:
            quarantine.append(quarantine_unknown(provider_action=provider_action, raw_event=ev, reason="UNMAPPED_ACTION"))
            continue

        meta = CanonMeta(
            epistemic_status=(EpistemicStatus.SIGNAL if entry.lossy else EpistemicStatus.FACT),
            lossy_mapping=entry.lossy,
            assumption_id=entry.assumption_id
        )

        canon_events.append(
            CanonEvent(
                action=entry.canon_action,
                meta=meta,
                payload=ev
            )
        )

    return canon_events, quarantine
