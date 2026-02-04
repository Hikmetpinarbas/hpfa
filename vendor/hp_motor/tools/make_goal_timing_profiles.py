from _root import ROOT  # noqa
import csv
from pathlib import Path
from collections import defaultdict

INP = Path("artifacts/reports/normalized/goal_timing__normalized.csv")
OUTD = Path("out/summaries")
OUTD.mkdir(parents=True, exist_ok=True)
OUT = OUTD / "goal_timing_team_profile.csv"

if not INP.exists():
    raise SystemExit(f"ERR: missing {INP}")

def to_int(x):
    x = (x or "").strip()
    return int(x) if x.isdigit() else 0

def is_team_name(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    # player lines are usually "Name, Team"
    if "," in s:
        return False
    # reject obvious junk
    if len(s) < 2:
        return False
    return True

teams = defaultdict(lambda: {
    "total":0,
    "g1h":0, "g2h":0,
    "g0_15":0, "g15_30":0, "g30_45":0, "g45p":0,
    "g45_60":0, "g60_75":0, "g75_90":0, "g90p":0,
    "rows":0
})

with INP.open("r", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        team = (row.get("team") or "").strip()
        if not is_team_name(team):
            continue

        total = to_int(row.get("total_goals"))
        if total <= 0:
            continue

        g1h = to_int(row.get("goals_1h"))
        g2h = to_int(row.get("goals_2h"))

        # sanity: 1H+2H should not exceed total by much
        # allow small extraction noise (+1), otherwise drop row
        if g1h + g2h > total + 1:
            continue

        agg = teams[team]
        agg["total"] += total
        agg["g1h"] += g1h
        agg["g2h"] += g2h
        agg["g0_15"] += to_int(row.get("g_0_15"))
        agg["g15_30"] += to_int(row.get("g_15_30"))
        agg["g30_45"] += to_int(row.get("g_30_45"))
        agg["g45p"] += to_int(row.get("g_45p"))
        agg["g45_60"] += to_int(row.get("g_45_60"))
        agg["g60_75"] += to_int(row.get("g_60_75"))
        agg["g75_90"] += to_int(row.get("g_75_90"))
        agg["g90p"] += to_int(row.get("g_90p"))
        agg["rows"] += 1

def share(num, den):
    return round(100 * num / den, 1) if den else 0.0

intervals = [
    ("0_15","g0_15"),
    ("15_30","g15_30"),
    ("30_45","g30_45"),
    ("45p","g45p"),
    ("45_60","g45_60"),
    ("60_75","g60_75"),
    ("75_90","g75_90"),
    ("90p","g90p"),
]

out_rows = []
for t, a in teams.items():
    total = a["total"]
    if total <= 0:
        continue

    early = a["g0_15"] + a["g15_30"]
    late  = a["g75_90"] + a["g90p"]
    tilt  = a["g2h"] - a["g1h"]

    peak_name, peak_val = None, -1
    for name, key in intervals:
        v = a[key]
        if v > peak_val:
            peak_val = v
            peak_name = name

    out_rows.append({
        "team": t,
        "total_goals": total,
        "share_1h_pct": share(a["g1h"], total),
        "share_2h_pct": share(a["g2h"], total),
        "share_early_0_30_pct": share(early, total),
        "share_late_75_90p_pct": share(late, total),
        "tilt_2h_minus_1h": tilt,
        "tilt_share_pct": share(tilt, total),
        "peak_interval": peak_name,
        "peak_interval_share_pct": share(peak_val, total),
        "rows": a["rows"],
    })

out_rows.sort(key=lambda x: x["total_goals"], reverse=True)

fields = ["team","total_goals","share_1h_pct","share_2h_pct","share_early_0_30_pct","share_late_75_90p_pct","tilt_2h_minus_1h","tilt_share_pct","peak_interval","peak_interval_share_pct","rows"]
with OUT.open("w", encoding="utf-8", newline="") as w:
    wr = csv.DictWriter(w, fieldnames=fields)
    wr.writeheader()
    wr.writerows(out_rows)

print("OK:", OUT, "teams=", len(out_rows))
