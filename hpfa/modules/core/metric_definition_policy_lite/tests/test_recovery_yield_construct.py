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


def episode_context(
    t: dict,
    *,
    episode_id: str | None = "ep_1",
    binding_state: str = "SINGLE_EPISODE_NAVIGATION_ASSOCIATION",
    phases: list[str] | None = None,
    processes: dict[str, int] | None = None,
) -> dict:
    return {
        "episode_consequence_candidate_id": "ec_" + t["trackable_action_trace_candidate_id"],
        "trackable_action_consequence_candidate_id": "c_" + t["trackable_action_trace_candidate_id"],
        "anchor_trackable_action_trace_candidate_id": t["trackable_action_trace_candidate_id"],
        "episode_candidate_id": episode_id,
        "episode_binding_state": binding_state,
        "phase_activity_labels": phases or [],
        "process_family_annotation_counts": processes or {},
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


def build(
    traces: list[dict],
    consequences: list[dict],
    episode_rows: list[dict] | None = None,
    *,
    episode_overrides: dict | None = None,
) -> dict:
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
    episode_payload = None
    if episode_rows is not None:
        episode_payload = {
            "module_id": "episode_consequence_projection_v1",
            "episode_consequence_candidates": episode_rows,
            "episode_consequence_candidate_count": len(episode_rows),
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
        episode_payload.update(episode_overrides or {})
    return build_recovery_yield_construct(trace_payload, consequence_payload, guard(), episode_payload)


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


def test_bound_episode_context_conditions_recovery_profiles_without_truth_inflation() -> None:
    a = trace("a", actor="actor_a")
    b = trace("b", family="INTERCEPTION", actor="actor_b")
    result = build(
        [a, b],
        [
            consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"),
            consequence(b, "OPPONENT_HANDOVER_CANDIDATE"),
        ],
        [
            episode_context(a, episode_id="ep_a", phases=["TRANSITION_ACTIVITY"], processes={"COUNTERATTACK": 1}),
            episode_context(b, episode_id="ep_b", phases=["SETTLED_RECOVERY_ACTIVITY"], processes={"POSITIONAL_ATTACK": 2}),
        ],
    )
    row = result["construct_candidate"]
    assert row["episode_context_conditioning_supplied"] is True
    assert row["episode_context_bound_recovery_trace_candidate_count"] == 2
    assert row["episode_context_binding_coverage_rate_candidate"] == 1.0
    phase = {p["phase_activity_label_candidate"]: p for p in row["phase_activity_context_recovery_yield_profile_candidates"]}
    process = {p["process_family_annotation_candidate"]: p for p in row["process_family_context_recovery_yield_profile_candidates"]}
    assert phase["TRANSITION_ACTIVITY"]["visible_same_team_yield_candidate_count"] == 1
    assert phase["SETTLED_RECOVERY_ACTIVITY"]["visible_adverse_post_recovery_handover_candidate_count"] == 1
    assert process["COUNTERATTACK"]["visible_same_team_yield_candidate_count"] == 1
    assert process["POSITIONAL_ATTACK"]["visible_adverse_post_recovery_handover_candidate_count"] == 1
    assert all(p["context_profile_is_phase_truth"] is False for p in phase.values())
    assert all(p["context_profile_is_tactical_plan_truth"] is False for p in process.values())
    assert row["context_annotation_is_recovery_cause_truth"] is False
    assert row["episode_binding_is_possession_truth"] is False
    assert row["episode_binding_is_sequence_truth"] is False


def test_unbound_episode_context_is_review_not_counterevidence() -> None:
    a = trace("a")
    result = build(
        [a],
        [consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE")],
        [episode_context(a, episode_id=None, binding_state="UNBOUND_REVIEW_REQUIRED", phases=["TRANSITION_ACTIVITY"])],
    )
    row = result["construct_candidate"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["episode_context_bound_recovery_trace_candidate_count"] == 0
    assert row["episode_context_unbound_recovery_trace_candidate_count"] == 1
    assert row["visible_same_team_yield_candidate_count"] == 1
    assert row["counterevidence_consequence_candidate_refs"] == []
    assert row["missing_episode_context_is_counterevidence"] is False
    assert "recovery_episode_context_coverage_incomplete" in result["review_hits"]


def test_overlapping_context_labels_are_marginal_not_additive_denominators() -> None:
    a = trace("a")
    result = build(
        [a],
        [consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE")],
        [episode_context(a, phases=["RECOVERY_ACTIVITY", "TRANSITION_ACTIVITY"], processes={"COUNTERATTACK": 1, "PRESSING": 1})],
    )
    row = result["construct_candidate"]
    assert row["eligible_recovery_trace_candidate_count"] == 1
    assert sum(p["eligible_recovery_trace_candidate_count"] for p in row["phase_activity_context_recovery_yield_profile_candidates"]) == 2
    assert sum(p["eligible_recovery_trace_candidate_count"] for p in row["process_family_context_recovery_yield_profile_candidates"]) == 2
    assert row["context_profile_denominators_are_marginal_not_additive"] is True
    assert all(p["context_profile_denominator_is_additive_across_labels"] is False for p in row["phase_activity_context_recovery_yield_profile_candidates"])


def test_episode_context_upstream_truth_claim_fails_closed() -> None:
    a = trace("a")
    result = build(
        [a],
        [consequence(a, "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE")],
        [episode_context(a)],
        episode_overrides={"canonical_event_count": 1},
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["construct_candidate"] is None
    assert "episode_consequence_canonical_event_count_claimed" in result["hard_block_hits"]


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
    assert result["phase_truth"] is False
    assert result["tactical_plan_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak() -> None:
    rendered = str(build([], []))
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in rendered
