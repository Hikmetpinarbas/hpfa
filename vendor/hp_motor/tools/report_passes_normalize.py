from _root import ROOT
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

TABLES_DIR = Path("artifacts/reports/tables")
OUT_DIR = Path("artifacts/reports/normalized")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "competition","season","stage","table_type",
    "entity_type","entity_name",
    "passes_attempted","passes_completed","pass_pct",
    "metric_hint",
    "source_report_id","source_page_index","source_line_index",
]

RE_FRAC = re.compile(r"(\d+)\s*/\s*(\d+)")
RE_PCT  = re.compile(r"(\d+)%")
RE_PLAYER_PREFIX = re.compile(r"^\s*\d+\s+([^,]+),\s*(.+?)\s+(?:\d+\s*/\s*\d+)\b")  # "20 Anton, B. Dortmund ..."

MIN_ATTEMPTED = 20


def load_index_meta() -> Dict[str, Dict[str, str]]:
    import json
    p = Path("artifacts/reports/index_reports.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    meta: Dict[str, Dict[str, str]] = {}
    if isinstance(data, list):
        for i, r in enumerate(data):
            if not isinstance(r, dict):
                continue
            comp = str(r.get("competition","")).strip()
            season = str(r.get("season","")).strip()
            fn = str(r.get("filename","")).strip().replace(" ", "_")
            meta[f"report_{i:04d}"] = {"competition": comp, "season": season}
            if fn:
                meta[fn] = {"competition": comp, "season": season}
    return meta

def metric_hint(text: str) -> str:
    t = text.lower()
    if "kilit pas" in t:
        return "key_pass"
    if "isabetli pas" in t:
        return "accurate_pass"
    if "pas arasi" in t:
        return "passes_into_opposition"
    return "passes"

def main():
    meta = load_index_meta()
    in_files = sorted(TABLES_DIR.glob("*__tables_raw.csv"))
    if not in_files:
        raise SystemExit("ERR: no *__tables_raw.csv found")

    out_path = OUT_DIR / "passes_clean__normalized.csv"
    out_rows: List[Dict[str,str]] = []
    rows_parsed = 0
    seen = set()  # dedup key


    for fp in in_files:
        if fp.name.startswith("hp_"):
            continue
        rid = fp.stem.replace("__tables_raw","")
        m = meta.get(rid, {"competition":"", "season":""})

        with fp.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                txt = (row.get("text") or "").strip()
                kind = (row.get("kind") or "").strip()
                if not txt:
                    continue

                # only keep lines that look like pass fractions
                mfrac = RE_FRAC.search(txt)
                if not mfrac:
                    continue

                # try pct near it
                mpct = RE_PCT.search(txt)
                pct = mpct.group(1) if mpct else ""

                # interpret as attempted/completed (your samples "510/439 86%" -> attempted/completed)
                attempted = mfrac.group(1)
                completed = mfrac.group(2)

                # FILTER: drop tiny fractions (chart noise)
                try:
                    if int(attempted) < MIN_ATTEMPTED:
                        continue
                except Exception:
                    continue
                if not pct:
                    continue


                # entity (player or aggregate)
                ent_type = "team_or_aggregate"
                ent_name = "aggregate"

                mp = RE_PLAYER_PREFIX.match(txt)
                if mp:
                    ent_type = "player"
                    ent_name = (mp.group(1) + ", " + mp.group(2)).strip()

                key = (rid, row.get("page_index",""), row.get("line_index",""), attempted, completed, pct)
                if key in seen:
                    continue
                seen.add(key)

                out_rows.append({
                    "competition": m.get("competition",""),
                    "season": m.get("season",""),
                    "stage": "league_phase",
                    "table_type": "passes",
                    "entity_type": ent_type,
                    "entity_name": ent_name,
                    "passes_attempted": attempted,
                    "passes_completed": completed,
                    "pass_pct": pct,
                    "metric_hint": metric_hint(txt),
                    "source_report_id": rid,
                    "source_page_index": str(row.get("page_index","")),
                    "source_line_index": str(row.get("line_index","")),
                })
                rows_parsed += 1

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(f"OK: rows_parsed={rows_parsed} out={out_path}")

if __name__ == "__main__":
    main()
