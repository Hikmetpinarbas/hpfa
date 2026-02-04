import json
from dataclasses import dataclass
from typing import Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class MappingEntry:
    canon_action: str
    lossy: bool
    assumption_id: UUID


def load_action_map(path: str) -> Dict[str, MappingEntry]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    out: Dict[str, MappingEntry] = {}
    for provider_action, spec in raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"Invalid mapping spec for {provider_action}: not an object")

        for k in ("canon_action", "lossy", "assumption_id"):
            if k not in spec:
                raise ValueError(f"Mapping for {provider_action} missing key: {k}")

        canon_action = spec["canon_action"]
        lossy = spec["lossy"]
        assumption_id = UUID(spec["assumption_id"])

        if not isinstance(canon_action, str) or not canon_action.strip():
            raise ValueError(f"Invalid canon_action for {provider_action}")

        if not isinstance(lossy, bool):
            raise ValueError(f"Invalid lossy flag for {provider_action}")

        out[provider_action] = MappingEntry(
            canon_action=canon_action.strip(),
            lossy=lossy,
            assumption_id=assumption_id
        )
    return out
