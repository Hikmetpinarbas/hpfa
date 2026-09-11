from pathlib import Path

import pytest

from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile import (
    MODULE_ID,
    build_process_variant_profiles,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src.process_variant_profile_outputs import (
    ANALYST_TXT,
    OUTPUT_JSON,
    OUTPUT_TXT,
    clear_outputs,
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


def _payload(*rows: dict, status: str = "PASS") -> dict:
    return {
        "status": status,
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

    assert result["module_id"] == MODULE_ID
    assert result["process_variant_profile_status"] == "PASS"
    assert result["process_variant_profile_count"] == 1
    assert result["repeated_process_variant_profile_count"] == 1
    assert result["multi_episode_process_variant_profile_count"] == 1
    assert result["outcome_variation_profile_count"] == 1
    assert result["process_resolution_variation_profile_count"] == 1

    profile = result["process_variant_profiles"][0]
    assert profile["visible_repeat_count_candidate"] == 2
    assert profile["unique_episode_scope_count_candidate"] == 2
    assert profile["trace_variant_frequency_candidate"] == 1.0
    assert profile["repeat_scope_state_candidate"] == "MULTI_EPISODE_SCOPE_REPEAT_CANDIDATE"
    assert profile["visible_outcome_variation_state_candidate"] == "MULTIPLE_VISIBLE_OUTCOME_SIGNATURES_CANDIDATE"
    classes = {
        row["process_resolution_class_candidate"]
        for row in profile["process_resolution_variant_profile_candidate"]
    }
    assert classes == {
        "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT",
        "ADVERSE_HANDOVER_VISIBLE_VARIANT",
    }
    assert profile["comparable_visible_resolution_count_candidate"] == 2
    assert profile["dominant_process_resolution_class_candidate"] is None
    assert profile["dominant_resolution_state_candidate"] == "NO_UNIQUE_MATCH_LOCAL_MODAL_RESOLUTION"
    assert profile["repeat_candidate_is_recurrence_truth"] is False
    assert profile["multi_episode_spread_is_stable_tendency_truth"] is False
    assert profile["outcome_variation_is_tactical_flexibility_truth"] is False
    assert profile["independent_evidence_vote"] is False


def test_unique_match_local_modal_resolution_and_deviant_variant_are_exposed():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2", response_consequence="SAME_TEAM_CONTINUATION_CANDIDATE"),
            _chain("r2", anchor_episode="e3", response_episode="e4", response_consequence="SHOT_FOLLOW_UP_CANDIDATE"),
            _chain("r3", anchor_episode="e5", response_episode="e6", response_consequence="OPPONENT_HANDOVER_CANDIDATE"),
        )
    )
    profile = result["process_variant_profiles"][0]
    assert profile["dominant_process_resolution_class_candidate"] == "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT"
    assert profile["deviant_process_resolution_classes_candidate"] == ["ADVERSE_HANDOVER_VISIBLE_VARIANT"]
    assert profile["dominant_resolution_state_candidate"] == "UNIQUE_MATCH_LOCAL_MODAL_RESOLUTION_CANDIDATE"
    assert result["unique_modal_resolution_profile_count"] == 1


def test_right_censoring_is_reported_but_excluded_from_comparable_resolution_denominator():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2", response_consequence="SAME_TEAM_CONTINUATION_CANDIDATE"),
            _chain("r2", anchor_episode="e3", response_episode="e4", response_consequence="RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE"),
        )
    )
    profile = result["process_variant_profiles"][0]
    assert profile["right_censored_resolution_count_candidate"] == 1
    assert profile["comparable_visible_resolution_count_candidate"] == 1
    censored = next(
        row for row in profile["process_resolution_variant_profile_candidate"]
        if row["process_resolution_class_candidate"] == "RIGHT_CENSORED_OBSERVATION_VARIANT"
    )
    assert censored["within_comparable_resolution_share_candidate"] is None
    assert censored["comparable_for_modal_deviation_candidate"] is False


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
    assert result["process_variant_profile_status"] == "REVIEW_REQUIRED"


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
    assert result["process_variant_profile_status"] == "REVIEW_REQUIRED"


def test_upstream_review_required_cannot_be_promoted_to_pass():
    result = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2"),
            _chain("r2", anchor_episode="e3", response_episode="e4"),
            status="REVIEW_REQUIRED",
        )
    )
    assert result["module_id"] == MODULE_ID
    assert result["upstream_reciprocal_status"] == "REVIEW_REQUIRED"
    assert result["process_variant_profile_status"] == "REVIEW_REQUIRED"


def test_single_instance_is_not_recurrence():
    result = build_process_variant_profiles(
        _payload(_chain("r1", anchor_episode="e1", response_episode="e2"))
    )
    profile = result["process_variant_profiles"][0]
    assert profile["repeat_scope_state_candidate"] == "SINGLE_INSTANCE_NOT_RECURRENCE"
    assert profile["segment_only_risk_candidate"] is False
    assert profile["repeat_candidate_is_recurrence_truth"] is False


def test_profile_fail_closes_with_upstream_fail_closed_and_keeps_module_identity():
    result = build_process_variant_profiles(
        {
            "status": "FAIL_CLOSED",
            "reciprocal_process_chain_candidates": [],
        }
    )
    assert result["module_id"] == MODULE_ID
    assert result["process_variant_profile_status"] == "FAIL_CLOSED"
    assert result["upstream_reciprocal_status"] == "FAIL_CLOSED"
    assert result["process_variant_profiles"] == []
    assert result["production_release"] is False


def test_output_writer_exposes_resolution_intelligence_and_keeps_claim_locks(tmp_path: Path):
    payload = build_process_variant_profiles(
        _payload(
            _chain("r1", anchor_episode="e1", response_episode="e2", response_consequence="SAME_TEAM_CONTINUATION_CANDIDATE"),
            _chain("r2", anchor_episode="e3", response_episode="e4", response_consequence="OPPONENT_HANDOVER_CANDIDATE"),
        )
    )
    paths = write_outputs(payload, tmp_path)
    assert paths["json"].is_file()
    assert paths["summary"].is_file()
    assert paths["analyst"].is_file()
    summary = paths["summary"].read_text(encoding="utf-8")
    analyst = paths["analyst"].read_text(encoding="utf-8")
    assert f"module_id={MODULE_ID}" in summary
    assert "process_resolution_variation_profile_count=1" in summary
    assert "recurrence_truth=false" in summary
    assert "canonical_event_count=UNKNOWN" in summary
    assert "true_action_count=UNKNOWN" in summary
    assert "production_release=false" in summary
    assert "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT" in analyst
    assert "ADVERSE_HANDOVER_VISIBLE_VARIANT" in analyst
    assert "modal_resolution=" in analyst


def test_clear_outputs_removes_only_owned_stale_variant_artifacts(tmp_path: Path):
    owned = [tmp_path / OUTPUT_JSON, tmp_path / OUTPUT_TXT, tmp_path / ANALYST_TXT]
    unrelated = tmp_path / "unrelated_current_artifact.json"
    for path in owned:
        path.write_text("stale", encoding="utf-8")
    unrelated.write_text("keep", encoding="utf-8")

    removed = clear_outputs(tmp_path)

    assert {path.name for path in removed} == {OUTPUT_JSON, OUTPUT_TXT, ANALYST_TXT}
    assert all(not path.exists() for path in owned)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_nested_phone_output_directory_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs({}, Path("/sdcard/Download/HPFA/nested"))
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        clear_outputs(Path("/sdcard/Download/HPFA/nested"))


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