from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "team_period_event_identity_discovery_lite" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team_period_event_identity_discovery import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA team-period event identity discovery")
    parser.add_argument("--canonical-json", required=True)
    parser.add_argument("--out", default="/sdcard/Download/HPFA")
    args = parser.parse_args()

    report = write_outputs(args.canonical_json, args.out)
    print(json.dumps({
        "status": report["status"],
        "assembled_same_role_pair_candidate_count": report["assembled_same_role_pair_candidate_count"],
        "ambiguous_trace_count": report["ambiguous_trace_count"],
        "unresolved_trace_count": report["unresolved_trace_count"],
        "canonical_event_count": report["canonical_event_count"],
        "production_release": report["production_release"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "DISCOVERY_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
