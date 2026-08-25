from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "temporal_episode_signature_lite" / "src"
    sys.path.insert(0, str(src))
    from temporal_episode_signature import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "temporal_episode_signature_count": report.get("temporal_episode_signature_count"),
        "comparison_available_count": report.get("comparison_available_count"),
        "zero_duration_temporal_rate_na_count": report.get("zero_duration_temporal_rate_na_count"),
        "same_start_order_indeterminate_count": report.get("same_start_order_indeterminate_count"),
        "hard_block_hits": report.get("hard_block_hits"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "production_release": report.get("production_release"),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
