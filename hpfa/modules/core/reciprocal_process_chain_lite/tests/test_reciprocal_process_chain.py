from pathlib import Path

from hpfa.modules.core.reciprocal_process_chain_lite.src.reciprocal_process_chain import (
    build_reciprocal_process_chains,
    validate_out,
)


def _seq(seq_id: str, team: str, start: float, end: float, family: str) -> dict:
    return {
        "visible_action_sequence_candidate_id": seq_id,
        "team_identity_candidate_id": team,
        "period_candidate": "1",
        "start_time_candidate": start,
        "end_time_candidate": end,
        "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "action_family_counts": {family: 1},
        "consequence_candidate_counts": {"SAME_TEAM_CONTINUATION_CANDIDATE": 1},
        "trackable_action_trace_candidate_ids": [f"tr:{seq_id}"],
    }


def _payload(rows: list[dict]) -> dict:
    return {
        "module_id": "visible_action_sequence_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "visible_action_sequence_candidates": rows,
        "visible_action_sequence_candidate_count": len(rows),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }


def _temporal() -> dict:
    return {
        "module_id": "temporal_episode_signature_lite_v1",
        "status": "PASS",
        "temporal_episode_signatures": [
            {
                "episode_candidate_id": "ep1",
                "period_candidate": "1",
                "start_second_candidate": 0.0,
                "end_second_candidate": 9.9,
            },
            {
                "episode_candidate_id": "ep2",
                "period_candidate": "1",
                "start_second_candidate": 10.0,
                "end_second_candidate": 19.9,
            },
            {
                "episode_candidate_id": "ep3",
                "period_candidate": "1",
                "start_second_candidate": 20.0,
                "end_second_candidate": 40.0,
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_builds_different_team_response_and_counter_response() -> None:
    rows = [
        _seq("a", "TEAM_A", 2.0, 5.0, "DRIBBLE"),
        _seq("b", "TEAM_B", 12.0, 15.0, "TACKLE"),
        _seq("c", "TEAM_A", 22.0, 25.0, "PASS"),
    ]
    report = build_reciprocal_process_chains(_payload(rows), _temporal())
    assert report["status"] == "PASS"
    assert report["reciprocal_process_chain_candidate_count"] >= 1
    first = report["reciprocal_process_chain_candidates"][0]
    assert first["anchor_team_identity_candidate_id"] == "TEAM_A"
    assert first["response_team_identity_candidate_id"] == "TEAM_B"
    assert first["counter_response_visible"] is True
    assert first["counter_response_team_identity_candidate_id"] == "TEAM_A"
    assert first["response_relation_is_causal_truth"] is False
    assert first["response_relation_is_tactical_truth"] is False


def test_same_timestamp_does_not_create_response_order() -> None:
    rows = [
        _seq("a", "TEAM_A", 2.0, 5.0, "DRIBBLE"),
        _seq("b", "TEAM_B", 5.0, 7.0, "TACKLE"),
    ]
    report = build_reciprocal_process_chains(_payload(rows), _temporal())
    assert report["reciprocal_process_chain_candidate_count"] == 0
    assert report["same_time_response_candidate_block_count"] == 1
    assert report["same_timestamp_internal_ordering_allowed"] is False


def test_unknown_team_not_forced_into_reciprocal_alternation() -> None:
    rows = [
        _seq("a", "TEAM_A", 2.0, 5.0, "PASS"),
        _seq("u", "", 8.0, 9.0, "RECOVERY"),
        _seq("b", "TEAM_B", 12.0, 15.0, "SHOT"),
    ]
    report = build_reciprocal_process_chains(_payload(rows), _temporal())
    assert any("sequence_not_reciprocal_eligible:u" == hit for hit in report["review_hits"])
    assert report["reciprocal_process_chain_candidate_count"] >= 1


def test_sequence_crossing_episode_boundary_is_not_uniquely_bound() -> None:
    rows = [
        _seq("a", "TEAM_A", 8.0, 12.0, "DRIBBLE"),
        _seq("b", "TEAM_B", 14.0, 16.0, "TACKLE"),
    ]
    report = build_reciprocal_process_chains(_payload(rows), _temporal())
    assert report["reciprocal_process_chain_candidate_count"] == 1
    chain = report["reciprocal_process_chain_candidates"][0]
    assert chain["anchor_episode_candidate_id"] is None
    assert chain["anchor_episode_binding_status"] == "SEQUENCE_CROSSES_EPISODE_BOUNDARY_REVIEW_REQUIRED"
    assert "SEQUENCE_CROSSES_EPISODE_BOUNDARY_REVIEW_REQUIRED" in chain["review_hits"]
    assert report["status"] == "REVIEW_REQUIRED"


def test_current_runner_requires_current_temporal_generation() -> None:
    source = Path("reciprocal_process_chain_current_v1.py").read_text(encoding="utf-8")
    assert "run_current_episode_lane" in source
    assert "current_temporal_generated" in source
    assert "current_invocation_artifacts" in source
    assert "current_episode_lane_fail_closed_or_current_temporal_output_missing" in source


def test_no_sample_match_identity_leak() -> None:
    paths = [
        Path("hpfa/modules/core/reciprocal_process_chain_lite/src/reciprocal_process_chain.py"),
        Path("reciprocal_process_chain_current_v1.py"),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source


def test_nested_phone_output_rejected() -> None:
    try:
        validate_out("/sdcard/Download/HPFA/nested")
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested phone output should be rejected")
