from __future__ import annotations

"""Compatibility adapter for the authoritative partial-order trace variant producer.

The implementation lives in ``partial_order_trace_variant_lite``. Keeping this
path as a thin import preserves callers without creating a second sequence/
variant engine or a second contract surface.
"""

from hpfa.modules.core.partial_order_trace_variant_lite.src.partial_order_trace_variant import (
    ORDER_VOCABULARY as ORDER_STATES,
    build_partial_order_trace_variants,
)

__all__ = ["ORDER_STATES", "build_partial_order_trace_variants"]
