from __future__ import annotations

from pathlib import Path

POLICY_ID = "termux_delivery_output_policy_v1"
POLICY_IS_FOOTBALL_TRUTH = False
POLICY_IS_RUNTIME_AUTHORITY = False

TERMUX_DIRECT_DOWNLOAD_OUTPUT_ROOTS = (
    Path("/sdcard/Download/HPFA"),
    Path("/storage/emulated/0/Download/HPFA"),
)


def restricted_output_roots() -> tuple[Path, ...]:
    """Return delivery-only roots that must remain flat on Termux/Android."""
    return TERMUX_DIRECT_DOWNLOAD_OUTPUT_ROOTS
