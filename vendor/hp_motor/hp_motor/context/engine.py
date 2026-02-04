from __future__ import annotations
from typing import Any, Dict, List, Tuple

def apply_context(metrics_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    # Lite: identity adjustment + flags
    flags = ["context:identity_v0"]
    adj = {"meta": dict(metrics_raw.get("meta", {})), "metrics": {}}
    for mid, p in metrics_raw.get("metrics", {}).items():
        adj["metrics"][mid] = {
            "value": p.get("value"),
            "status": p.get("status"),
            "adjustment": {"method": "identity_v0", "note": "Lite Core: adjustments deferred; flags provided."}
        }
    return adj, flags
