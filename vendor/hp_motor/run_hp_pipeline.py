from __future__ import annotations
import argparse
from hp_motor.pipeline.run_pipeline import run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="hp_motor/config/spec.json")
    ap.add_argument("--base-dir", default=".")
    ap.add_argument("--out", default="hp_report.json")
    ap.add_argument("--team", action="append", required=True, help="Birden fazla verebilirsin: --team Galatasaray --team 'Manchester City'")
    args = ap.parse_args()

    run(args.spec, args.base_dir, args.out, args.team)
    print(f"OK -> {args.out}")

if __name__ == "__main__":
    main()
