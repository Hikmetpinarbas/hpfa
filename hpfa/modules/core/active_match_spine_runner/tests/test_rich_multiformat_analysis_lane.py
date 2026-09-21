from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import run_intelligence_chain
from rich_multiformat_analysis_lane import _construct_c01, _construct_c02, _construct_c03, _construct_c04, _entity_views, _phase_state_candidates, _football_ontology_contract, _game_state_context, _recovery_next_process_context, _goalkeeper_restart_consequence_context, _player_function_profiles
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet
from hpfa.modules.core.xlsx_entity_metric_row_projection_lite.src.xlsx_entity_metric_row_projection import _project_sheet


class Cell:
    def __init__(self, value=None, data_type="n", number_format=""):
        self.value = value
        self.data_type = data_type
        self.number_format = number_format


class Sheet:
    def __init__(self, rows):
        self.rows = rows
        self.max_row = len(rows)
        self.max_column = max(len(row) for row in rows)

    def cell(self, row, column):
        try:
            return self.rows[row - 1][column - 1]
        except IndexError:
            return Cell(None)


def _audit():
    return {
        "sheet_name": "Players",
        "sheet_state": "visible",
        "header_row_index": 1,
        "raw_columns": ["Player", "Team", "Progressive passes", "Shots"],
        "column_profiles": [
            {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player"},
            {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team"},
            {"raw_column": "Progressive passes", "normalized_column": "progressive_passes", "identity_role_candidate": None, "percent_header_candidate": False},
            {"raw_column": "Shots", "normalized_column": "shots", "identity_role_candidate": None, "percent_header_candidate": False},
        ],
    }







def test_player_function_profiles_keep_dimensions_separate_without_quality_score():
    bindings = {
        "actor_1": {
            "actor_label": "Player 1",
            "team_identity_candidate_id": "team_1",
            "team_label": "Team 1",
            "xlsx_row_projection_id": "xrp_1",
            "xlsx_row": {
                "row_projection_id": "xrp_1",
                "metric_values": {
                    "final_third_entries": {
                        "raw_metric_label": "Final third entries",
                        "raw_value": 5,
                        "value_status": "OBSERVED",
                    },
                    "xa_expected_assists": {
                        "raw_metric_label": "xA (expected assists)",
                        "raw_value": 0.4,
                        "value_status": "OBSERVED",
                    },
                    "shots": {
                        "raw_metric_label": "Shots",
                        "raw_value": 3,
                        "value_status": "OBSERVED",
                    },
                    "ball_recoveries": {
                        "raw_metric_label": "Ball recoveries",
                        "raw_value": 7,
                        "value_status": "OBSERVED",
                    },
                },
            },
        }
    }
    process = [{
        "semantic_role": "PARTICIPATION_INTERVAL",
        "actor_identity_candidate_id": "actor_1",
        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
        "shot_present_annotation_candidate": True,
    }]
    profiles = _player_function_profiles(bindings, process)
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile["process_participation_counts"] == {"POSITIONAL_ATTACK_CANDIDATE": 1}
    assert profile["shot_ending_process_participation_counts"] == {"POSITIONAL_ATTACK_CANDIDATE": 1}
    assert profile["dimension_metric_counts"]["ACCESS"] == 1
    assert profile["dimension_metric_counts"]["CREATION"] == 1
    assert profile["dimension_metric_counts"]["TERMINAL"] == 1
    assert profile["dimension_metric_counts"]["RECOVERY_LOSS"] == 1
    assert profile["profile_is_quality_score"] is False
    assert profile["profile_is_tactical_role_truth"] is False
    assert profile["xlsx_aggregate_is_action_identity"] is False


def test_goalkeeper_restart_consequence_context_binds_provider_restart_to_visible_consequence():
    action = {
        "action_occurrence_candidates": [{
            "action_occurrence_candidate_id": "gk_1",
            "actor_identity_candidate_id": "keeper_1",
            "team_identity_candidate_id": "team_a",
            "attributes": {
                "restart_type_candidate": "GOAL_KICK",
                "provider_distance_bucket_candidate": "LONG",
                "pass_outcome_candidate": "SUCCESS",
            },
        }]
    }
    consequence = {
        "occurrence_consequence_projections": [{
            "action_occurrence_candidate_id": "gk_1",
            "followup_observation_status": "VISIBLE_FOLLOW_UP",
            "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
            "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
            "admitted_followup_horizon_sensitive": False,
            "record_status": "PASS",
        }]
    }
    result = _goalkeeper_restart_consequence_context(action, consequence)
    assert result["status"] == "PASS"
    assert result["provider_distance_bucket_counts"] == {"LONG": 1}
    assert result["pass_outcome_counts"] == {"SUCCESS": 1}
    assert result["primary_consequence_counts"] == {"SAME_TEAM_CONTINUATION_CANDIDATE": 1}
    row = result["rows"][0]
    assert row["provider_distance_bucket_is_tactical_strategy_truth"] is False
    assert row["same_team_continuation_is_possession_truth"] is False
    assert row["creates_independent_support"] is False


def test_goalkeeper_restart_consequence_context_is_not_available_without_goal_kick_occurrence():
    result = _goalkeeper_restart_consequence_context(
        {"action_occurrence_candidates": []},
        {"occurrence_consequence_projections": []},
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["goalkeeper_restart_context_row_count"] == 0


def test_recovery_next_process_context_binds_first_followup_to_visible_process_family():
    consequence = {
        "occurrence_consequence_projections": [{
            "action_occurrence_candidate_id": "occ_recovery_1",
            "recovery_first_admitted_followup_applicable": True,
            "recovery_first_admitted_followup_state": "CONTINUATION_ADMITTED",
            "recovery_first_admitted_followup_start_candidate": 12.0,
            "recovery_first_admitted_followup_team_identity_candidate_ids": ["team_a"],
            "recovery_first_admitted_followup_action_family_candidates": ["PASS"],
            "recovery_first_admitted_followup_provider_semantic_candidates": [
                "PROVIDER_FORWARD_PASS_VISIBLE_CANDIDATE"
            ],
            "period_candidates": ["1"],
            "team_identity_candidate_ids": ["team_a"],
            "actor_identity_candidate_ids": ["actor_a"],
            "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
            "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
        }]
    }
    process = {
        "process_participation_candidates": [
            {
                "process_participation_candidate_id": "ppc_1",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_b",
                "process_family_candidate": "COUNTERATTACK_CANDIDATE",
                "period_candidate": "1",
                "start_candidate": "10",
                "end_candidate": "20",
            },
            {
                "process_participation_candidate_id": "ppc_2",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_c",
                "process_family_candidate": "COUNTERATTACK_CANDIDATE",
                "period_candidate": "1",
                "start_candidate": "10",
                "end_candidate": "20",
            },
        ]
    }
    result = _recovery_next_process_context(consequence, process)
    assert result["status"] == "PASS"
    assert result["recovery_context_row_count"] == 1
    row = result["rows"][0]
    assert row["next_visible_process_family_candidates"] == ["COUNTERATTACK_CANDIDATE"]
    assert row["next_process_binding_state"] == "SINGLE_VISIBLE_PROCESS_FAMILY_MATCH"
    assert row["creates_independent_support"] is False
    assert row["next_process_is_tactical_plan_truth"] is False


def test_recovery_next_process_context_keeps_no_process_match_explicit():
    consequence = {
        "occurrence_consequence_projections": [{
            "action_occurrence_candidate_id": "occ_recovery_2",
            "recovery_first_admitted_followup_applicable": True,
            "recovery_first_admitted_followup_state": "CONTINUATION_ADMITTED",
            "recovery_first_admitted_followup_start_candidate": 50.0,
            "recovery_first_admitted_followup_team_identity_candidate_ids": ["team_a"],
            "period_candidates": ["1"],
        }]
    }
    result = _recovery_next_process_context(consequence, {"process_participation_candidates": []})
    assert result["rows"][0]["next_process_binding_state"] == "NO_VISIBLE_PROCESS_INTERVAL_MATCH"
    assert result["rows"][0]["next_visible_process_family_candidates"] == []


def test_game_state_context_is_match_agnostic_and_deduplicates_reflected_goals(tmp_path):
    header = "ID;start;end;code;team;action;half;pos_x;pos_y\n"
    rows = [
        "1;10;12;7. Player A (1);Alpha (11);Goals;1;90;34\n",
        "2;40;42;9. Player B (2);Beta (22);Goals;1;92;30\n",
        "3;80;82;4. Player C (3);Alpha (11);Passes accurate;1;50;20\n",
    ]
    (tmp_path / "players.csv").write_text(header + "".join(rows), encoding="utf-8")
    reflected = [
        "1;10;12;Alpha (11) - Team;Alpha (11);Goals;1;90;34\n",
        "2;40;42;Beta (22) - Team;Beta (22);Goals;1;92;30\n",
    ]
    (tmp_path / "reflection.csv").write_text(header + "".join(reflected), encoding="utf-8")

    result = _game_state_context(tmp_path)

    assert result["status"] == "PASS"
    assert result["goal_observation_count"] == 2
    assert result["team_labels"] == ["Alpha (11)", "Beta (22)"]
    assert [row["score_state_candidate"] for row in result["score_state_segments"]] == [
        {"Alpha (11)": 0, "Beta (22)": 0},
        {"Alpha (11)": 1, "Beta (22)": 0},
        {"Alpha (11)": 1, "Beta (22)": 1},
    ]
    assert result["creates_independent_support"] is False
    assert result["game_state_is_tactical_truth"] is False


def test_game_state_context_supports_zero_zero_without_goal_rows(tmp_path):
    (tmp_path / "match.csv").write_text(
        "ID;start;end;code;team;action;half;pos_x;pos_y\n"
        "1;5;7;1. A (1);Alpha;Passes accurate;1;20;20\n"
        "2;90;92;2. B (2);Beta;Lost balls;1;30;30\n",
        encoding="utf-8",
    )
    result = _game_state_context(tmp_path)
    assert result["status"] == "PASS"
    assert result["goal_observation_count"] == 0
    assert result["score_state_segments"][0]["score_state_candidate"] == {"Alpha": 0, "Beta": 0}
    assert result["score_state_segments"][0]["end_second_candidate"] == 90.0


def test_xlsx_row_projection_preserves_identity_metric_alignment_and_zero():
    formula = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(0), Cell(3)],
    ])
    values = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(0), Cell(3)],
    ])
    result = _project_sheet(
        formula,
        values,
        _audit(),
        {"file_id": "file_generic", "relative_path": "players.xlsx", "source_sha256": "abc", "source_role": "PLAYER_SURFACE_CANDIDATE"},
        "msb_generic",
    )
    assert result["status"] == "PASS"
    row = result["rows"][0]
    assert row["identity_candidates"]["player_raw_candidate"] == "P1"
    assert row["identity_candidates"]["team_raw_candidate"] == "T1"
    assert row["metric_values"]["progressive_passes"]["raw_value"] == 0
    assert row["metric_values"]["progressive_passes"]["value_status"] == "OBSERVED"
    assert row["row_projection_is_canonical_event"] is False


