from _root import ROOT  # sets cwd to repo root
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

TABLES_DIR = Path("artifacts/reports/tables")
OUT_DIR = Path("artifacts/reports/normalized")

FIELDS = [
    "competition","season","stage","table_type",
    "rank","team","played","wins","draws","losses",
    "gf","ga","gd","points",
    "source_report_id","source_page_index"
]

RE_INT = re.compile(r"^\d+$")
RE_SCORE = re.compile(r"^(\d+)\s*[:\-–]\s*(\d+)$")
RE_PCT = re.compile(r"^\d+%$")

def load_index() -> List[Dict[str,str]]:
    import json
    p = Path("artifacts/reports/index_reports.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    raise SystemExit("ERR: index not a list (unexpected)")

def pick_meta_by_report_id(index_rows: List[Dict[str,str]]) -> Dict[str, Dict[str,str]]:
    meta = {}
    for i, r in enumerate(index_rows):
        comp = str(r.get("competition","")).strip()
        season = str(r.get("season","")).strip()
        fn = str(r.get("filename","")).strip().replace(" ", "_")
        meta[f"report_{i:04d}"] = {"competition": comp, "season": season}
        if fn:
            meta[fn] = {"competition": comp, "season": season}
    return meta

def read_tables_csv(path: Path) -> List[Dict[str,str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def split_tokens(text: str) -> List[str]:
    # Your extracted lines mix single-space and multi-space; use generic split.
    # Keep tokens like "Newcastle" "Utd." etc separate, we will re-join team later.
    return [t for t in text.strip().replace("\t"," ").split(" ") if t]

def extract_team(tokens: List[str]) -> str:
    # tokens[0]=rank; team until first numeric-ish token (int or score)
    pos = None
    for i in range(1, len(tokens)):
        t = tokens[i].replace("—","").strip()
        if RE_INT.match(t) or RE_SCORE.match(t) or RE_PCT.match(t):
            pos = i
            break
    if pos is None:
        return " ".join(tokens[1:]).strip()
    return " ".join(tokens[1:pos]).strip()

def collect_numeric_stream(tokens: List[str]) -> List[int]:
    """
    Convert tokens into a stream of integers, ignoring percentages and dashes.
    Also splits score tokens '12:8' into [12,8].
    """
    ints: List[int] = []
    for t in tokens:
        tt = t.strip()
        if not tt or tt == "—":
            continue
        if RE_PCT.match(tt):
            continue
        m = RE_SCORE.match(tt)
        if m:
            ints.append(int(m.group(1)))
            ints.append(int(m.group(2)))
            continue
        if RE_INT.match(tt):
            ints.append(int(tt))
            continue
    return ints

def parse_standings_from_stream(rank: int, ints: List[int]) -> Optional[Dict[str,int]]:
    """
    Try common tails:
      P W D L GF GA GD PTS  (8 ints)
      P W D L GF GA PTS     (7 ints) -> derive GD = GF-GA
    We take from the END of the stream because your rows contain many extra nums.
    """
    if len(ints) < 7:
        return None

    # try 8-tail
    if len(ints) >= 8:
        P,W,D,L,GF,GA,GD,PTS = ints[-8:]
        if _sanity(P,W,D,L,GF,GA,PTS):
            return {"rank":rank,"played":P,"wins":W,"draws":D,"losses":L,"gf":GF,"ga":GA,"gd":GD,"points":PTS}

    # try 7-tail (no GD)
    P,W,D,L,GF,GA,PTS = ints[-7:]
    if _sanity(P,W,D,L,GF,GA,PTS):
        return {"rank":rank,"played":P,"wins":W,"draws":D,"losses":L,"gf":GF,"ga":GA,"gd":GF-GA,"points":PTS}

    return None

def _sanity(P,W,D,L,GF,GA,PTS) -> bool:
    # Basic football constraints
    if P < 1 or P > 60:
        return False
    if any(x < 0 or x > 200 for x in (GF,GA,PTS)):
        return False
    if W < 0 or D < 0 or L < 0:
        return False
    if W + D + L > P + 1:
        return False
    return True

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = pick_meta_by_report_id(load_index())

    in_files = sorted(TABLES_DIR.glob("*__tables_raw.csv"))
    if not in_files:
        raise SystemExit("ERR: no *__tables_raw.csv found in artifacts/reports/tables")

    out_path = OUT_DIR / "standings__normalized.csv"
    out_rows: List[Dict[str,str]] = []
    rows_parsed = 0

    for fp in in_files:
        if fp.name.startswith("hp_"):
            continue

        rid = fp.stem.replace("__tables_raw","")
        m = meta.get(rid, {"competition":"", "season":""})
        rows = read_tables_csv(fp)

        for row in rows:
            kind = (row.get("kind") or "").strip()
            # NOW include standings_row
            if kind not in ("spaced","numeric","standings_row"):
                continue

            txt = (row.get("text") or "").strip()
            tokens = split_tokens(txt)
            if not tokens or not RE_INT.match(tokens[0]):
                continue

            rank = int(tokens[0])
            team = extract_team(tokens)
            if not team or len(team) < 2:
                continue

            ints = collect_numeric_stream(tokens[1:])  # after rank
            parsed = parse_standings_from_stream(rank, ints)
            if not parsed:
                continue

            out_rows.append({
                "competition": m.get("competition",""),
                "season": m.get("season",""),
                "stage": "league_phase",
                "table_type": "standings",
                "rank": str(parsed["rank"]),
                "team": team,
                "played": str(parsed["played"]),
                "wins": str(parsed["wins"]),
                "draws": str(parsed["draws"]),
                "losses": str(parsed["losses"]),
                "gf": str(parsed["gf"]),
                "ga": str(parsed["ga"]),
                "gd": str(parsed["gd"]),
                "points": str(parsed["points"]),
                "source_report_id": rid,
                "source_page_index": str(row.get("page_index","")),
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
