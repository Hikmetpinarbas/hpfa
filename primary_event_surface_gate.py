#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "primary_event_surface_gate_lite" / "src"
SPINE_SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
for path in (SRC, SPINE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from primary_event_surface_gate import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Primary Event Surface Gate Lite V1")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    result = write_outputs(args.out_dir, root=ROOT)
    print(json.dumps({
        "status": result.get("status"),
        "decision": result.get("decision"),
        "claim_safety": result.get("claim_safety"),
        "primary_event_surface_candidate": result.get("primary_event_surface_candidate"),
        "primary_event_surface_candidate_role": result.get("primary_event_surface_candidate_role"),
        "candidate_score": result.get("candidate_score"),
        "candidate_evaluation_count": result.get("candidate_evaluation_count"),
        "eligible_candidate_count": result.get("eligible_candidate_count"),
        "canonical_event_count": result.get("canonical_event_count"),
        "deduplicated_event_count": result.get("deduplicated_event_count"),
        "event_count_claim_allowed": result.get("event_count_claim_allowed"),
        "metric_count_allowed": result.get("metric_count_allowed"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
