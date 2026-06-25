from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    src = repo_root / "hpfa" / "modules" / "core" / "axis_integrity_tagger_lite" / "src"
    sys.path.insert(0, str(src))
    from axis_integrity_tagger import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=repo_root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "axis_integrity_score": report.get("axis_integrity_score"),
        "axis_status": report.get("axis_status"),
        "downstream_permissions": report.get("downstream_permissions"),
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
