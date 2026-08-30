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
from full_spine_runner import run_full_spine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA ACTIVE_MATCH spine v1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--composite-registry")
    parser.add_argument(
        "--full-spine",
        action="store_true",
        help=(
            "Run the current reconstruction-to-intelligence spine using existing product producers. "
            "This does not create a parallel runtime engine."
        ),
    )
    parser.add_argument(
        "--execution-root",
        help=(
            "Explicit selected runtime execution root. "
            "Defaults to the product checkout root when omitted; no runtime discovery is performed."
        ),
    )
    args = parser.parse_args()

    execution_root = Path(args.execution_root).expanduser().resolve(strict=False) if args.execution_root else ROOT

    if args.full_spine:
        if args.composite_registry:
            parser.error("--composite-registry is not accepted with --full-spine")
        result = run_full_spine(
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
            execution_root=execution_root,
        )
        out_json = str(Path(args.out_dir) / "active_match_full_spine_v1.json")
        out_txt = str(Path(args.out_dir) / "active_match_full_spine_v1.txt")
        rc = 2 if result.get("status") == "FAIL_CLOSED" else 0
    else:
        result = run_spine_check(
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
            composite_registry=args.composite_registry,
            root=ROOT,
            execution_root=execution_root,
        )
        out_json = str(Path(args.out_dir) / "active_match_spine_check_v1.json")
        out_txt = str(Path(args.out_dir) / "active_match_spine_check_v1.txt")
        rc = 2 if result.get("status") == "FAIL_CLOSED" else 0

    print(json.dumps({
        "status": result.get("status"),
        "full_spine": bool(args.full_spine),
        "out_json": out_json,
        "out_txt": out_txt,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
