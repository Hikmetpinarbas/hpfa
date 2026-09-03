from pathlib import Path

import pytest

from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile import (
    build_process_variant_profiles,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile_outputs import (
    write_outputs,
)


def _chain(
    chain_id: str,
    *,
    anchor_episode: str | None,
    response_episode: str | None,
    counter_episode: str | None = None,
    counter_visible: bool = False,
    response_consequence: str = "CONTINUATION_VISIBLE",
    counter_consequence: str | None = None,
) -> dict:
    return {
        "reciprocal_process_chain_candidate_id": chain_id,
        "anchor_action_family_counts": {"PASS": 2, "PROGRESSION": 1},
        "response_action_family_counts": {"RECOVERY": 1},
        "anchor_episode_candidate_id": anchor_episode,
        "response_episode_candidate_id": response_episode,
        "counter_response_episode_candidate_id": counter_episode,
        "response_consequence_candidate_counts": {response_consequence: 1},
        "counter_response_consequence_candidate_counts": (
            {counter_consequence: 1} if counter_consequence else {}
        ),
        "counter_response_visible": counter_visible,
    }


def _payload(*rows: dict) -> dict:
    return {
        "status": "PASS",
        "reciprocal_process_chain_candidates": list(rows),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_same_process_multi_episode_and_outcome_variation_are_visible_candidates():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2"),
            _chain(
                "r2",
                anchor_episode="e3",
                response_episode="e4",
                response_consequence="LOSS_VISIBLE",
            ),
        )
    )

    assert result["process_variant_profile_status"] == "PASS"
    assert result["process_variant_profile_count"] == 1
    assert result["repeated_process_variant_profile_count"] == 1
    assert result["multi_episode_process_variant_profile_count"] == 1
    assert result["outcome_variation_profile_count"] == 1

    profile = result["process_variant_profiles"][0]
    assert profile["visible_repeat_count_candidate"] == 2
    assert profile["unique_episode_scope_count_candidate"] == 2
    assert profile["trace_variant_frequency_candidate"] == 1.0
    assert profile["repeat_scope_state_candidate"] == "MULTI_EPISODE_SCOPE_REPEAT_CANDIDATE"
    assert profile["visible_outcome_variation_state_candidate"] == "MULTIPLE_VISIBLE_OUTCOME_SIGNATURES_CANDIDATE"
    assert profile["repeat_candidate_is_recurrence_truth"] is False
    assert profile["multi_episode_spread_is_stable_tendency_truth"] is False
    assert profile["outcome_variation_is_tactical_flexibility_truth"] is False
    assert profile["independent_evidence_vote"] is False


def test_repeat_confined_to_one_episode_scope_surfaces_segment_only_risk():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2"),
            _chain("r2", anchor_episode="e1", response_episode="e2"),
        )
    )
    profile = result["process_variant_profiles"][0]

    assert profile["repeat_scope_state_candidate"] == "SINGLE_EPISODE_SCOPE_REPEAT_CANDIDATE"
    assert profile["segment_only_risk_candidate"] is True
    assert profile["multi_episode_spread_visible_candidate"] is False
    assert result["single_episode_repeat_risk_profile_count"] == 1


def test_missing_episode_binding_does_not_get_promoted_to_multi_episode_repeat():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2"),
            _chain("r2", anchor_episode=None, response_episode="e4"),
        )
    )
    profile = result["process_variant_profiles"][0]

    assert profile["repeat_scope_state_candidate"] == (
        "REPEATED_VISIBLE_PROCESS_INCOMPLETE_EPISODE_BINDING_REVIEW_REQUIRED"
    )
    assert profile["incomplete_episode_binding_count"] == 1
    assert profile["segment_only_risk_candidate"] is False
    assert profile["multi_episode_spread_visible_candidate"] is False
    assert result["incomplete_episode_binding_profile_count"] == 1


def test_counter_response_requires_episode_binding_when_visible():
    result = build_process_variant_profiles(
        _payload(
            _chain(
                "r1",
                anchor_episode="e1",
                response_episode="e2",
                counter_visible=True,
                counter_episode=None,
                counter_consequence="SHOT_VISIBLE",
            ),
            _chain(
                "r2",
                anchor_episode="e3",
                response_episode="e4",
                counter_visible=True,
                counter_episode="e5",
                counter_consequence="SHOT_VISIBLE",
            ),
        )
    )
    profile = result["process_variant_profiles"][0]
    assert profile["incomplete_episode_binding_count"] == 1
    assert "INCOMPLETE_EPISODE_BINDING" in profile["repeat_scope_state_candidate"]


def test_single_instance_is_not_recurrence():
    result = build_process_variant_profiles(
        _payload(_chain("r1", anchor_episode="e1", response_episode="e2"))
    )
    profile = result["process_variant_profiles"][0]
    assert profile["repeat_scope_state_candidate"] == "SINGLE_INSTANCE_NOT_RECURRENCE"
    assert profile["segment_only_risk_candidate"] is False
    assert profile["repeat_candidate_is_recurrence_truth"] is False


def test_profile_fail_closes_with_upstream_fail_closed():
    result = build_process_variant_profiles(
        {
            "status": "FAIL_CLOSED",
            "reciprocal_process_chain_candidates": [],
        }
    )
    assert result["process_variant_profile_status"] == "FAIL_CLOSED"
    assert result["process_variant_profiles"] == []
    assert result["production_release"] is False


def test_output_writer_keeps_claim_locks_and_direct_root(tmp_path: Path):
    payload = build_process_variant_profiles(
        _payload(_chain("r1", anchor_episode="e1", response_episode="e2"))
    )
    paths = write_outputs(payload, tmp_path)
    assert paths["json"].is_file()
    assert paths["summary"].is_file()
    assert paths["analyst"].is_file()
    text = paths["summary"].read_text(encoding="utf-8")
    assert "recurrence_truth=false" in text
    assert "tactical_truth=false" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_nested_phone_output_directory_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs({}, Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak():
    module_root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(module_root.glob("process_variant_profile*.py"))
    ).casefold()
    forbidden = (
        "genclerbirligi",
        "fenerbahce",
        "15.08.2026",
        "samsunspor",
        "galatasaray",
        "besiktas",
    )
    assert not any(token in text for token in forbidden)
