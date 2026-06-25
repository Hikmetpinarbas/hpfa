from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "event_window_builder_lite" / "src"
    sys.path.insert(0, str(src))
    from event_window_builder import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--raw-input-dir", default=None)
    parser.add_argument("--window-size-mins", type=int, default=5)
    parser.add_argument("--hop-mins", type=int, default=5)
    args = parser.parse_args()

    report = write_outputs(
        args.input_dir,
        args.out_dir,
        root=root,
        raw_input_dir=args.raw_input_dir,
        window_size_mins=args.window_size_mins,
        hop_mins=args.hop_mins,
    )
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "input_context_count": report.get("input_context_count"),
        "minute_bearing_context_count": report.get("minute_bearing_context_count"),
        "event_window_count": report.get("event_window_count"),
        "window_summary": report.get("window_summary"),
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
