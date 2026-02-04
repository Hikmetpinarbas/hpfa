from _root import ROOT  # noqa: F401 (chdir)
import csv
from pathlib import Path
from collections import defaultdict

NORM = Path("artifacts/reports/normalized")
OUT  = Path("out/summaries")
OUT.mkdir(parents=True, exist_ok=True)

INP = NORM / "passes_players_split__normalized.csv"
if not INP.exists():
    raise SystemExit(f"ERR: missing {INP}")

rows = []
with INP.open("r", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        # basic typing + cleanup
        try:
            att = int(row["passes_attempted"])
            comp = int(row["passes_completed"])
            pct = int(row["pass_pct"]) if row.get("pass_pct") else None
        except Exception:
            continue
        row["_att"] = att
        row["_comp"] = comp
        row["_pct"] = pct if pct is not None else (round(100 * comp / att) if att else 0)
        rows.append(row)

# 1) Top players by attempted
top_attempted = sorted(rows, key=lambda x: x["_att"], reverse=True)[:100]
out1 = OUT / "passes_players_top_attempted.csv"
fields1 = ["competition","season","team_name","player_name","passes_attempted","passes_completed","pass_pct","metric_hint","source_page_index","source_line_index"]
with out1.open("w", encoding="utf-8", newline="") as w:
    wr = csv.DictWriter(w, fieldnames=fields1)
    wr.writeheader()
    for x in top_attempted:
        wr.writerow({k: x.get(k,"") for k in fields1})

# 2) Top players by completion pct (min attempted threshold)
MIN_ATT = 50
cand = [x for x in rows if x["_att"] >= MIN_ATT]
top_pct = sorted(cand, key=lambda x: (x["_pct"], x["_att"]), reverse=True)[:100]
out2 = OUT / "passes_players_top_pct_min50.csv"
with out2.open("w", encoding="utf-8", newline="") as w:
    wr = csv.DictWriter(w, fieldnames=fields1)
    wr.writeheader()
    for x in top_pct:
        wr.writerow({k: x.get(k,"") for k in fields1})

# 3) Team summary (sum attempts/completions; weighted pct)
team = defaultdict(lambda: {"att":0, "comp":0, "n":0})
for x in rows:
    t = (x.get("team_name") or "").strip()
    if not t:
        continue
    team[t]["att"] += x["_att"]
    team[t]["comp"] += x["_comp"]
    team[t]["n"] += 1

team_rows = []
for t, agg in team.items():
    att = agg["att"]; comp = agg["comp"]
    pct = round(100 * comp / att) if att else 0
    team_rows.append({"team_name": t, "passes_attempted_sum": att, "passes_completed_sum": comp, "pass_pct_weighted": pct, "rows": agg["n"]})

team_rows.sort(key=lambda x: x["passes_attempted_sum"], reverse=True)

out3 = OUT / "passes_team_summary.csv"
fields3 = ["team_name","passes_attempted_sum","passes_completed_sum","pass_pct_weighted","rows"]
with out3.open("w", encoding="utf-8", newline="") as w:
    wr = csv.DictWriter(w, fieldnames=fields3)
    wr.writeheader()
    wr.writerows(team_rows)

print("OK:", out1, out2, out3)
