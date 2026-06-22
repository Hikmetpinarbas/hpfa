#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "canonical_event_lite" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from canonical_event_lite import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA Canonical Event Lite V1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = write_outputs(
        active_match_dir=args.active_match_dir,
        out_dir=args.out_dir,
        root=ROOT,
    )
    print(json.dumps({
        "status": result.get("status"),
        "canonical_event_count": result.get("canonical_event_count"),
        "canonical_lite_row_count": result.get("canonical_lite_row_count"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
