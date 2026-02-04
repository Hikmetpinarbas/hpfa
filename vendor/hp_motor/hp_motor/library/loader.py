from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


SDCARD_ROOT = Path("/sdcard/HP_LIBRARY")


@dataclass(frozen=True)
class LibraryHealth:
    status: str  # OK | DEGRADED
    flags: List[str]
    roots_checked: List[str]


def _project_library_root() -> Path:
    # hp_motor/library
    return Path(__file__).resolve().parent


def _roots() -> List[Path]:
    return [
        _project_library_root(),  # hp_motor/library
        SDCARD_ROOT,              # /sdcard/HP_LIBRARY
    ]


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Some artifacts may be double-encoded (JSON string containing JSON).
    # Normalize until we get a dict, or fall back to empty dict.
    tries = 0
    while isinstance(data, str) and tries < 3:
        try:
            data = json.loads(data)
        except Exception:
            break
        tries += 1

    if not isinstance(data, dict):
        return {}
    return data


def _resolve(rel: str) -> Tuple[Path | None, LibraryHealth]:
    checked: List[str] = []
    for r in _roots():
        checked.append(str(r))
        p = r / rel
        if p.exists() and p.is_file():
            return p, LibraryHealth(status="OK", flags=[], roots_checked=checked)

    # Not found anywhere
    return None, LibraryHealth(
        status="DEGRADED",
        flags=[f"missing_artifact:{rel}"],
        roots_checked=checked,
    )


def load_registry() -> Tuple[Dict[str, Any], LibraryHealth]:
    p, h = _resolve("registry/metric_registry.json")
    if not p:
        return {"version": "missing", "metrics": []}, h
    return _read_json(p), h


def load_vendor_mappings() -> Tuple[Dict[str, Any], LibraryHealth]:
    p, h = _resolve("registry/vendor_mappings_compiled.json")
    if not p:
        return {"version": "missing", "vendor": {}}, h
    return _read_json(p), h


def library_health() -> LibraryHealth:
    # Aggregate health across required artifacts + schema sanity checks
    p1, h1 = _resolve("registry/metric_registry.json")
    p2, h2 = _resolve("registry/vendor_mappings_compiled.json")

    flags = list(dict.fromkeys(h1.flags + h2.flags))
    roots_checked = h1.roots_checked

    # Schema checks for metric registry
    if p1 and p1.exists():
        try:
            mr = _read_json(p1)
            metrics = mr.get("metrics")
            if not isinstance(metrics, list):
                flags.append("invalid_schema:metric_registry.metrics_not_list")
            else:
                for i, it in enumerate(metrics[:50]):
                    if not isinstance(it, dict):
                        flags.append(f"invalid_schema:metric_registry.item_not_dict:{i}")
                        break
                    if not str(it.get("id", "")).strip():
                        flags.append(f"invalid_schema:metric_registry.missing_id:{i}")
                        break
        except Exception as e:
            flags.append(f"invalid_json:metric_registry:{type(e).__name__}")

    # Schema checks for vendor mappings
    if p2 and p2.exists():
        try:
            vm = _read_json(p2)
            vend = vm.get("vendor")
            if not isinstance(vend, dict):
                flags.append("invalid_schema:vendor_mappings.vendor_not_dict")
            else:
                g = vend.get("generic")
                if g is not None and not isinstance(g, dict):
                    flags.append("invalid_schema:vendor_mappings.generic_not_dict")
        except Exception as e:
            flags.append(f"invalid_json:vendor_mappings:{type(e).__name__}")

    flags = list(dict.fromkeys(flags))
    status = "OK" if not flags else "DEGRADED"
    return LibraryHealth(status=status, flags=flags, roots_checked=roots_checked)

