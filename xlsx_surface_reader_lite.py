from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "xlsx_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from xlsx_runtime_guard import XlsxRuntimeGuardError, guard_cli_arguments
from xlsx_surface_reader import main


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
