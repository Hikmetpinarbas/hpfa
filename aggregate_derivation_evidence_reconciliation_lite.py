from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "aggregate_derivation_evidence_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from aggregate_derivation_evidence_reconciliation import main


if __name__ == "__main__":
    raise SystemExit(main())
