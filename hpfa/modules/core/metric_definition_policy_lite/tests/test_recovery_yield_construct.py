from hpfa.modules.core.metric_definition_policy_lite.src.recovery_yield_construct import build_recovery_yield_construct

BINDING = "msb_" + "r" * 24


def trace(trace_id: str, *, family: str = "RECOVERY", team: str = "team_a", actor: str = "actor_a") -> dict:
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
            "denominator_set_id", "observation_window", "entity_scope", "team_scope",
            "period_scope", "context_policy_id", "source_surface_roles",
            "required_event_families", "construct_target", "dependency_group",
        ],
        "target_construct_families": ["RECOVERY_YIELD"],
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
    return build_recovery_yield_construct(trace_payload, consequence_payload, guard())


def test_recovery_denominator_uses_recovery_and_interception_only() -> None:
    a = trace("a", family="RECOVERY")
    b = trace("b", family="INTERCEPTION", actor="actor_b")
    c = trace("c", family="PASS", actor="actor_c")
    result = build([a, b, c], [
        consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
        consequence(c, "SAME_TEAM_CONTINUATION_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["eligible_recovery_trace_candidate_count"] == 2


def test_yield_and_exposure_share_same_evaluable_denominator() -> None:
    a = trace("a")
    b = trace("b", family="INTERCEPTION", actor="actor_b")
    result = build([a, b], [
        consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["evaluable_recovery_consequence_candidate_count"] == 2
    assert row["recovery_yield_rate_among_evaluable_candidate"] == 0.5
    assert row["post_recovery_exposure_rate_among_evaluable_candidate"] == 0.5


def test_missing_follow_up_is_unknown_not_failure() -> None:
    a = trace("a")
    result = build([a], [])
    row = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["unresolved_or_missing_consequence_candidate_count"] == 1
    assert row["counterevidence_consequence_candidate_refs"] == []
    assert row["missing_consequence_is_counterevidence"] is False


def test_entity_profiles_reconcile_to_recovery_denominator() -> None:
    a = trace("a", team="team_a", actor="actor_a")
    b = trace("b", family="INTERCEPTION", team="team_b", actor="actor_b")
    result = build([a, b], [
        consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"),
        consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
    ])
    row = result["construct_candidate"]
    assert row["team_profile_denominator_reconciles_to_construct"] is True
    assert row["actor_profile_denominator_reconciles_to_construct"] is True


def test_claim_locks_remain_closed() -> None:
    a = trace("a")
    result = build([a], [consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE")])
    row = result["construct_candidate"]
    assert row["recovery_yield_score_emitted"] is False
    assert row["construct_validity_truth"] is False
    assert row["recovery_quality_truth"] is False
    assert row["possession_gain_truth"] is False
    assert row["causal_truth"] is False
    assert row["professional_finding_emitted"] is False
    assert row["claim_output_allowed"] is False
    assert row["same_provider_reflection_adds_independent_vote"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak() -> None:
    rendered = str(build([], []))
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in rendered
