from hpfa.modules.core.active_match_spine_runner.src.process_sequence_information import build_process_sequence_information


def test_sequence_information_preserves_same_time_state_sets_and_counts_transitions():
    signatures = [
        {
            "process_development_signature_id": "p1",
            "period_candidate": "1",
            "process_interval_duration_candidate": 8.0,
            "layers": [
                {"timestamp_candidate": 10.0, "action_family_candidates": ["PASS", "CARRY"]},
                {"timestamp_candidate": 12.0, "action_family_candidates": ["PASS"]},
                {"timestamp_candidate": 15.0, "action_family_candidates": ["SHOT"]},
            ],
        },
        {
            "process_development_signature_id": "p2",
            "period_candidate": "2",
            "process_interval_duration_candidate": 6.0,
            "layers": [
                {"timestamp_candidate": 20.0, "action_family_candidates": ["CARRY", "PASS"]},
                {"timestamp_candidate": 23.0, "action_family_candidates": ["PASS"]},
                {"timestamp_candidate": 25.0, "action_family_candidates": ["LOSS"]},
            ],
        },
    ]

    result = build_process_sequence_information(signatures)

    assert result["eligible_process_signature_n"] == 2
    assert result["distinct_trace_variant_n"] == 2
    assert result["transition_count"] == 4
    assert result["state_token_basis"] == "SORTED_ACTION_FAMILY_SET_WITHIN_ADMITTED_TEMPORAL_LAYER"
    assert result["same_timestamp_internal_ordering_allowed"] is False

    transitions = {(r["from_state"], r["to_state"]): r for r in result["transition_profile"]}
    first = transitions[("CARRY+PASS", "PASS")]
    assert first["transition_n"] == 2
    assert first["conditional_transition_share_candidate"] == 1.0
    assert first["median_inter_layer_seconds_candidate"] == 2.5

    entropy = {r["from_state"]: r for r in result["downstream_transition_entropy"]}
    assert entropy["PASS"]["distinct_downstream_state_n"] == 2
    assert entropy["PASS"]["shannon_entropy_bits_candidate"] == 1.0
    assert entropy["PASS"]["normalized_transition_entropy_candidate"] == 1.0

    assert result["period_trace_distribution_comparisons"][0]["jensen_shannon_divergence_bits_candidate"] == 1.0
    assert result["trace_variant_is_tactical_pattern_truth"] is False
    assert result["transition_probability_is_causal_truth"] is False
    assert result["entropy_is_quality_or_creativity_truth"] is False


def test_sequence_information_has_no_fake_information_when_empty():
    result = build_process_sequence_information([])
    assert result["status"] == "NOT_APPLICABLE"
    assert result["eligible_process_signature_n"] == 0
    assert result["transition_count"] == 0
    assert result["process_duration_profile"]["median_process_interval_seconds_candidate"] is None
