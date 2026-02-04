from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ----------------------------
# Helpers
# ----------------------------
def slugify(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:64] if len(s) > 64 else s


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def backup_file(path: Path, backup_dir: Path) -> None:
    if not path.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"{path.name}.bak_{ts}"
    dst.write_bytes(path.read_bytes())


# ----------------------------
# HP mappings (Lite)
# ----------------------------
ROLE_TO_MECH = {
    "intent": ["kontrol"],
    "skill": ["kontrol"],
    "success": ["deger"],
    "reward": ["deger"],
    "risk": ["risk"],
    "value": ["deger"],
}

DEFAULT_LAYER = "micro"  # vendor sheet çoğunlukla maç başı aggregate; Lite core'da micro etiketiyle başlatıyoruz.


def build_from_sportsbase(sb: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    phases = sb.get("phases", [])
    metrics_rows = sb.get("metrics", [])

    # phase index
    phase_index = {p.get("phase_id"): p for p in phases}

    # group rows by vendor label
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in metrics_rows:
        label = str(r.get("metric", "")).strip()
        if not label:
            continue
        grouped[label].append(r)

    # produce canonical metrics
    canonical_metrics: List[Dict[str, Any]] = []
    vendor_map: Dict[str, str] = {}
    unmapped: Dict[str, Any] = {
        "missing_definition": [],
        "missing_sources": [],
        "role_conflicts": [],
        "unit_conflicts": [],
        "notes": [],
    }

    # deterministic id namespace
    used_ids = set()

    def alloc_id(label: str) -> str:
        base = f"SB_{slugify(label)}".upper()
        if base not in used_ids:
            used_ids.add(base)
            return base
        # collision: suffix counter
        i = 2
        while f"{base}_{i}" in used_ids:
            i += 1
        new = f"{base}_{i}"
        used_ids.add(new)
        return new

    for label, rows in sorted(grouped.items(), key=lambda kv: kv[0].lower()):
        cid = alloc_id(label)
        vendor_map[label] = cid

        role_counts = Counter([str(r.get("role_guess", "")).strip().lower() for r in rows if r.get("role_guess") is not None])
        role = role_counts.most_common(1)[0][0] if role_counts else "unknown"
        role_hints = [rk for rk, _ in role_counts.most_common() if rk and rk != "unknown"]

        if len(role_hints) > 1:
            unmapped["role_conflicts"].append({"metric": label, "roles": role_hints})

        mechs = ROLE_TO_MECH.get(role, ["UNKNOWN"])
        unit_counts = Counter([str(r.get("unit_or_type", "")).strip() for r in rows if r.get("unit_or_type") is not None])
        unit = unit_counts.most_common(1)[0][0] if unit_counts else ""

        if len(unit_counts) > 1:
            unmapped["unit_conflicts"].append({"metric": label, "units": [u for u, _ in unit_counts.most_common()]})

        # phase coverage
        phase_ids = sorted({str(r.get("phase_id", "")).strip() for r in rows if r.get("phase_id")})
        phase_names = []
        for pid in phase_ids:
            p = phase_index.get(pid, {})
            phase_names.append(p.get("phase_name", ""))

        # pick definition / sources (if any row has it)
        defs = [str(r.get("definition_tr", "")).strip() for r in rows if str(r.get("definition_tr", "")).strip()]
        srcs = [str(r.get("source_urls", "")).strip() for r in rows if str(r.get("source_urls", "")).strip()]

        definition_tr = defs[0] if defs else ""
        source_urls = srcs[0] if srcs else ""

        if not definition_tr:
            unmapped["missing_definition"].append(label)
        if not source_urls:
            unmapped["missing_sources"].append(label)

        # status policy: Lite core'da veri bağımlılıklarını vendor sheet'ten çıkaramayız -> UNKNOWN bırak
        status_policy = {
            "OK": "calculation_available_in_vendor_dataset",
            "DEGRADED": "definition_or_sources_missing_or_proxy",
            "UNKNOWN": "requires_event_or_tracking_mapping_not_defined_yet",
        }

        canonical_metrics.append(
            {
                "id": cid,
                "vendor": "sportsbase",
                "vendor_label": label,
                "layer": DEFAULT_LAYER,
                "mechanisms": mechs,
                "role_guess": role,
                "definition_tr": definition_tr,
                "unit_or_type": unit,
                "phase_coverage": phase_ids,
                "phase_names": phase_names,
                "raw_formula": "",  # Sprint-2'de doldurulacak
                "required_columns": [],  # event-mapping sonrası doldurulacak
                "status_policy": status_policy,
                "sources": source_urls.split(";") if source_urls else [],
            }
        )

    registry = {
        "version": "0.3.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_from": {
            "origin_file": sb.get("origin_file", ""),
            "sportsbase_version": sb.get("version", ""),
        },
        "metrics": canonical_metrics,
        "phases": phases,
    }

    vendor_mappings = {
        "version": "0.1.0",
        "vendor": "sportsbase",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mappings": vendor_map,
    }

    return registry, vendor_mappings, unmapped


def merge_additive(existing: Dict[str, Any], generated: Dict[str, Any]) -> Dict[str, Any]:
    """
    Additive merge:
      - keep existing metrics (by id)
      - append new metrics not present
      - keep existing metadata
    """
    out = dict(existing) if existing else {}
    out.setdefault("version", generated.get("version", "0.0.0"))
    out.setdefault("metrics", [])

    existing_ids = {m.get("id") for m in out.get("metrics", [])}
    new_metrics = [m for m in generated.get("metrics", []) if m.get("id") not in existing_ids]

    out["metrics"] = out.get("metrics", []) + new_metrics

    # keep phases if missing
    if "phases" not in out and "phases" in generated:
        out["phases"] = generated["phases"]

    # attach generation note
    out.setdefault("generated_sources", [])
    out["generated_sources"].append(generated.get("generated_from", {}))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="", help="input sportsbase json path")
    ap.add_argument("--registry", default="hp_motor/library/registry/metric_registry.json")
    ap.add_argument("--vendor-map", default="hp_motor/library/registry/vendor_mappings.json")
    ap.add_argument("--unmapped", default="artifacts/registry/unmapped_report.json")
    ap.add_argument("--backup-dir", default="artifacts/registry/backups")
    args = ap.parse_args()

    # input resolution
    candidates = []
    if args.inp:
        candidates.append(Path(args.inp))
    candidates += [
        Path("hp_motor/library/registry/inputs/sportsbase_metrics_hp_v1.json"),
        Path("/sdcard/HP_LIBRARY/sportsbase_metrics_hp_v1.json"),
        Path("/sdcard/HP_LIBRARY/registry_inputs/sportsbase_metrics_hp_v1.json"),
    ]

    in_path = None
    for c in candidates:
        if c.exists():
            in_path = c
            break
    if in_path is None:
        raise SystemExit("Input not found. Provide --in or put file into hp_motor/library/registry/inputs/ or /sdcard/HP_LIBRARY/")

    sb = read_json(in_path)
    gen_registry, gen_vendor_map, unmapped = build_from_sportsbase(sb)

    reg_path = Path(args.registry)
    vendor_path = Path(args.vendor_map)
    unmapped_path = Path(args.unmapped)
    backup_dir = Path(args.backup_dir)

    # backup existing
    backup_file(reg_path, backup_dir)
    backup_file(vendor_path, backup_dir)

    # merge registry additive
    existing = read_json(reg_path) if reg_path.exists() else {}
    merged = merge_additive(existing, gen_registry)

    write_json(reg_path, merged)
    write_json(vendor_path, gen_vendor_map)
    write_json(unmapped_path, unmapped)

    print("OK: wrote", str(reg_path))
    print("OK: wrote", str(vendor_path))
    print("OK: wrote", str(unmapped_path))
    print("INFO: metrics_added =", len(merged.get("metrics", [])) - len(existing.get("metrics", [])))


if __name__ == "__main__":
    main()
