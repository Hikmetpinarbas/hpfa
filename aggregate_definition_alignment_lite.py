from __future__ import annotations

import argparse
import json

from hpfa.modules.core.aggregate_definition_alignment_lite.src.aggregate_definition_alignment import (
    build_alignment,
    load_json,
    write_report,
)
from hpfa.modules.core.metric_definition_policy_lite.src.metric_definition_policy import (
    load_policy_pack,
)

__all__ = ["build_alignment", "load_json", "write_report"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-audit", required=True)
    parser.add_argument("--label-semantics", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--metric-policy")
    group.add_argument("--metric-config-dir")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    metric_policy = (
        load_json(args.metric_policy)
        if args.metric_policy
        else load_policy_pack(args.metric_config_dir)
    )
    report = build_alignment(
        load_json(args.xlsx_audit),
        load_json(args.label_semantics),
        metric_policy,
        load_json(args.registry),
    )
    destination = args.output
    from pathlib import Path

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    report["outputs"] = {"json": str(output)}
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: report.get(key)
                for key in (
                    "status",
                    "definition_candidate_count",
                    "alignment_decision_counts",
                    "hard_block_hits",
                    "review_hits",
                    "active_match_evidence_pass",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if report["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