def test_xlsx_row_projection_formula_without_cache_is_review_required():
    formula = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell("=1+1", "f"), Cell(3)],
    ])
    values = Sheet([
        [Cell("Player", "s"), Cell("Team", "s"), Cell("Progressive passes", "s"), Cell("Shots", "s")],
        [Cell("P1", "s"), Cell("T1", "s"), Cell(None), Cell(3)],
    ])
    result = _project_sheet(
        formula,
        values,
        _audit(),
        {"file_id": "file_generic", "relative_path": "players.xlsx", "source_sha256": "abc", "source_role": "PLAYER_SURFACE_CANDIDATE"},
        "msb_generic",
    )
    assert result["status"] == "REVIEW_REQUIRED"
    metric = result["rows"][0]["metric_values"]["progressive_passes"]
    assert metric["raw_value"] is None
    assert metric["value_status"] == "NOT_ADMITTED_FORMULA_CACHE_MISSING"


def test_phase_state_candidates_are_explicitly_candidates_not_truth():
    features = {
        "episode_feature_vectors": [{
            "start_second_candidate": 100,
            "end_second_candidate": 160,
            "shot_candidate_count": 2,
            "turnover_candidate_count": 1,
            "recovery_candidate_count": 1,
            "eligible_action_zone_counts": {"FINAL_THIRD": 8},
            "action_family_counts": {"PASS": 20},
        }]
    }
    rows = _phase_state_candidates(features)
    assert rows[0]["labels"] == [
        "TERMINAL_ACTIVITY_CANDIDATE",
        "LOSS_TRANSITION_ACTIVITY_CANDIDATE",
        "RECOVERY_TRANSITION_ACTIVITY_CANDIDATE",
        "ADVANCED_ACCESS_ACTIVITY_CANDIDATE",
        "CIRCULATION_ACTIVITY_CANDIDATE",
    ]
    assert rows[0]["phase_truth"] is False
    assert rows[0]["tactical_truth"] is False


def test_c01_same_scope_aggregate_pair_can_enter_c4_without_fake_action_requirement():
    projection_rows = [{
        "row_projection_id": "xrp_1",
        "source_sha256": "same_provider_sha",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "identity_candidates": {"player_raw_candidate": "P1", "team_raw_candidate": "T1"},
        "metric_values": {
            "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 12, "value_status": "OBSERVED"},
            "shots": {"raw_metric_label": "Shots", "raw_value": 4, "value_status": "OBSERVED"},
        },
    }]
    features = {"episode_feature_vectors": [{"shot_candidate_count": 4}]}
    construct = _construct_c01(projection_rows, features)
    assert construct["status"] == "REVIEW_REQUIRED"
    assert construct["packet_candidate"] is not None
    candidate = construct["packet_candidate"]

    assert candidate["required_lenses"] == ["aggregate"]
    assert candidate["optional_lenses"] == ["action", "outcome", "context", "contradiction"]
    assert candidate["input_features"][0]["lens"] == "action"
    assert all(metric["lens"] == "aggregate" for metric in candidate["input_metrics"])
    assert len({metric["row_projection_id"] for metric in candidate["input_metrics"]}) == 1
    assert candidate["supporting_signals"][0]["relation_type"] == "SUPPORTS"
    assert candidate["supporting_signals"][0]["independent_support_vote"] is False
    assert candidate["supporting_signals"][0]["causal_truth"] is False

    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["packet_family"] == "progression"
    assert packet["independent_support_count"] == 0
    assert packet["nominal_ref_count_is_independent_support_count"] is False
    assert packet["claim_ceiling"] == "composite_candidate_only"

    chain = run_intelligence_chain(packet)
    assert chain["lens"]["lens_requirement_mode"] == "EXPLICIT_ZFGV"
    assert chain["lens"]["required_lenses"] == ["aggregate"]
    assert chain["lens"]["missing_required_lenses"] == []
    assert chain["lens"]["status"] == "SMOKE_PASS"
    assert construct["review_reason"] == "aggregate_pair_scope_aligned_same_provider_support_non_independent"


def test_c01_must_not_pair_progression_from_one_entity_with_terminal_output_from_another():
    projection_rows = [
        {
            "row_projection_id": "xrp_progression_p1",
            "source_sha256": "same_provider_sha",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "P1", "team_raw_candidate": "T1"},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 12, "value_status": "OBSERVED"},
            },
        },
        {
            "row_projection_id": "xrp_terminal_p2",
            "source_sha256": "same_provider_sha",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "P2", "team_raw_candidate": "T1"},
            "metric_values": {
                "shots": {"raw_metric_label": "Shots", "raw_value": 5, "value_status": "OBSERVED"},
            },
        },
    ]
    features = {"episode_feature_vectors": [{"shot_candidate_count": 9}]}
    construct = _construct_c01(projection_rows, features)

    assert construct["packet_candidate"] is None
    assert construct["status"] == "REVIEW_REQUIRED"
    assert construct["review_reason"] == "comparable_aggregate_scope_not_observed"
    assert construct["comparable_scope_pair_count"] == 0


