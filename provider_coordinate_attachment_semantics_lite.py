from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "provider_coordinate_attachment_semantics_lite"
    / "src"
)
sys.path.insert(0, str(SRC))

from provider_coordinate_attachment_semantics import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
