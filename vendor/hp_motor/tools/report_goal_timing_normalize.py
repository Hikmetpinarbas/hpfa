from _root import ROOT  # chdir repo root
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TABLES_DIR = Path("artifacts/reports/tables")
OUT_DIR = Path("artifacts/reports/normalized")

FIELDS = [
    "competition","season","stage","table_type",
    "rank","team",
    "total_goals",
    "goals_1h","pct_1h",
    "goals_2h","pct_2h",
    "g_0_15","pct_0_15",
    "g_15_30","pct_15_30",
    "g_30_45","pct_30_45",
    "g_45p","pct_45p",
    "g_45_60","pct_45_60",
    "g_60_75","pct_60_75",
    "g_75_90","pct_75_90",
    "g_90p","pct_90p",
    "source_report_id","source_page_index"
]

RE_RANK = re.compile(r"^\d+$")
RE_PCT = re.compile(r"^(\d+)%$")
RE_DASH = re.compile(r"^(—|-)$")

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

def tokens_from_line(line: str) -> List[str]:
    # Use generic split but keep multiword team by later join
    return [t for t in line.strip().replace("\t"," ").split(" ") if t]

def parse_timing_row(line: str) -> Optional[Dict[str, object]]:
    """
    Expected structure (example):
      1 Arsenal 23 9 39% 14 61% 4 17% 2 9% 3 13% — 4 17% 6 26% 3 13% 1 4%
    We interpret as:
      rank, team, total,
      1H, 1H%, 2H, 2H%,
      0-15,0-15%, 15-30,15-30%, 30-45,30-45%, 45+,45+%,
      45-60,45-60%, 60-75,60-75%, 75-90,75-90%, 90+,90+%
    Missing interval values can be '—'.
    """
    toks = tokens_from_line(line)
    if len(toks) < 10:
        return None
    if not RE_RANK.match(toks[0]):
        return None
    rank = int(toks[0])

    # Find start of numeric stream after team:
    # team ends right before the first pure int token after rank.
    pos = None
    for i in range(1, len(toks)):
        if toks[i].isdigit():
            pos = i
            break
    if pos is None or pos == 1:
        return None

    team = " ".join(toks[1:pos]).strip()
    tail = toks[pos:]

    # Convert tail into sequence of (int_or_none, pct_or_none) pairs where possible
    def read_int(i: int) -> Tuple[Optional[int], int]:
        if i >= len(tail):
            return None, i
        t = tail[i]
        if RE_DASH.match(t):
            return None, i+1
        if t.isdigit():
            return int(t), i+1
        return None, i+1

    def read_pct(i: int) -> Tuple[Optional[int], int]:
        if i >= len(tail):
            return None, i
        m = RE_PCT.match(tail[i])
        if m:
            return int(m.group(1)), i+1
        if RE_DASH.match(tail[i]):
            return None, i+1
        return None, i+1

    # We expect 1 total, then 10 buckets of (goals,pct) for: 1H,2H,0-15,15-30,30-45,45+,45-60,60-75,75-90,90+
    # total is just an int (no pct)
    idx = 0
    if idx >= len(tail) or not tail[idx].isdigit():
        return None
    total = int(tail[idx]); idx += 1

    buckets = []
    for _ in range(10):
        g, idx = read_int(idx)
        p, idx = read_pct(idx)
        buckets.append((g, p))

    if len(buckets) != 10:
        return None

    (g1h,p1h),(g2h,p2h),(g0,p0),(g15,p15),(g30,p30),(g45p,p45p),(g4560,p4560),(g6075,p6075),(g7590,p7590),(g90p,p90p) = buckets

    return {
        "rank": rank,
        "team": team,
        "total_goals": total,
        "goals_1h": g1h, "pct_1h": p1h,
        "goals_2h": g2h, "pct_2h": p2h,
        "g_0_15": g0, "pct_0_15": p0,
        "g_15_30": g15, "pct_15_30": p15,
        "g_30_45": g30, "pct_30_45": p30,
        "g_45p": g45p, "pct_45p": p45p,
        "g_45_60": g4560, "pct_45_60": p4560,
        "g_60_75": g6075, "pct_60_75": p6075,
        "g_75_90": g7590, "pct_75_90": p7590,
        "g_90p": g90p, "pct_90p": p90p,
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = load_index_meta()

    in_files = sorted(TABLES_DIR.glob("*__tables_raw.csv"))
    if not in_files:
        raise SystemExit("ERR: no *__tables_raw.csv found")

    out_path = OUT_DIR / "goal_timing__normalized.csv"
    out_rows: List[Dict[str, str]] = []
    rows_parsed = 0

    for fp in in_files:
        if fp.name.startswith("hp_"):
            continue
        rid = fp.stem.replace("__tables_raw", "")
        m = meta.get(rid, {"competition":"", "season":""})

        with fp.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                kind = (row.get("kind") or "").strip()
                if kind not in ("standings_row", "spaced", "numeric"):
                    continue
                txt = (row.get("text") or "").strip()
                parsed = parse_timing_row(txt)
                if not parsed:
                    continue

                rec = {
                    "competition": m.get("competition",""),
                    "season": m.get("season",""),
                    "stage": "league_phase",
                    "table_type": "goal_timing",
                    "rank": str(parsed["rank"]),
                    "team": str(parsed["team"]),
                    "total_goals": str(parsed["total_goals"]),

                    "goals_1h": "" if parsed["goals_1h"] is None else str(parsed["goals_1h"]),
                    "pct_1h": "" if parsed["pct_1h"] is None else str(parsed["pct_1h"]),
                    "goals_2h": "" if parsed["goals_2h"] is None else str(parsed["goals_2h"]),
                    "pct_2h": "" if parsed["pct_2h"] is None else str(parsed["pct_2h"]),

                    "g_0_15": "" if parsed["g_0_15"] is None else str(parsed["g_0_15"]),
                    "pct_0_15": "" if parsed["pct_0_15"] is None else str(parsed["pct_0_15"]),
                    "g_15_30": "" if parsed["g_15_30"] is None else str(parsed["g_15_30"]),
                    "pct_15_30": "" if parsed["pct_15_30"] is None else str(parsed["pct_15_30"]),
                    "g_30_45": "" if parsed["g_30_45"] is None else str(parsed["g_30_45"]),
                    "pct_30_45": "" if parsed["pct_30_45"] is None else str(parsed["pct_30_45"]),
                    "g_45p": "" if parsed["g_45p"] is None else str(parsed["g_45p"]),
                    "pct_45p": "" if parsed["pct_45p"] is None else str(parsed["pct_45p"]),
                    "g_45_60": "" if parsed["g_45_60"] is None else str(parsed["g_45_60"]),
                    "pct_45_60": "" if parsed["pct_45_60"] is None else str(parsed["pct_45_60"]),
                    "g_60_75": "" if parsed["g_60_75"] is None else str(parsed["g_60_75"]),
                    "pct_60_75": "" if parsed["pct_60_75"] is None else str(parsed["pct_60_75"]),
                    "g_75_90": "" if parsed["g_75_90"] is None else str(parsed["g_75_90"]),
                    "pct_75_90": "" if parsed["pct_75_90"] is None else str(parsed["pct_75_90"]),
                    "g_90p": "" if parsed["g_90p"] is None else str(parsed["g_90p"]),
                    "pct_90p": "" if parsed["pct_90p"] is None else str(parsed["pct_90p"]),

                    "source_report_id": rid,
                    "source_page_index": str(row.get("page_index","")),
                }
                out_rows.append(rec)
                rows_parsed += 1

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(f"OK: rows_parsed={rows_parsed} out={out_path}")

if __name__ == "__main__":
    main()
