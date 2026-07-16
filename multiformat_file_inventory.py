from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "multiformat_file_inventory_lite" / "src"
sys.path.insert(0, str(SRC))

from multiformat_file_inventory import main

if __name__ == "__main__":
    raise SystemExit(main())
