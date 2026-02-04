import argparse
import json
from pathlib import Path

from engine.ingest.csv_ingest import inspect_csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input CSV")
    ap.add_argument("--mapping", required=True, help="Path to provider mapping YAML")
    args = ap.parse_args()

    inp = Path(args.input)
    mp = Path(args.mapping)

    if inp.suffix.lower() != ".csv":
        raise SystemExit(f"Only CSV supported right now. Got: {inp.suffix}")

    result = inspect_csv(str(inp), str(mp))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()