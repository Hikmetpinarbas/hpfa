#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "team_binding_lite" / "src"
SPINE_SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
for path in (SRC, SPINE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from team_binding_lite import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Team Binding Lite V1")
    parser.add_argument("--canonical-event-lite-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = write_outputs(args.canonical_event_lite_json, args.out_dir, root=ROOT)
    print(json.dumps({
        "status": result.get("status"),
        "team_entity_count": result.get("team_entity_count"),
        "player_entity_count": result.get("player_entity_count"),
        "unresolved_team_rows": result.get("unresolved_team_rows"),
        "canonical_event_count": result.get("canonical_event_count"),
        "deduplicated_event_count": result.get("deduplicated_event_count"),
        "primary_event_surface_candidate": result.get("primary_event_surface_candidate"),
        "event_count_claim_allowed": result.get("event_count_claim_allowed"),
        "surface_row_inventory_total": result.get("surface_row_inventory_total"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
