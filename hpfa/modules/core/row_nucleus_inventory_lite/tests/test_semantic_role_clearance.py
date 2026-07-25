from __future__ import annotations

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory import (
    semantic_clearance,
)


def _record(
    role: str,
    eligibility: str,
    *,
    family: str | None = None,
    mapping_status: str = "EXACT_REVIEWED_CANDIDATE",
    source_format: str = "csv",
) -> dict[str, str | None]:
    return {
        "semantic_role_candidate": role,
        "downstream_eligibility": eligibility,
        "action_family_candidate": family,
        "mapping_status": mapping_status,
        "source_format": source_format,
    }


def _aggregate_overlay() -> dict[str, str | None]:
    return _record(
        "AGGREGATE_METRIC_LABEL",
        "AGGREGATE_ONLY",
        mapping_status="XLSX_AGGREGATE_LABEL_CANDIDATE",
        source_format="xlsx",
    )


def test_action_anchor_requires_one_action_family() -> None:
    cleared, *_ = semantic_clearance(
        [_record("ACTION_ANCHOR", "ACTION_CANDIDATE_ELIGIBLE")]
    )
    assert cleared is False


def test_action_anchor_with_one_family_clears_with_aggregate_overlay() -> None:
    cleared, statuses, roles, families, eligibilities = semantic_clearance(
        [
            _record("ACTION_ANCHOR", "ACTION_CANDIDATE_ELIGIBLE", family="PASS"),
            _aggregate_overlay(),
        ]
    )
    assert cleared is True
    assert statuses == ["EXACT_REVIEWED_CANDIDATE", "XLSX_AGGREGATE_LABEL_CANDIDATE"]
    assert roles == ["ACTION_ANCHOR", "AGGREGATE_METRIC_LABEL"]
    assert families == ["PASS"]
    assert eligibilities == ["ACTION_CANDIDATE_ELIGIBLE", "AGGREGATE_ONLY"]


def test_reviewed_context_interval_does_not_require_action_family() -> None:
    cleared, *_ = semantic_clearance(
        [_record("CONTEXT_INTERVAL", "CONTEXT_ONLY"), _aggregate_overlay()]
    )
    assert cleared is True


def test_reviewed_participation_interval_does_not_require_action_family() -> None:
    cleared, *_ = semantic_clearance(
        [_record("PARTICIPATION_INTERVAL", "PARTICIPATION_ONLY"), _aggregate_overlay()]
    )
    assert cleared is True


def test_reviewed_derived_consequence_does_not_require_action_family() -> None:
    cleared, *_ = semantic_clearance(
        [
            _record("DERIVED_CONSEQUENCE_CANDIDATE", "DERIVED_ONLY"),
            _aggregate_overlay(),
        ]
    )
    assert cleared is True


def test_reviewed_terminal_outcome_does_not_require_action_family() -> None:
    cleared, *_ = semantic_clearance(
        [
            _record("TERMINAL_OUTCOME_CANDIDATE", "TERMINAL_OUTCOME_ONLY"),
            _aggregate_overlay(),
        ]
    )
    assert cleared is True


def test_reviewed_admin_marker_without_family_clears() -> None:
    cleared, *_ = semantic_clearance(
        [_record("ADMINISTRATIVE_MARKER", "ADMIN_ONLY")]
    )
    assert cleared is True


def test_reviewed_reference_without_family_clears() -> None:
    cleared, *_ = semantic_clearance(
        [_record("OPPONENT_ACTION_REFERENCE", "REFERENCE_ONLY")]
    )
    assert cleared is True


def test_unknown_role_remains_review_required() -> None:
    cleared, *_ = semantic_clearance(
        [_record("UNREGISTERED_ROLE", "CONTEXT_ONLY")]
    )
    assert cleared is False


def test_token_fallback_remains_review_required() -> None:
    cleared, *_ = semantic_clearance(
        [
            _record(
                "CONTEXT_INTERVAL",
                "CONTEXT_ONLY",
                mapping_status="TOKEN_FALLBACK_REVIEW_REQUIRED",
            )
        ]
    )
    assert cleared is False


def test_wrong_role_eligibility_pair_remains_review_required() -> None:
    cleared, *_ = semantic_clearance(
        [_record("CONTEXT_INTERVAL", "PARTICIPATION_ONLY")]
    )
    assert cleared is False
