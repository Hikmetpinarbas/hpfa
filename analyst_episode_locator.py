from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
    sys.path.insert(0, str(src))
    from analyst_episode_locator import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-inter-layer-gap-seconds", type=float, default=20.0)
    args = parser.parse_args()

    report = write_outputs(
        args.input_dir,
        args.out_dir,
        max_inter_layer_gap_seconds=args.max_inter_layer_gap_seconds,
    )
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "episode_candidate_count": report.get("episode_candidate_count"),
        "administrative_boundary_candidate_count": report.get("administrative_boundary_candidate_count"),
        "administrative_boundary_review_debt_count": report.get("administrative_boundary_review_debt_count"),
        "same_time_unordered_layer_count": report.get("same_time_unordered_layer_count"),
        "context_assignment_complete": report.get("context_assignment_complete"),
        "reflection_inflation_prevented": report.get("reflection_inflation_prevented"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "rhythm_truth": report.get("rhythm_truth"),
        "production_release": report.get("production_release"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
