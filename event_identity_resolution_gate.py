#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "event_identity_resolution_gate_lite" / "src"
SPINE_SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
for path in (SRC, SPINE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from event_identity_resolution_gate import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Event Identity Resolution Gate Lite V1")
    parser.add_argument("--canonical-event-lite-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = write_outputs(args.canonical_event_lite_json, args.out_dir, root=ROOT)
    print(json.dumps({
        "status": result.get("status"),
        "decision": result.get("decision"),
        "claim_safety": result.get("claim_safety"),
        "surface_row_inventory_total": result.get("surface_row_inventory_total"),
        "candidate_cluster_count": result.get("candidate_cluster_count"),
        "duplicate_risk_candidate_count": result.get("duplicate_risk_candidate_count"),
        "unresolved_candidate_count": result.get("unresolved_candidate_count"),
        "deduplicated_event_count": result.get("deduplicated_event_count"),
        "event_count_claim_allowed": result.get("event_count_claim_allowed"),
        "metric_count_allowed": result.get("metric_count_allowed"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
