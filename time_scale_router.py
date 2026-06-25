from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    src = repo_root / "hpfa" / "modules" / "core" / "time_scale_router_lite" / "src"
    sys.path.insert(0, str(src))
    from time_scale_router import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=repo_root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "input_window_count": report.get("input_window_count"),
        "routed_window_count": report.get("routed_window_count"),
        "minute_axis_window_count": report.get("minute_axis_window_count"),
        "event_index_window_count": report.get("event_index_window_count"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "possession_truth": report.get("possession_truth"),
        "sequence_truth": report.get("sequence_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
