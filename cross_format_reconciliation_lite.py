from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

import cross_format_reconciliation as core

_CORE_NORM_FIELD = core.norm_field
_MISSING_IDENTIFIER_TOKENS = {"none", "null", "nan", "n/a", "na", "-"}


def normalize_identifier_candidate(value: Any) -> str | None:
    """Preserve provider identifier representation until namespace semantics are admitted."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in _MISSING_IDENTIFIER_TOKENS:
        return None
    return text


def runtime_norm_field(field: str, value: Any) -> str | None:
    if field == "id":
        return normalize_identifier_candidate(value)
    return _CORE_NORM_FIELD(field, value)


# Runtime adaptation for the reconstructed historical capability: identifiers are
# representation-sensitive candidates, while measurement fields retain numeric
# normalization. This must remain candidate-only until provider/version namespace
# semantics explicitly authorize any stronger equivalence.
core.norm_field = runtime_norm_field

from research_hardening import guarded_main

if __name__ == "__main__":
    raise SystemExit(guarded_main())
