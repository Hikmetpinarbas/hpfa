from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

import csv_surface_reader as _reader
from content_role_bridge import install_content_team_binding

install_content_team_binding(_reader)
main = _reader.main

if __name__ == "__main__":
    raise SystemExit(main())
