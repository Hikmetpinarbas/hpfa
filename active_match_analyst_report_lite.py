#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_analyst_report_lite" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from report_lite import OUTPUT_JSON, OUTPUT_TXT, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA ACTIVE_MATCH Analyst Report Lite V1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = write_report(
        active_match_dir=args.active_match_dir,
        out_dir=args.out_dir,
        root=ROOT,
    )
    print(json.dumps({
        "status": result.get("status"),
        "canonical_event_count": result.get("canonical_event_count"),
        "out_json": str(Path(args.out_dir) / OUTPUT_JSON),
        "out_txt": str(Path(args.out_dir) / OUTPUT_TXT),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
