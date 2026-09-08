from pathlib import Path

from hpfa.modules.core.analyst_episode_locator_lite.src.process_participation_projection import (
    build_process_participation_projection,
)

BINDING = "msb_" + "a" * 24


def evidence(label="Involvement in positional attacks with shots", rule="plvs_v2_involvement_in_positional_attacks_with_shots"):
    atom = {
        "evidence_atom_id": "ea_abc",
        "row_nucleus_candidate_id": "rn_abc",
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "atom_class": "PARTICIPATION_INTERVAL_ATOM",
        "atom_status": "PASS",
        "semantic_role_candidate": "PARTICIPATION_INTERVAL",
        "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "semantic_rule_id": rule,
        "context_candidate": "POSITIONAL_ATTACK_CANDIDATE",
        "raw_label": label,
        "period_candidate": "1",
        "start_candidate": "100.0",
        "end_candidate": "112.0",
        "reflection_dependency_state": "DEPENDENT_SERIALIZATION_REFLECTION",
    }
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": [atom],
        "evidence_atom_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def identity(state="ACTOR_IDENTITY_CANDIDATE_BOUND"):
    return {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "identity_bindings": [{
            "evidence_atom_id": "ea_abc",
            "decision_state": state,
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "actor_a",
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def episode():
    return {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "episode_candidates": [{
            "episode_candidate_id": "ep_a",
            "row_nucleus_refs": ["rn_abc"],
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_participation_annotation_becomes_process_intelligence_not_action_truth():
    result = build_process_participation_projection(evidence(), identity(), episode())
    assert result["status"] == "PASS"
    row = result["process_participation_candidates"][0]
    assert row["process_family_candidate"] == "POSITIONAL_ATTACK_CANDIDATE"
    assert row["shot_present_annotation_candidate"] is True
    assert row["actor_identity_candidate_id"] == "actor_a"
    assert row["episode_candidate_id"] == "ep_a"
    assert row["process_participation_is_action_truth"] is False
    assert result["annotation_count_is_action_count"] is False


def test_process_participation_does_not_become_independent_vote():
    result = build_process_participation_projection(evidence(), identity(), episode())
    row = result["process_participation_candidates"][0]
    assert row["reflection_dependency_state"] == "DEPENDENT_SERIALIZATION_REFLECTION"
    assert row["independent_support_vote_count"] == 0
    assert result["reflection_adds_independent_vote"] is False


def test_provider_process_annotation_is_not_tactical_plan_or_off_ball_role():
    result = build_process_participation_projection(evidence(), identity(), episode())
    row = result["process_participation_candidates"][0]
    assert row["process_annotation_is_tactical_plan_truth"] is False
    assert row["process_annotation_is_coach_intention_truth"] is False
    assert row["process_annotation_is_off_ball_role_truth"] is False


def test_participation_requires_actor_identity_binding():
    result = build_process_participation_projection(evidence(), identity("ACTOR_CANDIDATE_MISSING"), episode())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["process_participation_candidate_count"] == 0


def test_semantic_rule_lineage_mismatch_fails_closed():
    result = build_process_participation_projection(
        evidence(rule="plvs_v2_wrong_rule"), identity(), episode()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any("process_semantic_rule_lineage_mismatch" in hit for hit in result["hard_block_hits"])


def test_missing_episode_binding_is_review_not_fabricated():
    ep = episode()
    ep["episode_candidates"][0]["row_nucleus_refs"] = []
    result = build_process_participation_projection(evidence(), identity(), ep)
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["process_participation_candidates"][0]
    assert row["episode_candidate_id"] is None


def test_absence_is_not_counterevidence():
    result = build_process_participation_projection(evidence(), identity(), episode())
    assert result["absence_is_counterevidence"] is False


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/analyst_episode_locator_lite/src/process_participation_projection.py"
    ).read_text(encoding="utf-8")
    forbidden = ("AS Roma", "Atalanta", "Genclerbirligi", "Fenerbahce", "05.09.2026")
    assert not any(token in source for token in forbidden)
