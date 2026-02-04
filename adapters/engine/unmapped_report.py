import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

MAX_EXAMPLE_BYTES = 2048
MAX_EXAMPLES_PER_ACTION = 3


def _utc_now_iso_z(now: Optional[datetime] = None) -> str:
    dt = now if now is not None else datetime.now(timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _truncate_utf8(s: str, max_bytes: int) -> str:
    b = s.encode("utf-8", errors="replace")
    if len(b) <= max_bytes:
        return s
    ell = "…".encode("utf-8")
    cut = b[: max(0, max_bytes - len(ell))]
    return cut.decode("utf-8", errors="ignore") + "…"


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            ks = _truncate_utf8(str(k), 128)
            out[ks] = _normalize(obj[k])
        return out
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, tuple):
        return [_normalize(x) for x in obj]
    if isinstance(obj, str):
        return _truncate_utf8(obj, 512)
    return obj


def _trim_to_bytes(obj: Any, max_bytes: int = MAX_EXAMPLE_BYTES) -> Any:
    norm = _normalize(obj)
    s = _stable_json(norm)
    if len(s.encode("utf-8", errors="replace")) <= max_bytes:
        return norm

    prefix = _truncate_utf8(s, max_bytes)
    wrapper = {"_truncated": True, "_json_prefix": prefix}
    ws = _stable_json(wrapper)
    if len(ws.encode("utf-8", errors="replace")) <= max_bytes:
        return wrapper

    wrapper["_json_prefix"] = _truncate_utf8(prefix, max(64, max_bytes // 2))
    return wrapper


def generate_unmapped_actions_report(
    *,
    provider: str,
    quarantine_items: Iterable[Any],
    reports_dir: Path,
    now: Optional[datetime] = None,
) -> Path:
    """
    Writes reports/unmapped_actions.json with deterministic ordering.
    Expects each item to have fields (reason, provider_action, raw_event, ts_utc) OR be dict-like.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "unmapped_actions.json"

    # Only UNMAPPED_ACTION contributes to this report (other reasons can be added later)
    events: List[Dict[str, Any]] = []
    for qi in quarantine_items:
        if hasattr(qi, "__dict__") and not isinstance(qi, dict):
            d = asdict(qi)
        else:
            d = dict(qi)
        if d.get("reason") != "UNMAPPED_ACTION":
            continue
        events.append(d)

    by_action: Dict[str, List[Dict[str, Any]]] = {}
    for e in events:
        act = str(e.get("provider_action", "")).strip()
        by_action.setdefault(act, []).append(e)

    rows: List[Dict[str, Any]] = []
    for act, items in by_action.items():
        # deterministic example selection: sort by stable json of raw_event
        sorted_items = sorted(items, key=_stable_json)
        examples = []
        for it in sorted_items[:MAX_EXAMPLES_PER_ACTION]:
            raw = it.get("raw_event", {})
            examples.append(_trim_to_bytes(raw, MAX_EXAMPLE_BYTES))

        rows.append(
            {
                "provider_action": act,
                "count": len(items),
                "examples": examples,
            }
        )

    # sort by count desc then provider_action asc
    rows.sort(key=lambda r: (-int(r["count"]), str(r["provider_action"])))

    report = {
        "provider": provider,
        "generated_at_utc": _utc_now_iso_z(now),
        "unmapped_actions": rows,
    }

    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def maybe_write_unmapped_report(provider: str, quarantine_items: List[Any]) -> Optional[Path]:
    """
    Side-effect is gated by HPFA_REPORTS_DIR. If env var not set, no write.
    """
    d = os.environ.get("HPFA_REPORTS_DIR", "").strip()
    if not d:
        return None
    return generate_unmapped_actions_report(
        provider=provider,
        quarantine_items=quarantine_items,
        reports_dir=Path(d),
        now=None,
    )
