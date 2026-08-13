from __future__ import annotations

import re
from typing import Any

_PERCENT_WORDS = ("percent", "percentage", "pct")


def semantic_header_norm(value: Any) -> str:
    """Normalize a spreadsheet header without collapsing counts and rates.

    Punctuation is generally treated as layout noise, but a percent marker is
    semantic: ``Passes accurate`` and ``Passes accurate, %`` must remain two
    distinct columns. The marker is converted to a stable ``percent`` token
    before punctuation removal.
    """

    text = str(value or "").strip().casefold()
    has_percent_symbol = "%" in text
    text = text.replace("%", " percent ")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w]+", "_", text, flags=re.UNICODE)
    normalized = re.sub(r"_+", "_", text).strip("_")

    if has_percent_symbol and not any(
        normalized == token or normalized.endswith(f"_{token}")
        for token in _PERCENT_WORDS
    ):
        normalized = f"{normalized}_percent" if normalized else "percent"
    return normalized
