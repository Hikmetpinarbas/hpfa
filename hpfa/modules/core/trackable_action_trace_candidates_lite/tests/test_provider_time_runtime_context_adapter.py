from hpfa.modules.core.trackable_action_trace_candidates_lite.src import (
    provider_time_runtime_context_adapter as adapter,
)


def test_runtime_context_uses_canonical_provider_time_producer(monkeypatch, tmp_path):
    monkeypatch.setattr(
        adapter.provider_time,
        "build_time_admission",
        lambda _root: {
            "status": "ADMITTED",
            "rule_id": "sportsbase_like_start_end_absolute_seconds_v1",
            "time_basis_admission_status": "ADMITTED",
            "time_basis_candidate": "ABSOLUTE_MATCH_SECONDS",
            "unit_admission_status": "ADMITTED",
            "unit_candidate": "SECOND",
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
    )
    payload = adapter.build_provider_time_runtime_context(tmp_path)
    assert payload["time_admission_status"] == "ADMITTED"
    contract = payload["provider_time_semantic_admission"]
    assert contract["time_basis_candidate"] == "ABSOLUTE_MATCH_SECONDS"
    assert contract["unit_candidate"] == "SECOND"
    assert payload["runtime_context_source"] == "CANONICAL_PROVIDER_TIME_SEMANTIC_ADMISSION_PRODUCER"
    assert payload["runtime_context_is_minimum_viable_context_replacement"] is False
    assert payload["source_row_order_is_temporal_truth"] is False
    assert payload["same_timestamp_internal_ordering_allowed"] is False


def test_runtime_context_preserves_review_required(monkeypatch, tmp_path):
    monkeypatch.setattr(
        adapter.provider_time,
        "build_time_admission",
        lambda _root: {
            "status": "REVIEW_REQUIRED",
            "review_reasons": ["absolute_match_time_basis_not_demonstrated"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
    )
    payload = adapter.build_provider_time_runtime_context(tmp_path)
    assert payload["time_admission_status"] == "REVIEW_REQUIRED"
    assert payload["provider_time_semantic_admission"]["status"] == "REVIEW_REQUIRED"