def test_c01_scope_alignment_does_not_promote_same_provider_aggregate_to_independent_support():
    projection_rows = [{
        "row_projection_id": "xrp_2",
        "source_sha256": "same_provider_sha",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "identity_candidates": {"player_raw_candidate": "P2", "team_raw_candidate": "T2"},
        "metric_values": {
            "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 15, "value_status": "OBSERVED"},
            "shots": {"raw_metric_label": "Shots", "raw_value": 5, "value_status": "OBSERVED"},
        },
    }]
    construct = _construct_c01(projection_rows, {"episode_feature_vectors": [{"shot_candidate_count": 5}]})
    packet = build_composite_packet(construct["packet_candidate"])
    chain = run_intelligence_chain(packet)

    assert packet["independent_support_count"] == 0
    assert chain["fusion"]["independent_support_count"] == 0
    assert construct["aggregate_support_is_independent_vote"] is False


def _c02_identity():
    return {
        "module_id": "match_local_identity_candidates_lite_v1",
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_kerem",
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "actor_normalized_key": "kerem_akturkoglu",
                "actor_aliases_raw": ["7. Kerem Akturkoglu (737292)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "actor_identity_candidate_id": "actor_guendouzi",
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "actor_normalized_key": "matteo_guendouzi",
                "actor_aliases_raw": ["6. Matteo Guendouzi (562671)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            },
        ],
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "team_fener",
                "team_normalized_key": "fenerbahce",
                "team_aliases_raw": ["Fenerbahce (27041)"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            }
        ],
    }


def _c02_xlsx_rows():
    return [
        {
            "row_projection_id": "xrp_kerem",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Kerem Akturkoglu", "team_raw_candidate": None},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 3, "value_status": "OBSERVED"},
                "xa": {"raw_metric_label": "xA", "raw_value": 0.85, "value_status": "OBSERVED"},
            },
        },
        {
            "row_projection_id": "xrp_guendouzi",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Matteo Guendouzi", "team_raw_candidate": None},
            "metric_values": {
                "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 11, "value_status": "OBSERVED"},
                "xa": {"raw_metric_label": "xA", "raw_value": 0.37, "value_status": "OBSERVED"},
            },
        },
    ]


def _c02_process_payload():
    rows = []
    # Four positional attacks: two shot-ending. Kerem+Guendouzi together in two, both shot-ending.
    specs = [
        ("10", "20", True, ["actor_kerem", "actor_guendouzi"]),
        ("30", "40", True, ["actor_kerem", "actor_guendouzi"]),
        ("50", "60", False, ["actor_kerem"]),
        ("70", "80", False, ["actor_guendouzi"]),
    ]
    for idx, (start, end, shot, actors) in enumerate(specs, start=1):
        common = {
            "team_identity_candidate_id": "team_fener",
            "process_family_candidate": "POSITIONAL_ATTACKS",
            "period_candidate": "1",
            "start_candidate": start,
            "end_candidate": end,
            "episode_candidate_id": f"ep_{idx}",
            "shot_present_annotation_candidate": shot,
        }
        rows.append({
            **common,
            "process_participation_candidate_id": f"context_{idx}",
            "semantic_role": "CONTEXT_INTERVAL",
            "actor_identity_candidate_id": None,
        })
        for actor in actors:
            rows.append({
                **common,
                "process_participation_candidate_id": f"participant_{idx}_{actor}",
                "semantic_role": "PARTICIPATION_INTERVAL",
                "actor_identity_candidate_id": actor,
            })
    return {
        "module_id": "analyst_episode_process_participation_projection_v1",
        "status": "PASS",
        "process_participation_candidates": rows,
    }


def test_c02_combines_process_participation_outcome_and_xlsx_context():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["process_participation_consumed"] is True
    assert result["xlsx_actor_binding_count"] == 2
    dyad = result["representative_dyad_argument"]
    assert dyad["actor_labels"] == ["Matteo Guendouzi", "Kerem Akturkoglu"] or set(dyad["actor_labels"]) == {"Matteo Guendouzi", "Kerem Akturkoglu"}
    assert dyad["support_n"] == 2
    assert dyad["shot_ending_n"] == 2
    assert dyad["eligible_process_n"] == 4
    assert dyad["baseline_shot_ending_n"] == 2
    assert dyad["conditional_shot_frequency"] == 1.0
    assert dyad["match_local_baseline_shot_frequency"] == 0.5
    assert dyad["match_local_lift"] == 2.0
    assert dyad["xlsx_enriched_actor_count"] == 2
    assert dyad["association_is_causal_player_credit"] is False
    assert dyad["association_is_independent_evidence_vote"] is False


def test_c02_does_not_cross_bind_ambiguous_xlsx_player_rows():
    rows = _c02_xlsx_rows()
    rows.append(dict(rows[0], row_projection_id="xrp_kerem_duplicate"))
    result = _construct_c02(rows, _c02_identity(), _c02_process_payload())

    dyad = result["representative_dyad_argument"]
    assert result["xlsx_actor_binding_count"] == 1
    assert dyad["xlsx_enriched_actor_count"] == 1
    assert any("xlsx_player_row_ambiguous:kerem_akturkoglu" in hit for hit in result["xlsx_binding_review_hits"])


def test_c02_process_association_survives_without_xlsx_enrichment():
    result = _construct_c02([], _c02_identity(), _c02_process_payload())

    dyad = result["representative_dyad_argument"]
    assert result["xlsx_actor_binding_count"] == 0
    assert dyad["support_n"] == 2
    assert dyad["shot_ending_n"] == 2
    assert dyad["xlsx_enriched_actor_count"] == 0
    assert dyad["claim_ceiling"] == "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY"



def test_c02_real_aggregate_role_can_bind_unique_xlsx_player_row():
    rows = _c02_xlsx_rows()
    for row in rows:
        row["source_role"] = "AGGREGATE_OR_TABULAR_SURFACE_CANDIDATE"
    result = _construct_c02(rows, _c02_identity(), _c02_process_payload())
    assert result["xlsx_actor_binding_count"] == 2
    assert result["representative_dyad_argument"]["xlsx_enriched_actor_count"] == 2


def test_c02_shot_specific_context_refines_same_interval_generic_context():
    payload = _c02_process_payload()
    generic = next(
        row for row in payload["process_participation_candidates"]
        if row["semantic_role"] == "CONTEXT_INTERVAL" and row["shot_present_annotation_candidate"] is True
    )
    generic["shot_present_annotation_candidate"] = False
    refined = dict(generic)
    refined["process_participation_candidate_id"] = generic["process_participation_candidate_id"] + "_shot"
    refined["shot_present_annotation_candidate"] = True
    payload["process_participation_candidates"].append(refined)
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), payload)
    profile = next(row for row in result["process_family_profiles"] if row["process_family_candidate"] == "POSITIONAL_ATTACKS")
    assert profile["shot_ending_n"] == 2
    assert result["representative_dyad_argument"]["shot_ending_n"] == 2

