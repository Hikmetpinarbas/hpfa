from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "context_action_semantics_rebind_lite" / "src"
    sys.path.insert(0, str(src))
    from context_action_semantics_rebind import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, repo_root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "input_context_count": report.get("input_context_count"),
        "reviewed_provider_semantics_bound_count": report.get("reviewed_provider_semantics_bound_count"),
        "action_occurrence_eligible_count": report.get("action_occurrence_eligible_count"),
        "non_action_context_or_reference_count": report.get("non_action_context_or_reference_count"),
        "provider_semantics_unresolved_or_review_required_count": report.get("provider_semantics_unresolved_or_review_required_count"),
        "eligible_action_family_candidate_counts": report.get("eligible_action_family_candidate_counts"),
        "semantic_collision_audit": report.get("semantic_collision_audit"),
        "hard_block_hits": report.get("hard_block_hits"),
        "review_hits": report.get("review_hits"),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
