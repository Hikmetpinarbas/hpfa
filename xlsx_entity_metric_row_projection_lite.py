from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "xlsx_entity_metric_row_projection_lite" / "src"
sys.path.insert(0, str(SRC))

from xlsx_entity_metric_row_projection import main


if __name__ == "__main__":
    raise SystemExit(main())
