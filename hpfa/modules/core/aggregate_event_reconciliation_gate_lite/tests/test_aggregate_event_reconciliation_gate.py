from hpfa.modules.core.aggregate_event_reconciliation_gate_lite.src.aggregate_event_reconciliation_gate import reconcile_aggregate_event_counts


def test_exact_parity_passes_without_releasing_production():
    result = reconcile_aggregate_event_counts(
        {"base_event_family_counts": {"SHOT": 37, "PASS": 1045}},
        {"aggregate_family_counts": {"SHOT": 37, "PASS": 1045}},
    )
    assert result["decision_state"] == "PASS_EXACT_AGGREGATE_EVENT_COUNT_PARITY"
    assert result["blocked_families"] == []
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_material_shot_inflation_is_blocked():
    result = reconcile_aggregate_event_counts(
        {"base_event_family_counts": {"SHOT": 235}},
        {"aggregate_family_counts": {"SHOT": 37}},
    )
    row = result["family_reconciliation"][0]
    assert result["decision_state"] == "BLOCKED_AGGREGATE_EVENT_RECONCILIATION"
    assert result["blocked_families"] == ["SHOT"]
    assert row["signed_delta"] == 198
    assert row["surface_to_aggregate_ratio"] == 235 / 37


def test_pass_shortfall_is_blocked_with_zero_default_tolerance():
    result = reconcile_aggregate_event_counts(
        {"base_event_family_counts": {"PASS": 1017}},
        {"aggregate_family_counts": {"PASS": 1045}},
    )
    assert result["blocked_families"] == ["PASS"]
    assert result["family_reconciliation"][0]["signed_delta"] == -28


def test_explicit_tolerance_remains_review_required():
    result = reconcile_aggregate_event_counts(
        {"base_event_family_counts": {"PASS": 1017}},
        {"aggregate_family_counts": {"PASS": 1045}},
        {"family_tolerances": {"PASS": 28}},
    )
    assert result["decision_state"] == "REVIEW_REQUIRED_EXPLICIT_RECONCILIATION_TOLERANCE"
    assert result["review_families"] == ["PASS"]
    assert result["production_release"] is False


def test_missing_family_is_compared_as_zero_not_ignored():
    result = reconcile_aggregate_event_counts(
        {"base_event_family_counts": {}},
        {"aggregate_family_counts": {"SHOT": 3}},
    )
    assert result["blocked_families"] == ["SHOT"]
    assert result["family_reconciliation"][0]["provisional_surface_count"] == 0


def test_invalid_negative_count_fails_closed():
    try:
        reconcile_aggregate_event_counts(
            {"base_event_family_counts": {"SHOT": -1}},
            {"aggregate_family_counts": {"SHOT": 1}},
        )
    except ValueError as exc:
        assert "invalid_base_event_family_counts" in str(exc)
    else:
        raise AssertionError("negative count must fail closed")
