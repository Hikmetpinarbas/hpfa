from __future__ import annotations

import sys
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[2]
XML_SRC = CORE_ROOT / "xml_surface_reader_lite" / "src"
if str(XML_SRC) not in sys.path:
    sys.path.insert(0, str(XML_SRC))
