from __future__ import annotations
import argparse
from hp_motor.ingest.loader import load_table
from hp_motor.integrity.popper import PopperGate
from hp_motor.engine.extract import extract_team_metrics
from hp_motor.narrative.generator import generate_match_report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="xlsx/csv dosya yolu")
    ap.add_argument("--team", required=True, help="Takım adı (ör: Galatasaray)")
    args = ap.parse_args()

    df = load_table(args.file)
    popper = PopperGate.check(df)
    if popper["status"] == "HARD_BLOCK":
        raise SystemExit(f"[HARD_BLOCK] {popper['reason']}")

    reg = extract_team_metrics(df, args.team)
    report = generate_match_report(reg.all(), popper)
    print(f"\n=== TEAM: {args.team} ===\n")
    print(report)

if __name__ == "__main__":
    main()
