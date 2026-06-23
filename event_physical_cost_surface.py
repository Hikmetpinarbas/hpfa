#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "support" / "event_physical_cost_surface_lite" / "src"
SPINE_SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
for path in (SRC, SPINE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from event_physical_cost_surface import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Event Physical Cost Surface Lite V1")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    result = write_outputs(args.out_dir, root=ROOT)
    print(json.dumps({
        "status": result.get("status"),
        "claim_safety": result.get("claim_safety"),
        "record_count": result.get("record_count"),
        "surface_counts": result.get("surface_counts"),
        "metric_family_counts": result.get("metric_family_counts"),
        "runtime_event_truth": result.get("runtime_event_truth"),
        "event_count_claim_allowed": result.get("event_count_claim_allowed"),
        "metric_count_allowed": result.get("metric_count_allowed"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