def test_c02_small_n_contract_does_not_coerce_not_target_annotation_into_resolved_non_shot():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    contract = dyad["small_n_association_contract"]
    assert contract["present_target_annotated_n"] == 2
    assert contract["present_not_target_annotated_n"] == 0
    assert contract["absent_target_annotated_n"] == 0
    assert contract["absent_not_target_annotated_n"] == 2
    assert contract["present_non_shot_n"] is None
    assert contract["absent_non_shot_n"] is None
    assert contract["outcome_resolution_state"] == "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE"
    assert contract["exchangeability_admitted"] is False
    assert contract["dependency_state"] == "UNRESOLVED_MATCH_LOCAL_PROCESS_DEPENDENCE"
    assert contract["fisher_exact_state"] == "NOT_EVALUATED_OUTCOME_RESOLUTION_UNAVAILABLE"
    assert contract["permutation_state"] == "NOT_EVALUATED_OUTCOME_RESOLUTION_AND_EXCHANGEABILITY_UNAVAILABLE"
    assert contract["p_value_is_football_importance"] is False


def test_c02_observation_capability_profile_distinguishes_annotation_absence_from_resolved_negative():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    profile = dyad["observation_capability_coverage_profile"]

    assert profile["required_capabilities"][-1] == "TARGET_OUTCOME_NEGATIVE_RESOLUTION"
    assert profile["missing_required_capabilities"] == ["TARGET_OUTCOME_NEGATIVE_RESOLUTION"]
    assert profile["capability_state"] == "PARTIALLY_ADMITTED"
    assert profile["coverage_state"] == "PARTIALLY_OBSERVABLE"
    assert profile["negative_claim_admission_state"] == "BLOCKED_NEGATIVE_OUTCOME_NOT_RESOLVABLE"
    assert profile["not_target_annotation_is_negative_outcome_truth"] is False
    assert dyad["not_target_annotated_is_resolved_non_target"] is False
    assert dyad["opportunity_normalized_evidence_anatomy"]["resolved_non_target_n"] is None


def test_c02_canonical_not_target_fields_preserve_legacy_alias_without_semantic_upgrade():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    actor = next(row for row in result["actor_argument_candidates"] if row["actor_identity_candidate_ids"] == ["actor_kerem"])

    assert actor["not_target_annotated_n"] == actor["non_shot_n"]
    assert actor["baseline_not_target_annotated_n"] == actor["baseline_non_shot_n"]
    assert actor["involved_without_target_annotation_refs"] == actor["counterexample_involved_without_shot_refs"]
    assert actor["legacy_non_shot_fields_deprecation_state"] == "DEPRECATED_COMPATIBILITY_ONLY"
    assert actor["legacy_non_shot_fields_are_resolved_non_target"] is False
    assert actor["baseline_not_target_annotated_is_resolved_non_target"] is False


def test_c02_epistemic_review_contract_preserves_claim_ceiling_and_exposes_review_actions():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    review = dyad["epistemic_review_contract"]

    assert review["contract_version"] == "C02_ASSOCIATION_EPISTEMIC_REVIEW_V1"
    assert review["creates_new_evidence"] is False
    assert review["can_authorize_emit"] is False
    assert review["can_strengthen_claim_ceiling"] is False
    assert review["claim_ceiling"] == dyad["claim_ceiling"]
    assert review["review_target_refs"] == dyad["shot_process_refs"]
    assert review["review_target_without_association_refs"] == dyad["counterexample_shot_without_association_refs"]
    assert review["review_not_target_annotated_refs"] == dyad["counterexample_involved_without_shot_refs"]
    assert "admitted current surfaces or other admissible evidence" in review["analyst_action"]
    assert "match_local_process_dependence_may_reduce_effective_support" in review["alternative_explanations"]
    assert "dependency_resolution_collapses_support_into_shared_lineage" in review["falsifier_conditions"]
    assert result["epistemic_review_contract_creates_new_evidence"] is False
    assert result["epistemic_review_contract_can_authorize_emit"] is False


def test_c02_descriptive_profile_separates_visible_annotation_from_resolved_outcome_and_selection_truth():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    assert dyad["eligible_n"] == dyad["support_n"] == 2
    assert dyad["visible_target_annotation_k"] == dyad["shot_ending_n"] == 2
    assert dyad["target_outcome_unresolved_u"] == 0
    assert dyad["observed_visible_target_annotation_frequency"] == 1.0
    assert dyad["observed_rate_semantics"] == "VISIBLE_TARGET_ANNOTATION_FREQUENCY_NOT_RESOLVED_OUTCOME_RATE"
    assert dyad["descriptive_lift"] == 2.0
    assert dyad["descriptive_lift_semantics"] == "VISIBLE_ANNOTATION_FREQUENCY_RATIO_MATCH_LOCAL_NOT_EFFECT_SIZE"
    assert dyad["eligible_episode_spread"] == 2
    assert dyad["positive_episode_spread"] == 2
    assert dyad["eligible_episode_spread_is_independence_proof"] is False
    assert dyad["positive_episode_spread_is_independence_proof"] is False
    assert dyad["selection_is_posthoc_attention_ranking"] is True
    assert dyad["selection_is_stable_signal"] is False
    assert dyad["no_p_value_eliminates_selection_multiplicity_risk"] is False
    assert dyad["outcome_must_not_define_its_own_eligible_denominator"] is True
    assert dyad["minimum_support_threshold_is_evidence_strength_truth"] is False
    assert dyad["shrunk_rate_is_observed_rate"] is False
    assert dyad["exact_computation_is_valid_football_inference"] is False
    assert dyad["cluster_aware_is_assumption_free"] is False
    assert dyad["claim_ceiling"] == "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY"


def test_c02_selection_scope_exposes_candidate_pool_and_posthoc_ranking():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    actor = result["representative_actor_argument"]
    dyad = result["representative_dyad_argument"]
    assert actor["selection_scope"] == "ALL_C02_ACTOR_CANDIDATES_CURRENT_MATCH"
    assert actor["selection_candidate_pool_n"] == result["selection_scope_actor_candidate_count"]
    assert dyad["selection_scope"] == "ALL_C02_DYAD_CANDIDATES_CURRENT_MATCH"
    assert dyad["selection_candidate_pool_n"] == result["selection_scope_dyad_candidate_count"]
    assert result["no_p_value_eliminates_selection_multiplicity_risk"] is False
    assert result["ranked_extreme_is_stable_signal"] is False


def test_c02_exposes_review_only_packet_candidates_without_independence_or_negative_invention():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    packets = result["packet_candidates"]
    assert result["packet_candidate_count"] == 2
    assert result["packet_candidates_create_new_evidence"] is False
    assert result["packet_candidates_admit_independent_support"] is False
    assert result["packet_candidates_can_authorize_emit"] is False
    for packet in packets:
        assert packet["source_construct_id"] == "C02_PROCESS_PARTICIPANT_OUTCOME_ASSOCIATION"
        assert packet["packet_family"] == "production_consequence"
        assert packet["claim_ceiling"] == "composite_candidate_only"
        assert packet["contradicting_signals"] == []
        assert len(packet["input_sequences"]) >= 2
        assert all(row["independent_support_vote"] is False for row in packet["input_sequences"])
        feature = packet["input_features"][0]
        assert feature["association_claim_ceiling"] == "MATCH_LOCAL_VISIBLE_ASSOCIATION_ONLY"
        assert feature["eligibility_contract"] == "C02_PROCESS_FAMILY_OUTCOME_BLIND_ELIGIBILITY_V1"
        assert feature["target_annotation_absence_is_counterevidence"] is False
        assert feature["association_is_causal_player_credit"] is False
        assert feature["selection_is_posthoc_attention_ranking"] is True
        assert feature["selection_is_stable_signal"] is False
        assert packet["supporting_signals"][0]["independent_support_vote"] is False
        assert packet["supporting_signals"][0]["statistical_significance_truth"] is False


