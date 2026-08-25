from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "episode_feature_vector_lite" / "src"
    sys.path.insert(0, str(src))
    from episode_feature_vector import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "episode_feature_vector_count": report.get("episode_feature_vector_count"),
        "total_eligible_action_candidate_count": report.get("total_eligible_action_candidate_count"),
        "density_not_applicable_zero_duration_count": report.get("density_not_applicable_zero_duration_count"),
        "hard_block_hits": report.get("hard_block_hits"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "production_release": report.get("production_release"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
