from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "xlsx_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

import xlsx_surface_reader
from xlsx_header_semantics import semantic_header_norm
from xlsx_runtime_guard import XlsxRuntimeGuardError, guard_cli_arguments

# Product execution must preserve semantically meaningful punctuation such as
# the percent marker before duplicate-header detection and metric inventory.
xlsx_surface_reader.norm = semantic_header_norm
main = xlsx_surface_reader.main


if __name__ == "__main__":
    try:
        guard_cli_arguments()
    except XlsxRuntimeGuardError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED",
                    "hard_block_hits": [str(exc)],
                    "active_match_evidence_pass": False,
                    "canonical_event_count": "UNKNOWN",
                    "production_release": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(2) from exc
    raise SystemExit(main())