def test_c02_opportunity_normalized_evidence_anatomy_freezes_denominator_and_preserves_episode_spread():
    result = _construct_c02(_c02_xlsx_rows(), _c02_identity(), _c02_process_payload())
    dyad = result["representative_dyad_argument"]
    anatomy = dyad["opportunity_normalized_evidence_anatomy"]
    assert anatomy["comparison_design_ref"] == "C02_PROCESS_FAMILY_OUTCOME_BLIND_ELIGIBILITY_V1"
    assert anatomy["denominator_state"] == "FAMILY_ELIGIBLE_PROCESS_N_FROZEN_BEFORE_OUTCOME_READ"
    assert anatomy["family_eligible_process_n"] == 4
    assert anatomy["association_involvement_n"] == 2
    assert anatomy["resolved_target_n"] == 2
    assert anatomy["resolved_non_target_n"] is None
    assert anatomy["unresolved_outcome_n"] is None
    assert anatomy["identification_state"] == "OUTCOME_RESOLUTION_CAPABILITY_NOT_AVAILABLE"
    assert anatomy["bound_transfer_state"] == "BOUND_NOT_TRANSFERABLE_TO_THIS_PROFILE"
    assert anatomy["supporting_episode_n"] == 2
    assert anatomy["episode_spread_is_independence_proof"] is False
    assert anatomy["lineage_group_n_is_effective_sample_size"] is False
    assert anatomy["counterexample_involved_without_target_refs"] == []


def test_full_spine_runs_sidecars_before_rich_multiformat_lane():
    source = (SRC / "full_spine_runner.py").read_text(encoding="utf-8")
    assert source.index("sidecar_report = run_sidecars(") < source.index("rich_report = run_rich_lane(")


def test_c03_builds_partial_order_process_development_and_anchor_path_without_tracking_claims():
    process = {
        "process_participation_candidates": [{
            "process_participation_candidate_id": "context_1",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "30",
            "shot_present_annotation_candidate": True,
        }]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "occ_1",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["12"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_1"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": ["SUCCESS"],
                "supporting_spatial_transition_candidate_ids": ["sp_1"],
            },
            {
                "action_occurrence_candidate_id": "occ_2",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["20"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_2"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": ["SUCCESS"],
                "supporting_spatial_transition_candidate_ids": ["sp_2"],
            },
            {
                "action_occurrence_candidate_id": "occ_3",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["20"],
                "action_family_candidates": ["CARRY"],
                "actor_identity_candidate_ids": ["actor_2"],
                "transition_class_candidates": ["VISIBLE_CONTINUATION_CANDIDATE"],
                "provider_outcome_candidates": [],
                "supporting_spatial_transition_candidate_ids": ["sp_2"],
            },
        ]
    }
    spatial = {
        "spatial_transition_candidates": [
            {
                "spatial_transition_candidate_id": "sp_1",
                "occurrence_annotation_anchor_location_admitted": True,
                "provider_coordinate_anchor_x_candidate": 20.0,
                "provider_coordinate_anchor_y_candidate": 30.0,
                "provider_zone_candidates": ["MIDDLE_THIRD"],
            },
            {
                "spatial_transition_candidate_id": "sp_2",
                "occurrence_annotation_anchor_location_admitted": True,
                "provider_coordinate_anchor_x_candidate": 50.0,
                "provider_coordinate_anchor_y_candidate": 40.0,
                "provider_zone_candidates": ["FINAL_THIRD"],
            },
        ]
    }
    result = _construct_c03(process, occurrences, spatial)
    signature = result["signatures"][0]
    assert signature["process_interval_duration_candidate"] == 20.0
    assert signature["process_duration_basis"] == "PROVIDER_REVIEWED_PROCESS_CONTEXT_INTERVAL"
    assert signature["process_interval_duration_is_generic_action_duration"] is False
    assert signature["temporal_layer_n"] == 2
    assert signature["layers"][1]["occurrence_ids"] == ["occ_2", "occ_3"]
    assert signature["layers"][1]["action_family_candidates"] == ["CARRY", "PASS"]
    assert signature["layers"][1]["same_timestamp_internal_ordering_allowed"] is False
    assert signature["annotation_anchor_path_coverage_state"] == "COMPLETE_CONSECUTIVE_SINGLE_ANCHOR"
    assert signature["annotation_anchor_segment_n"] == 1
    assert round(signature["annotation_anchor_segment_distance_sum_provider_units_candidate"], 6) == round((1000) ** 0.5, 6)
    assert signature["annotation_anchor_path_is_physical_trajectory"] is False
    assert signature["annotation_anchor_distance_is_physical_travel_distance"] is False
    assert signature["unique_actor_candidate_n"] == 2
    assert signature["action_family_layer_counts"] == {"CARRY": 1, "PASS": 2}
    assert signature["pass_carry_layer_mix"]["pass_layer_n"] == 2
    assert signature["pass_carry_layer_mix"]["carry_layer_n"] == 1
    assert signature["pass_carry_layer_mix"]["physical_touch_count_truth"] is False
    assert signature["visible_on_ball_profile"]["visible_on_ball_temporal_layer_n"] == 2
    assert signature["visible_on_ball_profile"]["visible_on_ball_family_layer_counts"] == {"CARRY": 1, "PASS": 2}
    assert signature["visible_on_ball_profile"]["temporal_layer_is_not_physical_touch"] is True
    assert signature["visible_on_ball_profile"]["same_timestamp_multi_family_is_not_multiple_touch_truth"] is True
    participation = signature["visible_on_ball_profile"]["actor_family_temporal_layer_participation_candidates"]
    assert [(row["actor_identity_candidate_id"], row["action_family_candidate"], row["temporal_layer_n"]) for row in participation] == [
        ("actor_1", "PASS", 1),
        ("actor_2", "CARRY", 1),
        ("actor_2", "PASS", 1),
    ]
    assert all(row["eligible_on_ball_temporal_layer_n"] == 2 for row in participation)
    assert all(row["temporal_layer_share_candidate"] == 0.5 for row in participation)
    assert all(row["causal_process_credit_truth"] is False for row in participation)
    assert signature["visible_on_ball_profile"]["actor_family_unresolved_temporal_layer_n"] == 0
    assert signature["visible_on_ball_profile"]["actor_family_participation_is_causal_process_credit"] is False
    assert signature["process_start_zone_candidates"] == ["MIDDLE_THIRD"]
    assert signature["process_end_zone_candidates"] == ["FINAL_THIRD"]
    assert signature["zone_layer_path_candidates"] == [["MIDDLE_THIRD"], ["FINAL_THIRD"]]
    assert signature["visible_zone_transition_candidate_n"] == 1
    assert signature["visible_zone_transition_candidates"][0]["from_zone_candidate"] == "MIDDLE_THIRD"
    assert signature["visible_zone_transition_candidates"][0]["to_zone_candidate"] == "FINAL_THIRD"
    assert signature["visible_zone_transition_candidates"][0]["progression_truth"] is False
    assert signature["visible_zone_transition_candidates"][0]["line_break_truth"] is False
    assert signature["visible_terminal_annotation_candidate_present"] is True
    assert signature["process_morphology_basis"] == "ADMITTED_TEMPORAL_LAYER_SUMMARY_NOT_PHYSICAL_TRAJECTORY_OR_PHASE_TRUTH"
    assert signature["tracking_truth"] is False
    assert result["process_morphology_is_phase_truth"] is False
    assert result["process_morphology_is_possession_truth"] is False
    assert result["process_morphology_is_tactical_plan_truth"] is False
    assert result["physical_speed_claim_allowed"] is False


def test_c03_loss_and_recovery_visibility_uses_explicit_consequence_semantics():
    process = {
        "process_participation_candidates": [{
            "process_participation_candidate_id": "context_consequence",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "30",
        }]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "occ_recovery",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["12"],
                "action_family_candidates": ["RECOVERY"],
                "actor_identity_candidate_ids": ["actor_1"],
                "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
                "primary_consequence_candidates": ["RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"],
                "supporting_spatial_transition_candidate_ids": [],
            },
            {
                "action_occurrence_candidate_id": "occ_loss",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["20"],
                "action_family_candidates": ["TURNOVER"],
                "actor_identity_candidate_ids": ["actor_2"],
                "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
                "primary_consequence_candidates": ["OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"],
                "supporting_spatial_transition_candidate_ids": [],
            },
        ]
    }
    result = _construct_c03(process, occurrences, {"spatial_transition_candidates": []})
    signature = result["signatures"][0]

    assert signature["visible_recovery_transition_candidate_present"] is True
    assert signature["visible_loss_transition_candidate_present"] is True
    assert signature["primary_consequence_candidates_observed"] == [
        "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
        "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE",
    ]
    assert signature["loss_recovery_visibility_basis"] == "EXPLICIT_ADMITTED_PRIMARY_CONSEQUENCE_CANDIDATES"


