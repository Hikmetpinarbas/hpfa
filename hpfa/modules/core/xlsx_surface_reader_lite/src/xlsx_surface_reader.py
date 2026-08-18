from __future__ import annotations

"""Compatibility shim for XLSX Surface Reader Lite V1.

The active implementation is HPFA-owned and stdlib-only under the
`xlsx_surface_reader` package. This file remains only for historical imports
and direct-file tests. No external workbook library is required at runtime.
"""

from hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader.native_reader import *  # noqa: F401,F403
