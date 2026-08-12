from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "coordinate_frame_anchor_recheck_lite" / "src"
sys.path.insert(0, str(SRC))

from coordinate_frame_anchor_recheck import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