def test_c03_filters_occurrences_to_exact_team_period_and_process_interval():
    process = {
        "process_participation_candidates": [{
            "process_participation_candidate_id": "context_1",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "20",
        }]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {"action_occurrence_candidate_id": "inside", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["1"], "start_candidates": ["15"], "action_family_candidates": ["PASS"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "outside_time", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["1"], "start_candidates": ["25"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "other_team", "team_identity_candidate_ids": ["team_b"], "period_candidates": ["1"], "start_candidates": ["15"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
            {"action_occurrence_candidate_id": "other_period", "team_identity_candidate_ids": ["team_a"], "period_candidates": ["2"], "start_candidates": ["15"], "action_family_candidates": ["SHOT"], "supporting_spatial_transition_candidate_ids": []},
        ]
    }
    result = _construct_c03(process, occurrences, {"spatial_transition_candidates": []})
    signature = result["signatures"][0]
    assert signature["visible_occurrence_n"] == 1
    assert signature["layers"][0]["occurrence_ids"] == ["inside"]
    assert signature["source_row_order_is_temporal_truth"] is False
    assert signature["annotation_anchor_path_coverage_state"] == "PARTIAL_OR_AMBIGUOUS"


def test_c03_is_projected_into_human_analyst_report_without_physical_path_promotion():
    source = (SRC / "user_output_bundle.py").read_text(encoding="utf-8")
    assert "C03_process_development_signature_count" in source
    assert "SUREC GELISIM IMZASI ADAYI" in source
    assert "annotation-anchor yolu fiziksel top/oyuncu" in source
    assert "video/episode incelemesine" not in source


def _xlsx_metric(raw_label, raw_value):
    return {"raw_metric_label": raw_label, "raw_value": raw_value, "value_status": "OBSERVED"}


def test_c04_preserves_total_exposure_and_derives_only_closed_compositions():
    row = {
        "row_projection_id": "xrp_player_1",
        "identity_candidates": {"player_raw_candidate": "P1", "team_raw_candidate": "T1"},
        "metric_values": {
            "actions": _xlsx_metric("Actions", 10),
            "actions_successful": _xlsx_metric("Actions successful", 7),
            "actions_unsuccessful": _xlsx_metric("Actions unsuccessful", 3),
            "challenges": _xlsx_metric("Challenges", 8),
            "challenges_won": _xlsx_metric("Challenges won", 5),
            "challenges_unsuccessful": _xlsx_metric("Challenges unsuccessful", 3),
            "final_third_entries": _xlsx_metric("Final third entries", 4),
            "final_third_entries_through_pass": _xlsx_metric("Final third entries through pass", 3),
            "final_third_entries_through_carry": _xlsx_metric("Final third entries through carry", 1),
            "lost_balls": _xlsx_metric("Lost balls", 5),
            "lost_balls_after_passes": _xlsx_metric("Lost balls after passes", 2),
            "individual_ball_losses": _xlsx_metric("Individual ball losses", 3),
            "open_passes_received": _xlsx_metric("Open passes received", 10),
            "open_passes_received_in_the_first_third": _xlsx_metric("Open passes received in the first third", 2),
            "open_passes_received_in_the_central_third": _xlsx_metric("Open passes received in the central third", 5),
            "open_passes_received_in_the_final_third": _xlsx_metric("Open passes received in the final third", 3),
            "shots": _xlsx_metric("Shots", 4),
            "shots_from_the_penalty_area": _xlsx_metric("Shots from the penalty area", 3),
            "shots_from_outside_the_penalty_area": _xlsx_metric("Shots from outside the penalty area", 1),
            "xgt_xg_while_player_is_on_the_pitch": _xlsx_metric("xGT", 2.5),
            "xgopp_opponent_s_xg_while_player_is_on_the_pitch": _xlsx_metric("xGOPP", 1.0),
            "nxg_net_xg_difference_between_xgt_and_xgopp": _xlsx_metric("NxG", 1.5),
        },
    }
    result = _construct_c04([row])
    assert result["closed_composition_profile_count"] == 6
    entry = next(p for p in result["composition_profiles"] if p["family_id"] == "FINAL_THIRD_ENTRY_MODE_COMPOSITION")
    assert entry["total_value"] == 4
    assert entry["composition_shares"]["final_third_entries_through_pass"] == 0.75
    assert entry["composition_shares"]["final_third_entries_through_carry"] == 0.25
    assert entry["total_exposure_preserved_separately"] is True
    assert entry["derived_composition_adds_independent_evidence"] is False
    assert entry["component_balance_has_quality_direction"] is False
    residual = result["model_context_residual_profiles"][0]
    assert residual["nxg_recomputed"] == 1.5
    assert residual["provider_model_output_context_only"] is True
    assert residual["player_causal_contribution_truth"] is False
    assert result["no_scalar_player_quality_score_created"] is True


def test_c04_mismatch_and_missing_components_are_not_forced_into_composition_truth():
    rows = [
        {
            "row_projection_id": "xrp_bad",
            "identity_candidates": {"player_raw_candidate": "P1"},
            "metric_values": {
                "actions": _xlsx_metric("Actions", 10),
                "actions_successful": _xlsx_metric("Actions successful", 8),
                "actions_unsuccessful": _xlsx_metric("Actions unsuccessful", 3),
            },
        },
        {
            "row_projection_id": "xrp_missing",
            "identity_candidates": {"player_raw_candidate": "P2"},
            "metric_values": {
                "actions": _xlsx_metric("Actions", 10),
                "actions_successful": _xlsx_metric("Actions successful", 8),
            },
        },
    ]
    result = _construct_c04(rows)
    assert result["composition_profile_count"] == 1
    profile = result["composition_profiles"][0]
    assert profile["closure_state"] == "DEFINITION_OR_DATA_MISMATCH_REVIEW"
    assert profile["composition_shares"] is None
    assert result["family_closure_audit"]["ACTION_OUTCOME_COMPOSITION"]["mismatch_n"] == 1


def test_c04_is_projected_into_analyst_report_as_total_plus_composition_not_quality_score():
    source = (SRC / "user_output_bundle.py").read_text(encoding="utf-8")
    assert "C04_closed_composition_profile_count" in source
    assert "XLSX BILESIM ADAYI" in source
    assert "Toplam hacim ayri eksendir" in source


def test_canonical_six_phase_ontology_separates_phase_from_evaluation() -> None:
    contract = _football_ontology_contract()
    assert contract["canonical_six_phases"] == [
        "ESTABLISHED_ATTACK",
        "ATTACKING_TRANSITION",
        "ATTACKING_SET_PIECE",
        "ESTABLISHED_DEFENCE",
        "DEFENSIVE_TRANSITION",
        "DEFENSIVE_SET_PIECE",
    ]
    assert contract["phase_is_evaluation"] is False
    assert contract["phase_is_outcome"] is False
    assert contract["success_failure_is_phase"] is False
    assert contract["efficiency_inefficiency_is_phase"] is False
    assert contract["set_piece_is_open_play_subtype"] is False
    assert "OPPONENT" in contract["observation_dimensions"]
    assert "TWO_TEAM_INTERACTION" in contract["scale_axis"]
    donor = contract["external_donor_adaptation_contract"]
    assert donor["provider_normalization"]["normalize_at_boundary_not_inside_constructs"] is True
    assert donor["provider_normalization"]["coordinate_system_requires_explicit_admission"] is True
    assert donor["action_state_consequence"]["action_value_model_is_not_observation_truth"] is True
    assert donor["tracking_boundary"]["event_coordinate_is_not_tracking"] is True
    assert donor["tracking_boundary"]["pitch_control_requires_tracking_or_equivalent_spatiotemporal_observation"] is True


def test_activity_state_candidates_do_not_claim_phase_admission() -> None:
    payload = {"episode_feature_vectors": [{"shot_candidate_count": 1, "action_family_counts": {"PASS": 2}}]}
    candidate = _phase_state_candidates(payload)[0]
    assert candidate["activity_labels_are_phase_labels"] is False
    assert candidate["phase_admission_status"] == "NOT_EVALUATED"
    assert candidate["phase_truth"] is False



def test_c03_builds_twelve_direction_six_phase_team_matrix() -> None:
    processes = []
    families = (
        "POSITIONAL_ATTACK_CANDIDATE",
        "COUNTERATTACK_CANDIDATE",
        "SET_PIECE_ATTACK_CANDIDATE",
    )
    cursor = 10.0
    for team in ("A", "B"):
        for family in families:
            processes.append({
                "process_participation_candidate_id": f"{team}_{family}",
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": family,
                "team_identity_candidate_id": team,
                "period_candidate": "1",
                "start_candidate": cursor,
                "end_candidate": cursor + 5.0,
                "shot_present_annotation_candidate": family == "POSITIONAL_ATTACK_CANDIDATE",
            })
            cursor += 10.0
    result = _construct_c03(
        {"process_participation_candidates": processes},
        {"occurrence_state_transition_projections": []},
        {"spatial_transition_candidates": []},
    )
    assert result["six_phase_team_matrix_expected_direction_count"] == 12
    assert result["six_phase_team_matrix_direction_count"] == 12
    assert result["six_phase_team_matrix_visible_direction_count"] == 12
    rows = result["six_phase_team_matrix"]
    a_def = next(
        row for row in rows
        if row["team_identity_candidate_id"] == "A"
        and row["canonical_phase_slot"] == "ESTABLISHED_DEFENCE"
    )
    assert a_def["source_process_profile_team_identity_candidate_id"] == "B"
    assert a_def["source_process_family_candidate"] == "POSITIONAL_ATTACK_CANDIDATE"
    assert a_def["metric_semantics"] == "OPPONENT_VISIBLE_PROCESS_EXPOSURE_PROFILE"
    assert a_def["opponent_visible_loss_is_forced_turnover_truth"] is False
    assert a_def["mean_duration_candidate"] == 5.0
    assert a_def["shot_variant_n"] == 1
    assert a_def["non_shot_variant_n"] == 0
    assert isinstance(a_def["representative_shot_process"], dict)
    assert a_def["representative_shot_process"]["replay_is_physical_trajectory_truth"] is False
    assert a_def["anatomy_is_physical_trajectory_truth"] is False
    assert result["six_phase_team_matrix_is_phase_truth"] is False


def test_c03_motif_identity_is_outcome_independent_and_keeps_variants_together() -> None:
    processes = [
        {
            "process_participation_candidate_id": "p_shot",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 10.0,
            "end_candidate": 15.0,
            "shot_present_annotation_candidate": True,
        },
        {
            "process_participation_candidate_id": "p_loss",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 20.0,
            "end_candidate": 25.0,
            "shot_present_annotation_candidate": False,
        },
        {
            "process_participation_candidate_id": "p_carry",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 30.0,
            "end_candidate": 35.0,
            "shot_present_annotation_candidate": False,
        },
    ]
    occurrences = [
        {
            "action_occurrence_candidate_id": "o_shot",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [12.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a1"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "o_loss",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [22.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a2"],
            "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "o_carry",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [32.0],
            "action_family_candidates": ["CARRY"],
            "actor_identity_candidate_ids": ["a3"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
    ]
    result = _construct_c03(
        {"process_participation_candidates": processes},
        {"occurrence_state_transition_projections": occurrences},
        {"spatial_transition_candidates": []},
    )
    motifs = result["process_motif_family_candidates"]
    recurring = [row for row in motifs if row["recurring_motif_candidate"]]
    assert len(recurring) == 1
    motif = recurring[0]
    assert motif["member_process_n"] == 2
    assert motif["shot_variant_n"] == 1
    assert motif["non_shot_variant_n"] == 1
    assert motif["visible_loss_variant_n"] == 1
    assert motif["outcome_fields_participate_in_motif_identity"] is False
    assert motif["same_motif_outcomes_are_variant_context_only"] is True
    assert result["process_motif_identity_uses_outcome"] is False


def test_c03_recurring_motif_exposes_first_supported_grammar_divergence() -> None:
    processes = [
        {
            "process_participation_candidate_id": "p_shot",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 10.0,
            "end_candidate": 16.0,
            "shot_present_annotation_candidate": True,
        },
        {
            "process_participation_candidate_id": "p_loss",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 20.0,
            "end_candidate": 26.0,
            "shot_present_annotation_candidate": False,
        },
    ]
    occurrences = [
        {
            "action_occurrence_candidate_id": "s1",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [11.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a1"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "s2",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [13.0],
            "action_family_candidates": ["CARRY"],
            "actor_identity_candidate_ids": ["a2"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "l1",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [21.0],
            "action_family_candidates": ["CARRY"],
            "actor_identity_candidate_ids": ["a3"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "l2",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [23.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a4"],
            "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
            "supporting_spatial_transition_candidate_ids": [],
        },
    ]
    result = _construct_c03(
        {"process_participation_candidates": processes},
        {"occurrence_state_transition_projections": occurrences},
        {"spatial_transition_candidates": []},
    )
    motifs = [row for row in result["process_motif_family_candidates"] if row["recurring_motif_candidate"]]
    assert len(motifs) == 1
    motif = motifs[0]
    assert motif["member_process_n"] == 2
    div = motif["representative_first_supported_grammar_divergence"]
    assert isinstance(div, dict)
    assert {div["left_variant_context"], div["right_variant_context"]} == {"SHOT_LINKED", "LOSS_LINKED"}
    assert div["first_supported_grammar_divergence"]["operation"] in {"SUBSTITUTE", "INSERT", "DELETE"}
    assert div["contrast_pair_outcome_context_is_not_similarity_basis"] is True
    assert div["first_divergence_is_causal_breakpoint_truth"] is False


def test_c03_variant_profiles_never_pool_opponent_teams() -> None:
    from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import _construct_c03

    processes = []
    occurrences = []
    for team, base in (("A", 10.0), ("B", 30.0)):
        for suffix, shot, offset in (("shot", True, 0.0), ("no", False, 10.0)):
            pid = f"{team}_{suffix}"
            start = base + offset
            processes.append({
                "process_participation_candidate_id": pid,
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "BUILD_UP",
                "team_identity_candidate_id": team,
                "period_candidate": "1",
                "start_candidate": start,
                "end_candidate": start + 5.0,
                "shot_present_annotation_candidate": shot,
            })
            occurrences.append({
                "action_occurrence_candidate_id": "occ_" + pid,
                "team_identity_candidate_ids": [team],
                "period_candidates": ["1"],
                "start_candidates": [start + 1.0],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_" + team],
                "transition_class_candidates": [],
                "provider_outcome_candidates": [],
                "primary_consequence_candidates": [],
                "supporting_spatial_transition_candidate_ids": [],
            })

    result = _construct_c03(
        {"process_participation_candidates": processes},
        {"occurrence_state_transition_projections": occurrences},
        {"spatial_transition_candidates": []},
    )
    profiles = result["variant_context_profiles"]
    assert len(profiles) == 2
    assert {row["team_identity_candidate_id"] for row in profiles} == {"A", "B"}
    assert all(row["eligible_process_n"] == 2 for row in profiles)
    assert all(row["cross_team_variant_pooling_allowed"] is False for row in profiles)


def test_c03_preserves_full_occurrence_pool_across_multiple_processes():
    process = {
        "process_participation_candidates": [
            {
                "process_participation_candidate_id": "context_1",
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": "10",
                "end_candidate": "20",
                "shot_present_annotation_candidate": False,
            },
            {
                "process_participation_candidate_id": "context_2",
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_b",
                "period_candidate": "1",
                "start_candidate": "30",
                "end_candidate": "40",
                "shot_present_annotation_candidate": False,
            },
        ]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "occ_a",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": ["15"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_a"],
                "supporting_spatial_transition_candidate_ids": [],
            },
            {
                "action_occurrence_candidate_id": "occ_b",
                "team_identity_candidate_ids": ["team_b"],
                "period_candidates": ["1"],
                "start_candidates": ["35"],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_b"],
                "supporting_spatial_transition_candidate_ids": [],
            },
        ]
    }
    result = _construct_c03(process, occurrences, {"spatial_transition_candidates": []})
    by_ref = {row["process_ref"]: row for row in result["signatures"]}
    assert by_ref["context_1"]["visible_occurrence_n"] == 1
    assert by_ref["context_2"]["visible_occurrence_n"] == 1
    assert by_ref["context_1"]["visible_on_ball_profile"]["visible_on_ball_temporal_layer_n"] == 1
    assert by_ref["context_2"]["visible_on_ball_profile"]["visible_on_ball_temporal_layer_n"] == 1


def test_entity_views_infers_goalkeeper_from_schema_not_filename_or_person_name():
    rows = [
        {
            "row_projection_id": "gk1",
            "source_role": "AGGREGATE_OR_TABULAR_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Example A"},
            "metric_values": {
                "shots_faced": {"value_status": "OBSERVED", "raw_value": 4},
                "shots_saved": {"value_status": "OBSERVED", "raw_value": 3},
            },
        },
        {
            "row_projection_id": "p1",
            "source_role": "AGGREGATE_OR_TABULAR_SURFACE_CANDIDATE",
            "identity_candidates": {"player_raw_candidate": "Example B"},
            "metric_values": {
                "passes": {"value_status": "OBSERVED", "raw_value": 20},
                "shots": {"value_status": "OBSERVED", "raw_value": 2},
            },
        },
    ]
    views = _entity_views(rows)
    assert len(views["goalkeeper_view_candidates"]) == 1
    assert len(views["player_view_candidates"]) == 1
    assert views["goalkeeper_view_candidates"][0]["entity_role_candidate"] == "GOALKEEPER"
    assert views["player_view_candidates"][0]["entity_role_candidate"] == "PLAYER"


def test_c03_builds_nonexclusive_visible_consequence_response_profile() -> None:
    processes = {
        "process_participation_candidates": [
            {
                "process_participation_candidate_id": "p1",
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 10.0,
                "end_candidate": 20.0,
                "shot_present_annotation_candidate": False,
            },
            {
                "process_participation_candidate_id": "p2",
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 30.0,
                "end_candidate": 40.0,
                "shot_present_annotation_candidate": False,
            },
        ]
    }
    occurrences = {
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "occ_1",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [12.0],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_a"],
                "primary_consequence_candidates": [
                    "OPPONENT_HANDOVER_CANDIDATE",
                    "SAME_TEAM_CONTINUATION_CANDIDATE",
                ],
                "supporting_spatial_transition_candidate_ids": [],
            },
            {
                "action_occurrence_candidate_id": "occ_2",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [32.0],
                "action_family_candidates": ["PASS"],
                "actor_identity_candidate_ids": ["actor_a"],
                "primary_consequence_candidates": [
                    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
                    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
                    "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
                ],
                "supporting_spatial_transition_candidate_ids": [],
            },
        ]
    }

    result = _construct_c03(processes, occurrences, {"spatial_transition_candidates": []})
    profile = result["team_process_profiles"][0]["visible_consequence_response_profile"]
    counts = profile["process_presence_counts"]

    assert profile["eligible_process_n"] == 2
    assert counts["OPPONENT_HANDOVER_CANDIDATE"] == 1
    assert counts["OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"] == 1
    assert counts["SAME_TEAM_CONTINUATION_CANDIDATE"] == 1
    assert counts["MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"] == 1
    assert counts["NO_VISIBLE_FOLLOW_UP_CANDIDATE"] == 1
    assert profile["categories_are_mutually_exclusive"] is False
    assert profile["counts_are_process_presence_not_occurrence_volume"] is True
    assert profile["opponent_handover_is_forced_turnover_truth"] is False
    assert profile["opponent_takeover_is_pressure_success_truth"] is False
    assert profile["mixed_team_same_time_is_ordered_response_truth"] is False
    assert profile["no_visible_followup_is_failure"] is False
    assert profile["profile_is_opponent_tactical_response_truth"] is False
    assert profile["profile_is_independent_support"] is False
    assert profile["claim_ceiling"] == "MATCH_LOCAL_VISIBLE_CONSEQUENCE_RESPONSE_PROFILE_CANDIDATE_ONLY"


def test_c03_morphology_neighborhood_links_near_variant_without_merging_exact_motif() -> None:
    processes = [
        {
            "process_participation_candidate_id": "p1",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 10.0,
            "end_candidate": 16.0,
            "shot_present_annotation_candidate": False,
        },
        {
            "process_participation_candidate_id": "p2",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 20.0,
            "end_candidate": 26.0,
            "shot_present_annotation_candidate": False,
        },
        {
            "process_participation_candidate_id": "p3",
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "A",
            "period_candidate": "1",
            "start_candidate": 30.0,
            "end_candidate": 36.0,
            "shot_present_annotation_candidate": False,
        },
    ]
    occurrences = [
        {
            "action_occurrence_candidate_id": "o1",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [11.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a1"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "o2",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [21.0],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_ids": ["a2"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
        {
            "action_occurrence_candidate_id": "o3",
            "team_identity_candidate_ids": ["A"],
            "period_candidates": ["1"],
            "start_candidates": [31.0],
            "action_family_candidates": ["PASS", "DUEL"],
            "actor_identity_candidate_ids": ["a3"],
            "primary_consequence_candidates": [],
            "supporting_spatial_transition_candidate_ids": [],
        },
    ]

    result = _construct_c03(
        {"process_participation_candidates": processes},
        {"occurrence_state_transition_projections": occurrences},
        {"spatial_transition_candidates": []},
    )

    assert result["recurring_process_motif_family_candidate_count"] == 1
    assert result["recurring_process_motif_covered_process_n"] == 2
    assert result["process_motif_neighborhood_candidate_count"] == 1
    assert result["singleton_process_motif_with_recurring_neighbor_count"] == 1

    neighbor = result["process_motif_neighborhood_candidates"][0]
    assert neighbor["neighborhood_basis"] == "ONE_ACTION_FAMILY_DELTA_SAME_LENGTH_BUCKET"
    assert neighbor["action_family_delta"] == ["DUEL"]
    assert sorted([neighbor["left_member_process_n"], neighbor["right_member_process_n"]]) == [1, 2]
    assert neighbor["exact_motif_identity_changed"] is False
    assert neighbor["recurrence_support_created"] is False
    assert neighbor["independent_support_created"] is False
    assert neighbor["similarity_is_tactical_pattern_truth"] is False
    assert neighbor["similarity_is_coach_intention_truth"] is False
    assert neighbor["similarity_is_causal_equivalence_truth"] is False
    assert neighbor["outcome_participates_in_neighborhood_identity"] is False
    assert neighbor["claim_ceiling"] == "MATCH_LOCAL_VISIBLE_PROCESS_MORPHOLOGY_NEIGHBOR_CANDIDATE_ONLY"
