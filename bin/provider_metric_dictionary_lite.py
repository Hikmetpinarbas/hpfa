from __future__ import annotations

import argparse
import json
from pathlib import Path

from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import write_dictionary_report


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Provider Metric Dictionary Lite V1")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = write_dictionary_report(Path(args.repo_root), Path(args.output))
    print(json.dumps({
        "module_id": report["module_id"],
        "status": report["status"],
        "metric_record_count": report["metric_record_count"],
        "provider_definition_ready_count": report["provider_definition_ready_count"],
        "hpfa_domain_contract_ready_count": report["hpfa_domain_contract_ready_count"],
        "open_conflict_count": report["open_conflict_count"],
        "canonical_event_count": report["canonical_event_count"],
        "production_release": report["production_release"],
    }, sort_keys=True))
    return 0 if report["status"] in {"SPEC_ONLY", "REVIEW_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
