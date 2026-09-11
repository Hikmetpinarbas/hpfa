from hpfa.modules.core.trackable_action_trace_candidates_lite.src.temporal_relation_admission_adapter import (
    bind_temporal_relation_admission,
)


def _context():
    return {
        "time_admission_status": "ADMITTED",
        "provider_time_semantic_admission": {
            "status": "ADMITTED",
            "time_basis_admission_status": "ADMITTED",
            "time_basis_candidate": "ABSOLUTE_MATCH_SECONDS",
            "unit_admission_status": "ADMITTED",
            "unit_candidate": "SECOND",
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "rule_id": "sportsbase_like_start_end_absolute_seconds_v1",
        },
    }


def _trace_payload():
    return {
        "status": "PASS",
        "module_status": "PASS",
        "review_hits": [],
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "tat_a",
                "period_candidate": "1",
                "start_candidate": "10.0",
                "end_candidate": "11.0",
            },
            {
                "trackable_action_trace_candidate_id": "tat_same",
                "period_candidate": "1",
                "start_candidate": "10.0",
                "end_candidate": "12.0",
            },
            {
                "trackable_action_trace_candidate_id": "tat_overlap",
                "period_candidate": "1",
                "start_candidate": "10.5",
                "end_candidate": "12.5",
            },
            {
                "trackable_action_trace_candidate_id": "tat_after",
                "period_candidate": "1",
                "start_candidate": "13.0",
                "end_candidate": "14.0",
            },
            {
                "trackable_action_trace_candidate_id": "tat_period2",
                "period_candidate": "2",
                "start_candidate": "13.0",
                "end_candidate": "14.0",
            },
        ],
    }


def _relation_map(payload):
    return {
        (
            row["anchor_trackable_action_trace_candidate_id"],
            row["candidate_trackable_action_trace_candidate_id"],
        ): row["relation_state"]
        for row in payload["temporal_relation_admission_records"]
    }


def test_admitted_absolute_seconds_emit_after_same_time_and_indeterminate_without_row_order():
    payload = bind_temporal_relation_admission(_trace_payload(), _context())
    relations = _relation_map(payload)
    assert relations[("tat_a", "tat_same")] == "SAME_TIME_UNORDERED"
    assert relations[("tat_a", "tat_overlap")] == "ORDER_INDETERMINATE"
    assert relations[("tat_a", "tat_after")] == "AFTER_CONFIRMED"
    assert payload["same_timestamp_is_total_order"] is False
    assert payload["source_row_order_is_temporal_truth"] is False
    assert payload["cross_period_temporal_relation_admitted"] is False
    assert not any("tat_period2" in pair for pair in relations)


def test_unadmitted_time_contract_emits_no_directional_relation():
    context = _context()
    context["provider_time_semantic_admission"]["status"] = "REVIEW_REQUIRED"
    payload = bind_temporal_relation_admission(_trace_payload(), context)
    assert payload["temporal_relation_admission_records"] == []
    assert payload["provider_time_contract_admission_status"] == "NOT_ADMITTED"
    assert payload["status"] == "REVIEW_REQUIRED"


def test_same_timestamp_ordering_permission_is_rejected():
    context = _context()
    context["provider_time_semantic_admission"]["same_timestamp_internal_ordering_allowed"] = True
    payload = bind_temporal_relation_admission(_trace_payload(), context)
    assert payload["temporal_relation_admission_records"] == []
    assert "same_timestamp_internal_ordering_must_remain_false" in payload["provider_time_contract_review_reasons"]
