from pathlib import Path

from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_difference import (
    build_process_variant_difference_explanations,
)


def _row(chain_id: str, consequence: str, *, latency: float, counter: bool, counter_family: str | None = None) -> dict:
    return {
        "reciprocal_process_chain_candidate_id": chain_id,
        "anchor_action_family_counts": {"PASS": 2, "PROGRESSION": 1},
        "response_action_family_counts": {"RECOVERY": 1},
        "response_consequence_candidate_counts": {consequence: 1},
        "counter_response_consequence_candidate_counts": {},
        "response_latency_candidate_seconds": latency,
        "counter_response_visible": counter,
        "counter_response_action_family_counts": {counter_family: 1} if counter_family else {},
        "anchor_episode_candidate_id": f"a-{chain_id}",
        "response_episode_candidate_id": f"r-{chain_id}",
        "counter_response_episode_candidate_id": f"c-{chain_id}" if counter else None,
    }


def _payload(*rows: dict) -> dict:
    return {
        "status": "PASS",
        "reciprocal_process_chain_candidates": list(rows),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_modal_vs_deviant_process_resolution_exposes_visible_difference_candidates():
    result = build_process_variant_difference_explanations(_payload(
        _row("m1", "SAME_TEAM_CONTINUATION_CANDIDATE", latency=1.0, counter=True, counter_family="PASS"),
        _row("m2", "SAME_TEAM_CONTINUATION_CANDIDATE", latency=1.2, counter=True, counter_family="PASS"),
        _row("d1", "OPPONENT_HANDOVER_CANDIDATE", latency=3.0, counter=False),
    ))
    assert result["status"] == "PASS"
    assert result["process_variant_difference_explanation_count"] == 1
    row = result["process_variant_difference_explanations"][0]
    assert row["modal_resolution_class_candidate"] == "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT"
    assert row["deviant_resolution_class_candidate"] == "ADVERSE_HANDOVER_VISIBLE_VARIANT"
    dimensions = {item["observation_dimension"] for item in row["visible_difference_candidates"]}
    assert "response_latency_median_candidate_seconds" in dimensions
    assert "counter_response_visible_count" in dimensions
    assert "counter_response_action_family_presence_counts" in dimensions
    assert row["difference_is_causal_explanation"] is False
    assert row["deviant_is_failure_truth"] is False


def test_right_censoring_is_excluded_from_modal_deviant_comparison():
    result = build_process_variant_difference_explanations(_payload(
        _row("m1", "SAME_TEAM_CONTINUATION_CANDIDATE", latency=1.0, counter=True),
        _row("m2", "SAME_TEAM_CONTINUATION_CANDIDATE", latency=1.1, counter=True),
        _row("c1", "RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE", latency=5.0, counter=False),
    ))
    assert result["status"] == "NO_ELIGIBLE_COMPARISON"
    assert result["right_censoring_used_as_counterevidence"] is False


def test_tied_modal_resolution_does_not_invent_a_baseline():
    result = build_process_variant_difference_explanations(_payload(
        _row("a", "SAME_TEAM_CONTINUATION_CANDIDATE", latency=1.0, counter=True),
        _row("b", "OPPONENT_HANDOVER_CANDIDATE", latency=2.0, counter=False),
    ))
    assert result["status"] == "NO_ELIGIBLE_COMPARISON"
    assert result["process_variant_difference_explanations"] == []


def test_no_sample_match_identity_leak():
    text = (Path(__file__).resolve().parents[1] / "src" / "process_variant_difference.py").read_text(encoding="utf-8").casefold()
    assert not any(token in text for token in ("genclerbirligi", "fenerbahce", "15.08.2026", "galatasaray", "besiktas"))
