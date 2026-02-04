from __future__ import annotations
from typing import Any, Dict, List
from hp_motor.library.loader import load_vendor_mappings

def _to_int(v: Any, d: int = 0) -> int:
    try: return int(float(v))
    except Exception: return d

def _to_float(v: Any, d: float = 0.0) -> float:
    try: return float(v)
    except Exception: return d

def normalize_events(events: List[Dict[str, Any]], vendor: str = "generic") -> List[Dict[str, Any]]:
    mappings, _ = load_vendor_mappings()

    # type guard: loader may return json string/path instead of dict
    try:
        import json
        from pathlib import Path as _P
        if isinstance(mappings, str):
            _pp = _P(mappings)
            if _pp.exists():
                mappings = json.loads(_pp.read_text(encoding="utf-8"))
            else:
                mappings = json.loads(mappings)
        if not isinstance(mappings, dict):
            mappings = {}
    except Exception:
        mappings = {}

        # normalize vendor field: vendor mappings may be json string (double-encoded)
    try:
        import json
        vend = mappings.get("vendor", {})
        tries = 0
        while isinstance(vend, str) and tries < 3:
            vend = json.loads(vend)
            tries += 1
        if not isinstance(vend, dict):
            vend = {}
        mappings["vendor"] = vend
    except Exception:
        mappings["vendor"] = {}

    vmap = mappings.get("vendor", {}).get(vendor) or mappings.get("vendor", {}).get("generic", {})
    out: List[Dict[str, Any]] = []
    for e in events:
        ne: Dict[str, Any] = {}
        for ck, vk in vmap.items():
            if vk in e: ne[ck] = e[vk]
        for k in ["match_id","team_id","period","minute","second","event_type","player_id",
                  "possession_id","sequence_id","start_x","start_y","end_x","end_y","outcome","sot","set_piece_state","phase"]:
            if k in e and k not in ne: ne[k] = e[k]

        ne["period"] = _to_int(ne.get("period", 1), 1)
        ne["minute"] = _to_int(ne.get("minute", 0), 0)
        ne["second"] = _to_int(ne.get("second", 0), 0)
        for fk in ["start_x","start_y","end_x","end_y"]:
            if fk in ne: ne[fk] = _to_float(ne[fk], 0.0)
        ne["event_type"] = str(ne.get("event_type","")).strip().lower()
        if "outcome" in ne: ne["outcome"] = str(ne["outcome"]).strip().lower()
        out.append(ne)
    return out
