from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
    sys.path.insert(0, str(src))
    from minimum_viable_context import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "surface_row_count": report.get("surface_row_count"),
        "context_candidate_count": report.get("context_candidate_count"),
        "canonical_event_count": report.get("canonical_event_count"),
        "phase_truth": report.get("phase_truth"),
        "possession_truth": report.get("possession_truth"),
        "sequence_truth": report.get("sequence_truth"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
