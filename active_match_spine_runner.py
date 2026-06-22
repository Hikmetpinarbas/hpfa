#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from spine_runner import run_spine_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA ACTIVE_MATCH spine check v1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--composite-registry")
    args = parser.parse_args()

    result = run_spine_check(
        active_match_dir=args.active_match_dir,
        out_dir=args.out_dir,
        composite_registry=args.composite_registry,
        root=ROOT,
    )
    print(json.dumps({
        "status": result.get("status"),
        "out_json": str(Path(args.out_dir) / "active_match_spine_check_v1.json"),
        "out_txt": str(Path(args.out_dir) / "active_match_spine_check_v1.txt"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
