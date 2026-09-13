from __future__ import annotations

from pathlib import Path
from typing import Any

from hpfa.modules.core.provider_alias_field_semantics_lite.src import (
    provider_time_semantic_admission as provider_time,
)


def build_provider_time_runtime_context(input_dir: str | Path) -> dict[str, Any]:
    """Build the trace-time temporal context from the canonical provider-time producer.

    This removes dependency on the later-written minimum_viable_context artifact while
    preserving the exact same provider contract and fail-closed admission semantics.
    """
    admission = provider_time.build_time_admission(input_dir)
    status = str(admission.get("status") or "REVIEW_REQUIRED")
    return {
        "time_admission_status": status,
        "provider_time_semantic_admission": admission,
        "runtime_context_source": "CANONICAL_PROVIDER_TIME_SEMANTIC_ADMISSION_PRODUCER",
        "runtime_context_is_minimum_viable_context_replacement": False,
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
