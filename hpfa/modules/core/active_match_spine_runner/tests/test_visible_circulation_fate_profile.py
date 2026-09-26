from hpfa.modules.core.active_match_spine_runner.src.visible_circulation_fate_profile import (
    CLAIM_CEILING,
    build_visible_circulation_fate_profile,
)


def _sig(team, family, *, passes=0, carries=0, shot=False, loss=False, recovery=False, sid="s"):
    return {
        "process_development_signature_id": sid,
        "team_identity_candidate_id": team,
        "process_family_candidate": family,
        "period_candidate": "1",
        "process_start_candidate": 100.0,
        "process_end_candidate": 110.0,
        "action_family_layer_counts": {"PASS": passes, "CARRY": carries},
        "shot_present_annotation_candidate": shot,
        "visible_loss_transition_candidate_present": loss,
        "visible_recovery_transition_candidate_present": recovery,
    }


def test_visible_circulation_fate_profile_counts_visible_outcomes():
    payload = [
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=4, shot=True, sid="s1"),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=3, loss=True, sid="s2"),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=2, recovery=True, sid="s3"),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=5, sid="s4"),
    ]
    result = build_visible_circulation_fate_profile(payload)

    assert result["status"] == "PASS"
    assert result["eligible_circulation_process_n"] == 4
    assert result["visible_fate_counts"] == {
        "LOSS_LINKED_VISIBLE": 1,
        "OTHER_VISIBLE_OR_UNRESOLVED": 1,
        "RECOVERY_LINKED_VISIBLE": 1,
        "SHOT_LINKED_VISIBLE": 1,
    }
    assert result["claim_ceiling"] == CLAIM_CEILING
    assert result["sterile_productive_binary_emitted"] is False
    assert result["circulation_fate_is_tactical_quality_truth"] is False
    assert result["circulation_fate_is_causal_truth"] is False


def test_shot_and_loss_remain_joint_visible_context():
    result = build_visible_circulation_fate_profile([
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=3, shot=True, loss=True)
    ])

    assert result["rows"][0]["visible_fate_candidate"] == "SHOT_AND_LOSS_VISIBLE"


def test_process_without_pass_or_carry_is_not_in_denominator():
    result = build_visible_circulation_fate_profile([
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=0, carries=0, shot=True)
    ])

    assert result["status"] == "NOT_AVAILABLE"
    assert result["eligible_circulation_process_n"] == 0


def test_team_and_process_family_denominators_stay_separate():
    result = build_visible_circulation_fate_profile([
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", passes=2, shot=True, sid="a1"),
        _sig("A", "COUNTERATTACK_CANDIDATE", carries=2, loss=True, sid="a2"),
        _sig("B", "POSITIONAL_ATTACK_CANDIDATE", passes=2, sid="b1"),
    ])

    assert len(result["profiles"]) == 3
    assert all(row["eligible_circulation_process_n"] == 1 for row in result["profiles"])
    assert all(row["sterile_productive_binary_emitted"] is False for row in result["profiles"])
