from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from event_label_structural_progression_evidence import (  # noqa: E402
    _label_progression_profile,
    _verification,
)


def test_contradictory_provider_outcomes_are_ambiguous_and_blocked():
    matches = [
        {
            "record_id": "success_record",
            "progression_candidate": "PROGRESSIVE_CANDIDATE",
            "outcome_candidate": "SUCCESS",
        },
        {
            "record_id": "failure_record",
            "progression_candidate": "PROGRESSIVE_CANDIDATE",
            "outcome_candidate": "FAILURE",
        },
    ]

    profile = _label_progression_profile(matches)

    assert profile["provider_successful_outcome_candidate"] is True
    assert profile["provider_unsuccessful_outcome_candidate"] is True
    assert profile["provider_outcome_conflicted"] is True

    verification_status, downstream = _verification(
        "EXACT_REVIEWED_RULE",
        "",
        profile,
        {"zone_delta_class": "ZONE_GAIN_CANDIDATE"},
        {
            "coordinate_support": "SUPPORTED_CANDIDATE",
            "outcome_support": "SUPPORTED_CANDIDATE",
            "duration_support": "SUPPORTED_CANDIDATE",
            "consequence_support": "SUPPORTED_CANDIDATE",
            "aggregate_support": "SUPPORT_ONLY",
        },
    )

    assert verification_status == "LABEL_AMBIGUOUS"
    assert downstream == "DOWNSTREAM_BLOCKED_REVIEW_REQUIRED"
