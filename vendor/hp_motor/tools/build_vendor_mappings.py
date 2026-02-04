#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build vendor_mappings.json by matching vendor metric labels to canonical metric_registry.json.

Inputs (expected in hp_motor/library/registry/inputs/vendor/):
- hp_metric_registry_sportsbase_v1_1.json OR .csv  (preferred)
- sportsbase_metrics_hp_v1.json (optional, extra aliases)

Canonical:
- hp_motor/library/registry/metric_registry.json

Outputs:
- hp_motor/library/registry/vendor_mappings.json
- artifacts/registry/unmapped_vendor_metrics.json

Philosophy:
- never hard-block; produce DEGRADED + unmapped report
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(".")
REG_PATH = Path("hp_motor/library/registry/metric_registry.json")
VENDOR_DIR = Path("hp_motor/library/registry/inputs/vendor")
OUT_PATH = Path("hp_motor/library/registry/vendor_mappings.json")
ART_DIR = Path("artifacts/registry")
ART_DIR.mkdir(parents=True, exist_ok=True)

RX = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def norm(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = (s.replace("ı","i").replace("ğ","g").replace("ü","u").replace("ş","s").replace("ö","o").replace("ç","c"))
    return RX.sub("_", s).strip("_")

def load_json(p: Path) -> Any:
    return json.load(p.open("r", encoding="utf-8"))

def load_csv(p: Path) -> List[Dict[str, str]]:
    with p.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def iter_records(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, dict) and "metrics" in obj and isinstance(obj["metrics"], list):
        return [r for r in obj["metrics"] if isinstance(r, dict)]
    if isinstance(obj, dict) and "rows" in obj and isinstance(obj["rows"], list):
        return [r for r in obj["rows"] if isinstance(r, dict)]
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        # dict keyed by id
        out = []
        for k, v in obj.items():
            if isinstance(v, dict):
                vv = dict(v)
                vv.setdefault("id", k)
                out.append(vv)
        return out
    return []

def build_canonical_lookup(reg: Dict[str, Any]) -> Dict[str, str]:
    """
    Returns: normalized_key -> canonical_metric_id
    Uses: id + vendor_label + aliases/vendor_labels if present
    """
    lookup: Dict[str, str] = {}
    metrics = reg.get("metrics", [])
    for m in metrics:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid:
            continue

        keys = []
        for k in ["id", "metric_id", "metric", "name", "name_tr", "vendor_label", "display_name", "display_name_tr"]:
            v = m.get(k)
            if isinstance(v, str) and v.strip():
                keys.append(v)

        for lk in ["aliases", "vendor_labels", "synonyms"]:
            vls = m.get(lk) or []
            if isinstance(vls, list):
                for x in vls:
                    if isinstance(x, str) and x.strip():
                        keys.append(x)
                    elif isinstance(x, dict):
                        lbl = x.get("label") or x.get("name") or x.get("value")
                        if isinstance(lbl, str) and lbl.strip():
                            keys.append(lbl)

        for k in keys:
            nk = norm(k)
            if nk and nk not in lookup:
                lookup[nk] = mid

    return lookup

def pick_first(d: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        v = d.get(c)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def parse_vendor_files() -> List[Dict[str, Any]]:
    """
    Load vendor records from preferred sources if they exist.
    """
    records: List[Dict[str, Any]] = []

    # prefer hp_metric_registry_sportsbase_v1_1.json/csv
    pref_json = VENDOR_DIR / "hp_metric_registry_sportsbase_v1_1.json"
    pref_csv  = VENDOR_DIR / "hp_metric_registry_sportsbase_v1_1.csv"

    if pref_json.exists():
        records += iter_records(load_json(pref_json))
    elif pref_csv.exists():
        records += load_csv(pref_csv)

    # extra: sportsbase_metrics_hp_v1.json may add definitions/aliases
    sb_json = VENDOR_DIR / "sportsbase_metrics_hp_v1.json"
    if sb_json.exists():
        # keep as separate source by merging into records list too
        records += iter_records(load_json(sb_json))

    # fallback: any other json/csv in vendor dir
    for p in sorted(VENDOR_DIR.glob("*")):
        if p.name in {pref_json.name, pref_csv.name, sb_json.name}:
            continue
        if p.suffix.lower() == ".json":
            try:
                records += iter_records(load_json(p))
            except Exception:
                pass
        if p.suffix.lower() == ".csv":
            try:
                records += load_csv(p)
            except Exception:
                pass

    return records

def main() -> int:
    if not REG_PATH.exists():
        raise SystemExit(f"Missing canonical registry: {REG_PATH}")
    if not VENDOR_DIR.exists():
        raise SystemExit(f"Missing vendor inputs dir: {VENDOR_DIR}")

    reg = load_json(REG_PATH)
    canon_lookup = build_canonical_lookup(reg)

    vendor_records = parse_vendor_files()

    # Heuristic field candidates
    vendor_label_fields = ["vendor_label", "metric", "label", "name", "metric_name", "vendorMetric", "vendor_metric"]
    vendor_id_fields    = ["vendor_id", "sb_id", "sportsbase_id", "id", "metric_id", "sb_metric_id"]
    vendor_def_tr_fields= ["definition_tr", "definition", "def_tr", "desc_tr"]

    mappings: List[Dict[str, Any]] = []
    unmapped: List[Dict[str, Any]] = []

    seen = set()

    for r in vendor_records:
        if not isinstance(r, dict):
            continue

        vlabel = pick_first(r, vendor_label_fields)
        vid    = pick_first(r, vendor_id_fields)
        dtr    = pick_first(r, vendor_def_tr_fields)

        # ignore empty rows
        if not (vlabel or vid):
            continue

        # choose a matching key (try label then id)
        candidates = []
        if vlabel: candidates.append(vlabel)
        if vid: candidates.append(vid)

        match_id: Optional[str] = None
        matched_key: Optional[str] = None
        for c in candidates:
            nk = norm(c)
            if nk in canon_lookup:
                match_id = canon_lookup[nk]
                matched_key = nk
                break

        if match_id:
            key = (match_id, norm(vlabel or vid or ""))
            if key in seen:
                continue
            seen.add(key)
            mappings.append({
                "vendor": "sportsbase",
                "vendor_label": vlabel or "",
                "vendor_id": vid or "",
                "canonical_metric_id": match_id,
                "match_key": matched_key,
                "definition_tr_vendor": dtr or ""
            })
        else:
            unmapped.append({
                "vendor": "sportsbase",
                "vendor_label": vlabel or "",
                "vendor_id": vid or "",
                "hint_norm": [norm(x) for x in candidates if x],
            })

    out = {
        "vendor": "sportsbase",
        "generated_from": str(VENDOR_DIR),
        "count_mapped": len(mappings),
        "count_unmapped": len(unmapped),
        "mappings": mappings,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART_DIR / "unmapped_vendor_metrics.json").write_text(json.dumps(unmapped, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK: vendor mappings built")
    print("mapped:", len(mappings))
    print("unmapped:", len(unmapped))
    print("out:", OUT_PATH)
    print("unmapped_report:", ART_DIR / "unmapped_vendor_metrics.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
