from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def main() -> int:
    root = repo_root()
    src = root / "hpfa" / "modules" / "core" / "identity_review_resolution_lite" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from identity_review_resolution import write_outputs

    parser = argparse.ArgumentParser(description="HPFA Identity Review Resolution Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "candidate_cluster_count": report.get("candidate_cluster_count"),
        "duplicate_risk_candidate_count": report.get("duplicate_risk_candidate_count"),
        "blocking_reasons": report.get("blocking_reasons"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
