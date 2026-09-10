from hpfa.modules.core.partial_order_trace_variant_lite.src.partial_order_trace_variant import (
    build_partial_order_trace_variants,
)


def _trace(trace_id: str, start: float, occurrence_id: str) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": "binding_generic",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": f"actor_{trace_id}",
        "start_candidate": start,
        "period_candidate": "1",
        "action_family_candidates": ["PASS"],
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "supporting_evidence_atom_ids": [f"ea:{occurrence_id}"],
        "supporting_relation_candidate_ids": [f"rel:{occurrence_id}"],
        "reflection_context_action_bundle_candidate_ids": [],
        "primary_source_lineage_records": [{"source_sha256": f"sha:{occurrence_id}"}],
        "reflection_source_lineage_records": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence(trace_id: str, outcome: str, censored: bool = False) -> dict:
    return {
        "trackable_action_consequence_candidate_id": f"c:{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "primary_consequence_candidate": outcome,
        "right_censored_no_visible_follow_up": censored,
        "right_censoring_is_terminal_event": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _payloads() -> tuple[dict, dict, dict]:
    sequence = {
        "module_id": "visible_action_sequence_candidates_lite_v1",
        "status": "PASS",
        "visible_action_sequence_candidates": [{
            "visible_action_sequence_candidate_id": "s1",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_reason_candidate": "PERIOD_START",
            "end_reason_candidate": "PERIOD_END",
            "time_layer_candidate_ids": ["l1", "l2"],
            "sequence_occurrence_object_context_state": "NO_CONTEXT_VISIBLE",
            "sequence_occurrence_context_is_independent_support": False,
            "goalkeeper_context_is_sequence_participant_truth": False,
            "reflection_context_is_sequence_equivalence_truth": False,
            "sequence_occurrence_context_creates_event": False,
            "sequence_occurrence_context_ref_count_is_action_count": False,
            "canonical_event_count": "UNKNOWN",
        }],
        "visible_action_time_layer_candidates": [
            {"visible_action_time_layer_candidate_id": "l1", "start_candidate": 10.0, "trackable_action_trace_candidate_ids": ["t1"]},
            {"visible_action_time_layer_candidate_id": "l2", "start_candidate": 20.0, "trackable_action_trace_candidate_ids": ["t2"]},
        ],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    trace = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_trace_candidates": [
            _trace("t1", 10.0, "o1"),
            _trace("t2", 20.0, "o2"),
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    consequence = {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "status": "PASS",
        "trackable_action_consequence_candidates": [
            _consequence("t1", "SAME_TEAM_CONTINUATION_CANDIDATE", False),
            _consequence("t2", "RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE", True),
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return sequence, trace, consequence


def test_right_censoring_is_not_outcome_denominator_authority() -> None:
    result = build_partial_order_trace_variants(*_payloads())
    assert result["status"] == "PASS"
    assert result["right_censored_variant_node_count"] == 1
    assert result["non_censored_consequence_variant_node_count"] == 1
    assert result["right_censored_nodes_are_terminal_outcomes"] is False
    assert result["right_censored_nodes_are_failures"] is False
    assert result["right_censored_nodes_are_neutral_outcomes"] is False
    assert result["right_censored_nodes_are_counterevidence"] is False
    assert result["right_censored_node_count_is_recurrence_count"] is False
    assert result["outcome_signature_may_be_used_as_denominator_authority"] is False
    assert result["non_censored_outcome_signature_is_denominator_candidate_only"] is True

    variant = result["partial_order_trace_variants"][0]
    legacy = {row["outcome_candidate"]: row["count"] for row in variant["outcome_signature"]}
    non_censored = {row["outcome_candidate"]: row["count"] for row in variant["non_censored_outcome_signature"]}
    censoring = {row["censoring_state"]: row["count"] for row in variant["censoring_signature"]}

    assert legacy["RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE"] == 1
    assert "RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE" not in non_censored
    assert non_censored == {"SAME_TEAM_CONTINUATION_CANDIDATE": 1}
    assert censoring == {"RIGHT_CENSORED_OBSERVATION": 1}
    assert variant["outcome_signature_role"] == "LEGACY_CONSEQUENCE_LINEAGE_ONLY_NOT_DENOMINATOR_AUTHORITY"
    assert variant["outcome_denominator_authority"] == "NON_CENSORED_VISIBLE_CONSEQUENCE_NODES_ONLY"

    nodes = {row["trace_ref"]: row for row in variant["node_records"]}
    censored = nodes["t2"]
    assert censored["consequence_observation_state"] == "RIGHT_CENSORED_OBSERVATION"
    assert censored["right_censored_observation"] is True
    assert censored["right_censoring_is_terminal_outcome"] is False
    assert censored["right_censoring_is_failure"] is False
    assert censored["right_censoring_is_counterevidence"] is False
    assert censored["right_censoring_counts_as_recurrence_support"] is False


def test_no_sample_match_identity_leak() -> None:
    encoded = str(build_partial_order_trace_variants(*_payloads()))
    assert "Genclerbirligi" not in encoded
    assert "Fenerbahce" not in encoded
