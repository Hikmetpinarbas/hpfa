from __future__ import annotations

"""Compatibility shim for XLSX Surface Reader Lite V1.

The active implementation is HPFA-owned and stdlib-only under the
`xlsx_surface_reader` package. This file remains only for historical imports
and direct-file tests. No external workbook library is required at runtime.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from xlsx_surface_reader.native_reader import *  # noqa: F401,F403
