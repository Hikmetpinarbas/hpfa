#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "reporting" / "postmatch_analyst_report_lite" / "src"
SPINE_SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
for path in (SRC, SPINE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from postmatch_analyst_report import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Numeric Match Report Lite V1")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    result = write_outputs(args.out_dir, root=ROOT)
    print(json.dumps({
        "status": result.get("status"),
        "claim_safety": result.get("claim_safety"),
        "team_comparison": result.get("team_comparison"),
        "surface_status": result.get("surface_status"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
