#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_identity_guard_lite" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from active_match_identity_guard import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA Active Match Identity Guard Lite V1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--declared-manifest", default=None)
    args = parser.parse_args()

    result = write_outputs(
        active_match_dir=args.active_match_dir,
        out_dir=args.out_dir,
        declared_manifest_path=args.declared_manifest,
        root=ROOT,
    )
    print(json.dumps({
        "status": result.get("status"),
        "identity_match_status": result.get("identity_match_status"),
        "active_match_evidence_allowed": result.get("active_match_evidence_allowed"),
        "canonical_event_count": result.get("canonical_event_count"),
        "outputs": result.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
