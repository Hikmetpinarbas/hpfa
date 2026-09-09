from hpfa.modules.core.metric_definition_policy_lite.src.ball_security_construct import (
    build_ball_security_construct,
)

BINDING = "msb_" + "b" * 24


def trace(trace_id: str, *, family: str = "PASS", team: str = "team_a", actor: str = "actor_a") -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "10",
        "end_candidate": "10.5",
        "action_family_candidates": [family],
        "canonical_event_count": "UNKNOWN",
    }


def consequence(t: dict, primary: str, *, status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict:
    return {
        "trackable_action_consequence_candidate_id": "c_" + t["trackable_action_trace_candidate_id"],
        "anchor_trackable_action_trace_candidate_id": t["trackable_action_trace_candidate_id"],
        "match_surface_binding_id": BINDING,
        "record_status": status,
        "primary_consequence_candidate": primary,
        "canonical_event_count": "UNKNOWN",
    }


def guard() -> dict:
    return {
        "module_id": "construct_context_guard_v1",
        "observation_model": "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1",
        "required_comparability_dimensions": [
            "denominator_set_id",
            "observation_window",
            "entity_scope",
            "team_scope",
            "period_scope",
            "context_policy_id",
            "source_surface_roles",
            "required_event_families",
            "construct_target",
            "dependency_group",
        ],
        "target_construct_families": ["BALL_SECURITY"],
    }


def build(traces: list[dict], consequences: list[dict]) -> dict:
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": len(traces),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    consequence_payload = {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": consequences,
        "trackable_action_consequence_candidate_count": len(consequences),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return build_ball_security_construct(trace_payload, consequence_payload, guard())


def test_ball_use_denominator_excludes_explicit_turnover_trace() -> None:
    a = trace("a", family="PASS")
    b = trace("b", family="CARRY", actor="actor_b")
    loss = trace("loss", family="TURNOVER", actor="actor_b")
    result = build([
        a, b, loss
    ], [
        consequence(a, "SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
        consequence(loss, "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["eligible_ball_use_trace_candidate_count"] == 2
    assert row["explicit_turnover_trace_candidate_count_outside_denominator"] == 1
    assert row["explicit_turnover_is_denominator_member"] is False


def test_retention_and_loss_exposure_share_same_evaluable_denominator() -> None:
    a = trace("a", family="PASS")
    b = trace("b", family="DRIBBLE", actor="actor_b")
    result = build([
        a, b
    ], [
        consequence(a, "SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["evaluable_ball_security_consequence_candidate_count"] == 2
    assert row["retention_rate_among_evaluable_candidate"] == 0.5
    assert row["loss_exposure_rate_among_evaluable_candidate"] == 0.5


def test_missing_follow_up_is_unknown_not_counterevidence() -> None:
    a = trace("a")
    result = build([a], [])
    row = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["unresolved_or_missing_consequence_candidate_count"] == 1
    assert row["counterevidence_consequence_candidate_refs"] == []
    assert row["missing_consequence_is_counterevidence"] is False


def test_entity_profiles_reconcile_to_construct_denominator() -> None:
    a = trace("a", team="team_a", actor="actor_a")
    b = trace("b", family="CARRY", team="team_b", actor="actor_b")
    result = build([
        a, b
    ], [
        consequence(a, "SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["team_profile_denominator_reconciles_to_construct"] is True
    assert row["actor_profile_denominator_reconciles_to_construct"] is True


def test_claim_locks_remain_closed() -> None:
    a = trace("a")
    result = build([a], [consequence(a, "SAME_TEAM_CONTINUATION_CANDIDATE")])
    row = result["construct_candidate"]
    assert row["ball_security_score_emitted"] is False
    assert row["construct_validity_truth"] is False
    assert row["player_quality_truth"] is False
    assert row["causal_truth"] is False
    assert row["professional_finding_emitted"] is False
    assert row["claim_output_allowed"] is False
    assert row["same_provider_reflection_adds_independent_vote"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak() -> None:
    result = build([], [])
    rendered = str(result)
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in rendered
