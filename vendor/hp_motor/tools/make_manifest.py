from _root import ROOT  # noqa: F401
import csv, json, subprocess
from pathlib import Path
from datetime import datetime, timezone

NORM = Path("artifacts/reports/normalized")
SUMM = Path("out/summaries")

FILES = [
    NORM / "standings__normalized.csv",
    NORM / "goal_timing__normalized.csv",
    NORM / "passes_players_split__normalized.csv",
    SUMM / "goal_timing_team_profile.csv",
    SUMM / "passes_players_top_attempted.csv",
    SUMM / "passes_players_top_pct_min50.csv",
    SUMM / "passes_team_summary.csv",
]

OUT = SUMM / "manifest.json"
SUMM.mkdir(parents=True, exist_ok=True)

def sh(*args):
    try:
        return subprocess.check_output(list(args), text=True).strip()
    except Exception:
        return ""

def csv_meta(p: Path):
    with p.open("r", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, [])
        n = 1
        for _ in r:
            n += 1
    return {"rows_including_header": n, "columns": header}

manifest = {
    "schema_version": "reports_manifest_v1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "git": {
        "branch": sh("git", "branch", "--show-current"),
        "commit": sh("git", "rev-parse", "HEAD"),
        "describe": sh("git", "describe", "--tags", "--always"),
    },
    "files": {},
}

for p in FILES:
    if p.exists() and p.suffix.lower() == ".csv":
        manifest["files"][str(p)] = csv_meta(p)
    elif p.exists():
        manifest["files"][str(p)] = {"bytes": p.stat().st_size}
    else:
        manifest["files"][str(p)] = {"missing": True}

OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK:", OUT)
