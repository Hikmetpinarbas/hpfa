from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "xml_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from xml_surface_reader import main


if __name__ == "__main__":
    raise SystemExit(main())
