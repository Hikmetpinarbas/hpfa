#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "hpfa/modules/core/event_instance_admission_guard_lite/src"
sys.path.insert(0, str(SRC))

from event_instance_admission_guard import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Event Instance Admission Guard Lite V1")
    parser.add_argument("--canonical-json", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--out", default="/sdcard/Download/HPFA")
    args = parser.parse_args()

    report = write_outputs(args.canonical_json, args.source_manifest, args.out)
    print(json.dumps({
        "decision_state": report["decision_state"],
        "visible_surface_row_count": report["visible_surface_row_count"],
        "admitted_event_candidate_count": report["admitted_event_candidate_count"],
        "support_only_row_count": report["support_only_row_count"],
        "quarantined_row_count": report["quarantined_row_count"],
        "canonical_event_count": report["canonical_event_count"],
        "production_release": report["production_release"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["decision_state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
