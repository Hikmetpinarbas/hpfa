from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_label_value_semantics import main

if __name__ == "__main__":
    raise SystemExit(main())
