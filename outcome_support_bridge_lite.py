from __future__ import annotations

import sys
from pathlib import Path

SRC = (
    Path(__file__).resolve().parent
    / "hpfa"
    / "modules"
    / "core"
    / "outcome_support_bridge_lite"
    / "src"
)
sys.path.insert(0, str(SRC))

from outcome_support_bridge import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
