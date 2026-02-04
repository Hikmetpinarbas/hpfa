#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARTIFACTS_DIR = Path("artifacts") / "registry"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

NORMALIZE_RX = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def norm_key(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = (s.replace("ı", "i")
           .replace("ğ", "g")
           .replace("ü", "u")
           .replace("ş", "s")
           .replace("ö", "o")
           .replace("ç", "c"))
    return NORMALIZE_RX.sub("_", s).strip("_")

@dataclass
class DefHit:
    tr: Optional[str]
    en: Optional[str]
    source: str
    confidence: float

def coerce_text(x: Any) -> Optional[str]:
    if isinstance(x, str):
        return x.strip() or None
    if isinstance(x, dict):
        for k in ["tr", "en", "text", "description", "value", "content"]:
            v = x.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in x.values():
            t = coerce_text(v)
            if t:
                return t
    if isinstance(x, list):
        for it in x:
            t = coerce_text(it)
            if t:
                return t
    return None

def extract_defs(r: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    defs = r.get("definitions")
    tr = en = None

    if isinstance(defs, dict):
        if "tr" in defs or "en" in defs:
            tr = coerce_text(defs.get("tr"))
            en = coerce_text(defs.get("en"))
        else:
            for tier in ["basic", "medium", "academic"]:
                if tier in defs:
                    picked = defs[tier]
                    tr = coerce_text(picked)
                    break

    if not tr:
        tr = coerce_text(r.get("definition_tr") or r.get("definition"))
    if not en:
        en = coerce_text(r.get("definition_en"))

    return tr, en

def extract_aliases(r: Dict[str, Any]) -> List[str]:
    out = []
    for k in ["aliases", "vendor_aliases", "vendor_labels"]:
        v = r.get(k)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    out.append(it)
                elif isinstance(it, dict):
                    lbl = it.get("label") or it.get("name")
                    if lbl:
                        out.append(lbl)
    return out

def load_json(p: Path):
    return json.load(p.open("r", encoding="utf-8"))

def load_csv(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build_lookup(inputs: Path) -> Dict[str, DefHit]:
    lookup: Dict[str, DefHit] = {}

    for p in inputs.rglob("*"):
        if p.is_dir():
            continue

        try:
            if p.suffix == ".json":
                obj = load_json(p)
                records = obj["metrics"] if isinstance(obj, dict) and "metrics" in obj else obj
            elif p.suffix == ".csv":
                records = load_csv(p)
            else:
                continue

            for r in records:
                tr, en = extract_defs(r)
                if not (tr or en):
                    continue

                hit = DefHit(tr, en, str(p), 0.9)

                for key in [
                    r.get("id"),
                    r.get("name"),
                    r.get("name_tr"),
                    r.get("metric"),
                ] + extract_aliases(r):
                    k = norm_key(key)
                    if k:
                        lookup[k] = hit

        except Exception:
            continue

    return lookup

def enrich(registry: Path, inputs: Path):
    reg = load_json(registry)
    metrics = reg.get("metrics", [])
    lookup = build_lookup(inputs)

    filled = 0
    missing = []

    for m in metrics:
        if m.get("definition_tr") or m.get("definition_en"):
            continue

        keys = [norm_key(m.get("id")), norm_key(m.get("metric")), norm_key(m.get("vendor_label"))]
        hit = next((lookup[k] for k in keys if k in lookup), None)

        if hit:
            m["definition_tr"] = hit.tr
            m["definition_en"] = hit.en
            m["definition_source"] = hit.source
            m["definition_confidence"] = hit.confidence
            filled += 1
        else:
            missing.append(m.get("id"))

    json.dump(reg, registry.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

    review = {
        "filled": filled,
        "missing": missing,
        "lookup_size": len(lookup)
    }
    json.dump(review, (ARTIFACTS_DIR / "enrichment_review.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("OK")
    print("Filled:", filled)
    print("Missing:", len(missing))
    print("Lookup:", len(lookup))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--inputs", required=True)
    args = ap.parse_args()
    enrich(Path(args.registry), Path(args.inputs))

if __name__ == "__main__":
    main()
