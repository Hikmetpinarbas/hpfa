from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd

from hp_motor.config.loader import load_spec
from hp_motor.ingest.loader import load_table
from hp_motor.integrity.popper import PopperGate
from hp_motor.engine.extract import extract_team_metrics
from hp_motor.diagnostics.dictionary import load_dictionary, build_alias_map
from hp_motor.diagnostics.inventory import load_inventory, allowed_sheets_for_corr
from hp_motor.semantics.tagger import load_6faz_map, build_6faz_index, tag_metric
from hp_motor.semantics.dictionary_enrich import load_dictionary as load_metric_dictionary, enrich as enrich_metric
from hp_motor.engine.match_stats import extract_team_match_stats

def _find_source_file(base_dir: Path, rel_path: str) -> Path | None:
    # spec'teki path genelde dosya adıdır; base_dir içinde ararız
    cand = base_dir / rel_path
    if cand.exists():
        return cand
    # fallback: sadece file name ile ara
    name = Path(rel_path).name
    hits = list(base_dir.rglob(name))
    return hits[0] if hits else None

def run(spec_path: str, base_dir: str, out_path: str, team_names: list[str]) -> Dict[str, Any]:
    spec = load_spec(spec_path)
    base = Path(base_dir)

    dict_path = base / "hp_motor/data/metric_dictionary.csv"
    inv_path  = base / "hp_motor/data/data_inventory.csv"

    # dictionary/inventory optional (yoksa degrade)
    dict_df = load_metric_dictionary(str(dict_path)) if dict_path.exists() else None
    inv_df  = load_inventory(str(inv_path)) if inv_path.exists() else None

    faz_map_path = base / 'hp_motor/data/6faz_map.json'
    faz_map = load_6faz_map(str(faz_map_path)) if faz_map_path.exists() else None
    faz_idx = build_6faz_index(faz_map) if faz_map else {}

    report: Dict[str, Any] = {
        "hp_motor_version": spec.get("hp_motor_version"),
        "project": spec.get("project"),
        "sources": [],
        "teams": {},
        "degraded": []
    }

    # 1) sources: event csv'yi bul ve yükle
    event_sources = [s for s in spec.get("ingest", {}).get("sources", []) if s.get("grain_hint") == "event" and s.get("type") == "csv"]
    if not event_sources:
        report["degraded"].append("No event csv source found in spec.")
        Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    # Load ALL event csv sources (not just the first one) and concat
    event_tables = []
    for es in event_sources:
        sp = _find_source_file(base, es["path"])
        if not sp:
            report["degraded"].append(f"Event source not found: {es['path']}")
            continue
        dfi = load_table(str(sp))
        pop = PopperGate.check(dfi)
        report["sources"].append({"type": "event_csv", "path": str(sp), "popper": pop, "rows": int(len(dfi))})
        event_tables.append(dfi)

    if not event_tables:
        report["degraded"].append("Event sources listed but none could be loaded.")
        Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    df = pd.concat(event_tables, ignore_index=True)

    # 2) dictionary alias map (kolon normalizasyonu rapora)
    if dict_df is not None:
        alias = build_alias_map(list(df.columns), dict_df)
        report["event_schema"] = {"columns": list(df.columns), "alias_map": alias}
    else:
        report["degraded"].append("Metric dictionary missing -> no canonical aliasing.")

    
    # 2.5) other sources (xlsx/csv/xml) -> load for schema + optional match-stats metrics
    other_sources = [s for s in spec.get('ingest', {}).get('sources', []) if s not in event_sources]
    loaded_tables = []  # list of (source_meta, df)
    for s in other_sources:
        sp = _find_source_file(base, s.get('path',''))
        if not sp:
            report['degraded'].append(f"Source not found: {s.get('path')}")
            continue
        try:
            df2 = load_table(str(sp))
            loaded_tables.append((s, df2))
            report['sources'].append({
                'type': s.get('type'),
                'path': str(sp),
                'grain_hint': s.get('grain_hint'),
                'rows': int(len(df2)),
                'cols': list(map(str, df2.columns))[:60]
            })
        except Exception as e:
            report['degraded'].append(f"Failed to load {s.get('path')}: {e}")

# 3) team reports
    for t in team_names:
        reg = extract_team_metrics(df, t).all()
        # Optional: append match-stats metrics from any loaded xlsx source
        match_stats_added = False
        for smeta, sdf in loaded_tables:
            if smeta.get('grain_hint') in ('match', 'team_match', 'match_stats') and smeta.get('type') == 'xlsx':
                extra = extract_team_match_stats(sdf, t)
                # extra list can be empty; still safe
                reg.extend(extra)
                match_stats_added = True
        if not match_stats_added:
            report['degraded'].append('No match-stats xlsx source loaded -> Shots/xG may remain UNKNOWN (expected for event-only).')

        enriched = []
        for m in reg:
            d = m.as_dict()
            faz = tag_metric(d.get('name', ''), faz_idx)
            d['phase_id'] = faz.get('phase_id')
            d['metric_role'] = faz.get('metric_role')
            meta = enrich_metric(d.get('name', ''), dict_df)
            d.update(meta)
            enriched.append(d)
        report['teams'][t] = enriched

    # 4) inventory gate (şimdilik sadece rapora koyuyoruz; corr engine sonra)
    if inv_df is not None:
        report["corr_allowed_sheets"] = allowed_sheets_for_corr(inv_df, max_corr_pairs=15000)
    else:
        report["degraded"].append("Data inventory missing -> no cost gating for correlations.")

    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
