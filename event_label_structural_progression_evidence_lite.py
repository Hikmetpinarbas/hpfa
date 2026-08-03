from __future__ import annotations

import sys
from pathlib import Path

SRC = (
    Path(__file__).resolve().parent
    / "hpfa"
    / "modules"
    / "core"
    / "event_label_structural_progression_evidence_lite"
    / "src"
)
sys.path.insert(0, str(SRC))

from event_label_structural_progression_evidence import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
