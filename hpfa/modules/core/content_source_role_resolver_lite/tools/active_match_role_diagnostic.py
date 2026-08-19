from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as resolver,
)


def _compact(values: object) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    args = parser.parse_args()

    input_root = Path(args.input_root).expanduser().resolve(strict=False)
    report = resolver.build_report(input_root, root=ROOT)

    print("HPFA #181 RECONCILIATION ROLE DIAGNOSTIC")
    print("status=" + str(report.get("status")))
    print(
        "role_resolution_applicable_file_count="
        + str(report.get("role_resolution_applicable_file_count"))
    )
    print(
        "role_candidate_admitted_file_count="
        + str(report.get("role_candidate_admitted_file_count"))
    )
    print("unresolved_role_file_count=" + str(report.get("unresolved_role_file_count")))
    print("resolved_role_counts=" + _compact(report.get("resolved_role_counts") or {}))
    print("hard_block_hits=" + _compact(report.get("hard_block_hits") or []))
    print("review_hits=" + _compact(report.get("review_hits") or []))

    for record in report.get("files", []) or []:
        resolution = record.get("resolution") or {}
        print(
            "surface="
            + _compact(
                {
                    "path": record.get("relative_path"),
                    "format": record.get("extension"),
                    "role": resolution.get("resolved_source_role"),
                    "resolution_status": resolution.get("resolution_status"),
                    "reasons": resolution.get("resolution_reasons") or [],
                    "votes": resolution.get("reviewed_label_role_votes") or {},
                    "aggregate_support": resolution.get("aggregate_semantic_support_candidates") or [],
                    "cross_format_support": resolution.get("cross_format_support_candidates") or [],
                    "filename_support_used_for_admission": False,
                }
            )
        )

    print("validated_team_identity=false")
    print("validated_player_identity=false")
    print("validated_event_identity=false")
    print("canonical_event_count=UNKNOWN")
    print("production_release=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
