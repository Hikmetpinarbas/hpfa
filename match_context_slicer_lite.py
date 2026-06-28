from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "match_context_slicer_lite" / "src"
    sys.path.insert(0, str(src))
    from match_context_slicer import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "input_context_count": report.get("input_context_count"),
        "context_slice_count": report.get("context_slice_count"),
        "event_window_count": report.get("event_window_count"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "possession_truth": report.get("possession_truth"),
        "sequence_truth": report.get("sequence_truth"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
