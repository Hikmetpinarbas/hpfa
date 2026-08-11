from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "aggregate_derivation_evidence_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from aggregate_derivation_evidence_reconciliation import main
from runtime_source_guard import preflight_from_paths


def _arg_value(argv: list[str], flag: str) -> str | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


def _run(argv: list[str]) -> int:
    if "--active-match-execution" in argv:
        runtime = _arg_value(argv, "--runtime-authority")
        xlsx = _arg_value(argv, "--xlsx-row-projection")
        evidence = _arg_value(argv, "--evidence-atoms")
        if not runtime or not xlsx or not evidence:
            print(
                json.dumps(
                    {
                        "module_id": "aggregate_derivation_evidence_reconciliation_lite_v1",
                        "status": "FAIL_CLOSED",
                        "hard_block_hits": ["active_match_source_rehash_arguments_missing"],
                        "canonical_event_count": "UNKNOWN",
                        "production_release": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        try:
            preflight = preflight_from_paths(runtime, xlsx, evidence)
        except ValueError as exc:
            print(
                json.dumps(
                    {
                        "module_id": "aggregate_derivation_evidence_reconciliation_lite_v1",
                        "status": "FAIL_CLOSED",
                        "runtime_source_rehash_status": "FAIL_CLOSED",
                        "hard_block_hits": [str(exc)],
                        "canonical_event_count": "UNKNOWN",
                        "production_release": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        print(json.dumps({"runtime_source_rehash_preflight": preflight}, ensure_ascii=False))
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(_run(sys.argv[1:]))
