from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich_multiformat_analysis_lane import (
    _build_p02_comparison_populations,
    _build_p02_sequence_process_units,
    _build_p02_process_unit_comparison_populations,
    _construct_c01,
    _phase_state_candidates,
    _progression_pool_p02,
    _score_state_timeline_candidates,
    _team_score_state_at_episode_start,
)
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet
from hpfa.modules.core.multi_signal_evidence_fusion_lite.src.multi_signal_evidence_fusion import fuse_packet
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


def test_c01_construct_can_enter_existing_composite_packet_without_independence_inflation():
    projection_rows = [{
        "row_projection_id": "xrp_1",
        "source_sha256": "same_provider_sha",
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
    packet = build_composite_packet(construct["packet_candidate"])
    assert packet["status"] == "SMOKE_PASS"
    assert packet["packet_family"] == "progression"
    assert packet["independent_support_count"] == 0
    assert packet["nominal_ref_count_is_independent_support_count"] is False
    assert packet["claim_ceiling"] == "composite_candidate_only"



def _p02_features():
    return {
        "episode_feature_vectors": [
            {
                "episode_candidate_id": "aep_generic_001",
                "episode_feature_vector_id": "efv:aep_generic_001",
                "claim_ceiling": "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
                "period_candidate": "1",
                "start_second_candidate": 10.0,
                "end_second_candidate": 70.0,
                "duration_seconds_candidate": 60.0,
                "eligible_action_candidate_count": 12,
                "same_time_unordered_layer_count": 2,
                "action_family_counts": {"PASS": 8, "DRIBBLE": 2, "TURNOVER": 2},
                "eligible_action_zone_counts": {"DEFENSIVE_THIRD": 4, "MIDDLE_THIRD": 6, "FINAL_THIRD": 2},
                "eligible_action_channel_counts": {"LEFT_CHANNEL": 3, "CENTRAL_CHANNEL": 5, "RIGHT_CHANNEL": 4},
                "shot_candidate_count": 1,
                "turnover_candidate_count": 2,
                "recovery_candidate_count": 1,
                "feature_readiness": "FEATURE_READY",
                "context_refs": ["ctx_1", "ctx_2"],
            }
        ]
    }


def _p02_temporal():
    return {
        "temporal_episode_signatures": [
            {
                "temporal_episode_signature_id": "tes:aep_generic_001",
                "episode_candidate_id": "aep_generic_001",
                "comparison_status": "COMPARABLE_PRIOR_EPISODE_AVAILABLE",
                "eligible_action_rate_delta_per_minute": 1.5,
                "zone_share_shift_candidate": {"FINAL_THIRD": 0.1},
                "channel_share_shift_candidate": {"CENTRAL_CHANNEL": -0.05},
            }
        ]
    }


def test_p02_projection_builds_atoms_and_pool_item_without_independence_inflation():
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal())
    assert p02["p02_pool_item_count"] == 1
    assert p02["finding_atom_candidate_count"] == 6
    assert p02["pool_item_is_new_evidence_vote"] is False
    assert p02["invented_semantics_count"] == 0
    item = p02["p02_pool_items"][0]
    assert item["pool_id"] == "P02_PROGRESSION"
    assert item["dependency_roots"] == ["episode_feature:aep_generic_001"]
    assert item["station_type"] == "ACTION_STATION"
    assert item["visible_observation_summary"]["action_station_candidate_count"] == 12


def test_p02_projection_preserves_same_time_ambiguity_and_withholds_route_truth():
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal())
    item = p02["p02_pool_items"][0]
    signature = item["process_signature_fields"]
    assert signature["same_time_unordered_layer_count"] == 2
    assert signature["route_evaluability"] == "NOT_EVALUATED"
    assert signature["visible_path_length_proxy"] is None
    assert signature["directness_proxy"] is None
    assert p02["same_timestamp_is_total_order"] is False
    assert p02["coordinate_is_tracking"] is False


def test_p02_projection_zero_duration_does_not_invent_rate():
    features = _p02_features()
    features["episode_feature_vectors"][0]["duration_seconds_candidate"] = 0.0
    p02 = _progression_pool_p02(features, _p02_temporal())
    item = p02["p02_pool_items"][0]
    assert item["visible_observation_summary"]["eligible_action_rate_per_second_candidate"] is None


def test_p02_projection_final_third_activity_is_candidate_not_access_truth():
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal())
    item = p02["p02_pool_items"][0]
    assert item["process_signature_fields"]["advanced_access_activity_candidate"] is True
    assert "start_end_zone_transition_not_bound" in item["unresolved_refs"]
    assert item["claim_ceiling"] == "P02_EPISODE_DESCRIPTIVE_CANDIDATE_ONLY"



def _p02_episode():
    return {
        "episode_candidates": [
            {
                "episode_candidate_id": "aep_generic_001",
                "time_layer_refs": ["ael_1", "ael_2", "ael_3", "ael_4"],
            }
        ],
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id": "ael_1",
                "second_candidate": 10.0,
                "eligible_action_zone_candidate_counts": {"DEFENSIVE_THIRD": 2},
                "same_time_unordered": True,
            },
            {
                "episode_time_layer_candidate_id": "ael_2",
                "second_candidate": 20.0,
                "eligible_action_zone_candidate_counts": {"MIDDLE_THIRD": 1},
                "same_time_unordered": False,
            },
            {
                "episode_time_layer_candidate_id": "ael_3",
                "second_candidate": 30.0,
                "eligible_action_zone_candidate_counts": {"MIDDLE_THIRD": 1, "FINAL_THIRD": 1},
                "same_time_unordered": True,
            },
            {
                "episode_time_layer_candidate_id": "ael_4",
                "second_candidate": 40.0,
                "eligible_action_zone_candidate_counts": {"FINAL_THIRD": 2},
                "same_time_unordered": True,
            },
        ],
    }


def test_p02_zone_station_path_uses_only_unique_zone_time_layers():
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal(), _p02_episode())
    item = p02["p02_pool_items"][0]
    signature = item["process_signature_fields"]
    assert signature["zone_station_path_candidate"] == [
        "DEFENSIVE_THIRD",
        "MIDDLE_THIRD",
        "FINAL_THIRD",
    ]
    assert signature["zone_station_count_candidate"] == 3
    assert signature["start_zone_candidate"] == "DEFENSIVE_THIRD"
    assert signature["end_zone_candidate"] == "FINAL_THIRD"
    assert signature["zone_advancement_steps_candidate"] == 2
    assert len(signature["zone_transition_candidates"]) == 2


def test_p02_zone_transition_does_not_assert_internal_same_time_order():
    episode = _p02_episode()
    episode["episode_time_layer_candidates"][1]["second_candidate"] = 10.0
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal(), episode)
    item = p02["p02_pool_items"][0]
    transitions = item["process_signature_fields"]["zone_transition_candidates"]
    assert all(row["same_timestamp_transition"] is False for row in transitions)
    assert all(row["transition_is_physical_trajectory_truth"] is False for row in transitions)


def test_p02_zone_advancement_is_discrete_zone_candidate_not_metric_distance():
    p02 = _progression_pool_p02(_p02_features(), _p02_temporal(), _p02_episode())
    item = p02["p02_pool_items"][0]
    assert item["visible_observation_summary"]["zone_advancement_steps_candidate"] == 2
    assert item["process_signature_fields"]["net_goalward_progression"] is None
    assert item["process_signature_fields"]["visible_path_length_proxy"] is None



def _p02_consequence():
    return {
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "tacc_1",
                "period_candidate": "1",
                "anchor_start_candidate": "15.0",
                "supporting_action_occurrence_candidate_ids": ["aoc_1"],
                "occurrence_visible_consequence_support": True,
                "visible_follow_up_trace_ids": ["tat_2"],
                "terminal_outcome_support_visible": False,
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
            },
            {
                "trackable_action_consequence_candidate_id": "tacc_2",
                "period_candidate": "1",
                "anchor_start_candidate": "15.0",
                "supporting_action_occurrence_candidate_ids": ["aoc_1"],
                "occurrence_visible_consequence_support": True,
                "visible_follow_up_trace_ids": ["tat_3"],
                "terminal_outcome_support_visible": True,
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
            },
            {
                "trackable_action_consequence_candidate_id": "tacc_outside",
                "period_candidate": "1",
                "anchor_start_candidate": "90.0",
                "supporting_action_occurrence_candidate_ids": ["aoc_outside"],
                "occurrence_visible_consequence_support": True,
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
            },
        ]
    }


def test_p02_consequence_binding_collapses_same_occurrence_root():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
    )
    item = p02["p02_pool_items"][0]
    summary = item["visible_observation_summary"]
    signature = item["process_signature_fields"]
    assert summary["occurrence_bound_consequence_occurrence_count"] == 1
    assert summary["visible_follow_up_occurrence_count"] == 1
    assert summary["terminal_support_occurrence_count"] == 1
    assert summary["opponent_follow_up_visible_occurrence_count"] == 1
    assert signature["occurrence_ids"] == ["aoc_1"]
    assert signature["opponent_follow_up_occurrence_ids"] == ["aoc_1"]


def test_p02_opponent_followup_is_visible_candidate_not_tactical_response_truth():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
    )
    item = p02["p02_pool_items"][0]
    signature = item["process_signature_fields"]
    assert item["opponent_context"] == "VISIBLE_OPPONENT_FOLLOW_UP_CANDIDATE"
    assert signature["occurrence_consequence_binding_is_causal_truth"] is False
    assert signature["opponent_follow_up_is_tactical_response_truth"] is False


def test_p02_consequence_binding_respects_episode_time_bounds():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
    )
    item = p02["p02_pool_items"][0]
    assert "aoc_outside" not in item["process_signature_fields"]["occurrence_ids"]



def _p02_semantics():
    return {
        "context_action_semantic_records": [
            {
                "context_id": "ctx_1",
                "action_occurrence_eligible": True,
                "context_team_candidate": "TEAM_A",
                "provider_action_family_candidate": "PASS",
                "context_zone_candidate": "DEFENSIVE_THIRD",
                "context_channel_candidate": "LEFT_CHANNEL",
            },
            {
                "context_id": "ctx_2",
                "action_occurrence_eligible": True,
                "context_team_candidate": "TEAM_B",
                "provider_action_family_candidate": "TURNOVER",
                "context_zone_candidate": "MIDDLE_THIRD",
                "context_channel_candidate": "CENTRAL_CHANNEL",
            },
        ]
    }


def test_p02_team_split_creates_team_specific_child_items():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
        _p02_semantics(),
    )
    assert p02["p02_team_pool_item_count"] == 2
    by_team = {row["team_candidate"]: row for row in p02["p02_team_pool_items"]}
    assert by_team["TEAM_A"]["visible_observation_summary"]["action_family_counts"] == {"PASS": 1}
    assert by_team["TEAM_B"]["visible_observation_summary"]["action_family_counts"] == {"TURNOVER": 1}
    assert by_team["TEAM_A"]["visible_observation_summary"]["zone_counts"] == {"DEFENSIVE_THIRD": 1}
    assert by_team["TEAM_B"]["visible_observation_summary"]["zone_counts"] == {"MIDDLE_THIRD": 1}


def test_p02_team_process_stage_profile_preserves_stage_presence_without_inventing_order():
    features = _p02_features()
    features["episode_feature_vectors"][0]["context_refs"] = ["s1", "s2", "s3"]
    semantics = {
        "context_action_semantic_records": [
            {
                "context_id": "s1",
                "action_occurrence_eligible": True,
                "context_team_candidate": "TEAM_A",
                "provider_action_family_candidate": "PASS",
                "provider_progression_candidate": "PROGRESSIVE_CANDIDATE",
                "provider_zone_candidate": "PENALTY_AREA",
                "provider_key_action_candidate": "KEY_PASS_CANDIDATE",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "context_zone_candidate": "FINAL_THIRD",
                "context_channel_candidate": "CENTRAL_CHANNEL",
            },
            {
                "context_id": "s2",
                "action_occurrence_eligible": True,
                "context_team_candidate": "TEAM_A",
                "provider_action_family_candidate": "SHOT",
                "provider_shot_result_candidate": "ON_TARGET",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "context_zone_candidate": "FINAL_THIRD",
                "context_channel_candidate": "CENTRAL_CHANNEL",
            },
            {
                "context_id": "s3",
                "action_occurrence_eligible": False,
                "context_team_candidate": "TEAM_A",
                "provider_action_family_candidate": "UNKNOWN",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "context_zone_candidate": "FINAL_THIRD",
                "context_channel_candidate": "CENTRAL_CHANNEL",
            },
        ]
    }
    p02 = _progression_pool_p02(
        features,
        _p02_temporal(),
        _p02_episode(),
        {},
        semantics,
    )
    team = next(row for row in p02["p02_team_pool_items"] if row["team_candidate"] == "TEAM_A")
    profile = team["process_signature_fields"]["team_specific_process_stage_profile"]
    assert profile["stage_counts"]["PROGRESSION"] == 1
    assert profile["stage_counts"]["FINAL_THIRD"] == 2
    assert profile["stage_counts"]["PENALTY_AREA"] == 1
    assert profile["stage_counts"]["KEY_ACTION"] == 1
    assert profile["stage_counts"]["SHOT"] == 1
    assert profile["stage_counts"]["SHOT_ON_TARGET"] == 1
    assert "GOAL" not in profile["stage_counts"]
    assert "CHANCE" not in profile["stage_counts"]
    assert profile["spatial_access_stage_candidate"] == "PENALTY_AREA"
    assert profile["terminal_action_stage_candidate"] == "SHOT_ON_TARGET"
    assert profile["chance_stage_status"] == "NOT_EVALUATED_NO_PROCESS_BOUND_TERMINAL_AUTHORITY"
    assert profile["goal_stage_status"] == "NOT_EVALUATED_NO_PROCESS_BOUND_TERMINAL_AUTHORITY"
    assert profile["exit_stage_candidate"] == "UNRESOLVED"
    assert profile["ordering_state"] == "PRESENCE_ONLY_NO_TOTAL_ORDER"
    assert profile["terminal_outcomes_do_not_add_action_volume"] is True
    assert profile["stage_counts_are_event_counts"] is False
    assert profile["stage_counts_are_independent_support"] is False
    assert profile["single_linear_stage_ladder_claimed"] is False
    assert profile["stage_ladder_is_physical_sequence_truth"] is False
    assert profile["spatial_access_stage_is_tactical_quality_truth"] is False
    assert profile["terminal_action_stage_is_tactical_quality_truth"] is False


def test_p02_team_child_items_do_not_create_independent_support_votes():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
        _p02_semantics(),
    )
    parent = p02["p02_pool_items"][0]
    for child in p02["p02_team_pool_items"]:
        assert child["parent_pool_item_id"] == parent["pool_item_id"]
        assert child["independent_support_vote"] is False
        assert parent["dependency_roots"][0] in child["dependency_roots"]


def test_p02_team_split_ignores_noneligible_semantic_context():
    semantics = _p02_semantics()
    semantics["context_action_semantic_records"].append({
        "context_id": "ctx_3",
        "action_occurrence_eligible": False,
        "context_team_candidate": "TEAM_A",
        "provider_action_family_candidate": "SHOT",
        "context_zone_candidate": "FINAL_THIRD",
        "context_channel_candidate": "RIGHT_CHANNEL",
    })
    features = _p02_features()
    features["episode_feature_vectors"][0]["context_refs"].append("ctx_3")
    p02 = _progression_pool_p02(
        features,
        _p02_temporal(),
        _p02_episode(),
        _p02_consequence(),
        semantics,
    )
    by_team = {row["team_candidate"]: row for row in p02["p02_team_pool_items"]}
    assert by_team["TEAM_A"]["visible_observation_summary"]["shot_candidate_count"] == 0



def _p02_team_path_case():
    features = _p02_features()
    features["episode_feature_vectors"][0]["context_refs"] = ["a1", "a2", "a3", "b1", "b2"]
    semantics = {
        "context_action_semantic_records": [
            {"context_id":"a1","action_occurrence_eligible":True,"context_team_candidate":"TEAM_A","provider_action_family_candidate":"PASS","context_zone_candidate":"DEFENSIVE_THIRD","context_channel_candidate":"LEFT_CHANNEL"},
            {"context_id":"a2","action_occurrence_eligible":True,"context_team_candidate":"TEAM_A","provider_action_family_candidate":"PASS","context_zone_candidate":"MIDDLE_THIRD","context_channel_candidate":"CENTRAL_CHANNEL"},
            {"context_id":"a3","action_occurrence_eligible":True,"context_team_candidate":"TEAM_A","provider_action_family_candidate":"SHOT","context_zone_candidate":"FINAL_THIRD","context_channel_candidate":"RIGHT_CHANNEL"},
            {"context_id":"b1","action_occurrence_eligible":True,"context_team_candidate":"TEAM_B","provider_action_family_candidate":"PASS","context_zone_candidate":"MIDDLE_THIRD","context_channel_candidate":"CENTRAL_CHANNEL"},
            {"context_id":"b2","action_occurrence_eligible":True,"context_team_candidate":"TEAM_B","provider_action_family_candidate":"TURNOVER","context_zone_candidate":"DEFENSIVE_THIRD","context_channel_candidate":"LEFT_CHANNEL"},
        ]
    }
    episode = {
        "episode_candidates": [{"episode_candidate_id":"aep_generic_001","time_layer_refs":["tl1","tl2","tl3"]}],
        "episode_time_layer_candidates": [
            {"episode_time_layer_candidate_id":"tl1","second_candidate":10.0,"context_refs":["a1","b1"],"eligible_action_zone_candidate_counts":{"DEFENSIVE_THIRD":1,"MIDDLE_THIRD":1},"same_time_unordered":True},
            {"episode_time_layer_candidate_id":"tl2","second_candidate":20.0,"context_refs":["a2","b2"],"eligible_action_zone_candidate_counts":{"MIDDLE_THIRD":1,"DEFENSIVE_THIRD":1},"same_time_unordered":True},
            {"episode_time_layer_candidate_id":"tl3","second_candidate":30.0,"context_refs":["a3"],"eligible_action_zone_candidate_counts":{"FINAL_THIRD":1},"same_time_unordered":False},
        ],
    }
    return features, episode, semantics


def test_p02_team_specific_zone_paths_remain_separate():
    features, episode, semantics = _p02_team_path_case()
    p02 = _progression_pool_p02(features, _p02_temporal(), episode, {}, semantics)
    by_team = {row["team_candidate"]: row for row in p02["p02_team_pool_items"]}
    a = by_team["TEAM_A"]["process_signature_fields"]
    b = by_team["TEAM_B"]["process_signature_fields"]
    assert a["team_specific_zone_station_path"] == ["DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD"]
    assert a["team_specific_zone_advancement_steps_candidate"] == 2
    assert b["team_specific_zone_station_path"] == ["MIDDLE_THIRD", "DEFENSIVE_THIRD"]
    assert b["team_specific_zone_advancement_steps_candidate"] == -1


def test_p02_team_zone_path_does_not_infer_metric_route_or_internal_order():
    features, episode, semantics = _p02_team_path_case()
    p02 = _progression_pool_p02(features, _p02_temporal(), episode, {}, semantics)
    by_team = {row["team_candidate"]: row for row in p02["p02_team_pool_items"]}
    for item in by_team.values():
        sig = item["process_signature_fields"]
        assert sig["team_specific_visible_path_length_proxy"] is None
        assert sig["team_specific_directness_proxy"] is None
        assert all(x["same_timestamp_transition"] is False for x in sig["team_specific_zone_transition_candidates"])
        assert all(x["transition_is_physical_trajectory_truth"] is False for x in sig["team_specific_zone_transition_candidates"])



def _p02_identities():
    return {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "teamc_A",
                "team_aliases_raw": ["TEAM_A"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "team_identity_candidate_id": "teamc_B",
                "team_aliases_raw": ["TEAM_B"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
        ]
    }


def _p02_team_consequence():
    return {
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "tacc_A",
                "period_candidate": "1",
                "anchor_start_candidate": "15.0",
                "team_identity_candidate_id": "teamc_A",
                "supporting_action_occurrence_candidate_ids": ["aoc_A"],
                "occurrence_visible_consequence_support": True,
                "terminal_outcome_support_visible": True,
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
            },
            {
                "trackable_action_consequence_candidate_id": "tacc_B",
                "period_candidate": "1",
                "anchor_start_candidate": "25.0",
                "team_identity_candidate_id": "teamc_B",
                "supporting_action_occurrence_candidate_ids": ["aoc_B"],
                "occurrence_visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
            },
        ]
    }


def test_p02_team_consequence_binding_uses_match_local_team_identity():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_team_consequence(),
        _p02_semantics(),
        _p02_identities(),
    )
    by_team = {row["team_candidate"]: row for row in p02["p02_team_pool_items"]}
    a = by_team["TEAM_A"]
    b = by_team["TEAM_B"]
    assert a["team_identity_candidate_id"] == "teamc_A"
    assert b["team_identity_candidate_id"] == "teamc_B"
    assert a["process_signature_fields"]["team_specific_occurrence_ids"] == ["aoc_A"]
    assert b["process_signature_fields"]["team_specific_occurrence_ids"] == ["aoc_B"]
    assert a["process_signature_fields"]["team_specific_opponent_follow_up_occurrence_ids"] == ["aoc_A"]
    assert b["process_signature_fields"]["team_specific_opponent_follow_up_occurrence_ids"] == []


def test_p02_team_consequence_missing_identity_degrades_without_cross_team_guess():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_team_consequence(),
        _p02_semantics(),
        {},
    )
    for item in p02["p02_team_pool_items"]:
        assert item["team_identity_candidate_id"] is None
        assert item["process_signature_fields"]["team_specific_occurrence_ids"] == []
        assert "team_identity_candidate_not_bound" in item["unresolved_refs"]


def test_p02_team_consequence_does_not_promote_opponent_followup_to_tactical_truth():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_team_consequence(),
        _p02_semantics(),
        _p02_identities(),
    )
    team_a = next(row for row in p02["p02_team_pool_items"] if row["team_candidate"] == "TEAM_A")
    sig = team_a["process_signature_fields"]
    assert sig["occurrence_consequence_binding_is_causal_truth"] is False
    assert sig["opponent_follow_up_is_tactical_response_truth"] is False



def _score_state_case():
    episode = {
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id": "tl_goal_a",
                "period_candidate": "1",
                "second_candidate": 25.0,
                "context_refs": ["goal_a_1", "goal_a_reflection"],
                "same_time_unordered": True,
            },
            {
                "episode_time_layer_candidate_id": "tl_goal_b",
                "period_candidate": "1",
                "second_candidate": 50.0,
                "context_refs": ["goal_b_1", "goal_b_player"],
                "same_time_unordered": True,
            },
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {
                "context_id": "goal_a_1",
                "row_nucleus_candidate_id": "rn_goal_a_1",
                "source_role": "TEAM",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_A",
            },
            {
                "context_id": "goal_a_reflection",
                "row_nucleus_candidate_id": "rn_goal_a_2",
                "source_role": "TEAM",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_A",
            },
            {
                "context_id": "goal_b_1",
                "row_nucleus_candidate_id": "rn_goal_b_1",
                "source_role": "TEAM",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_B",
            },
            {
                "context_id": "goal_b_player",
                "row_nucleus_candidate_id": "rn_goal_b_player",
                "source_role": "PLAYER",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_B",
            },
        ]
    }
    identities = {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "teamc_A",
                "team_aliases_raw": ["TEAM_A"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "team_identity_candidate_id": "teamc_B",
                "team_aliases_raw": ["TEAM_B"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
        ]
    }
    return episode, semantics, identities


def test_score_state_timeline_uses_reviewed_team_goal_outcomes_and_collapses_reflections():
    episode, semantics, identities = _score_state_case()
    timeline = _score_state_timeline_candidates(episode, semantics, identities)
    assert timeline["goal_score_change_candidate_count"] == 2
    assert timeline["collapsed_goal_reflection_count"] == 1
    assert timeline["validated_score_truth"] is False
    assert timeline["source_row_order_is_temporal_truth"] is False


def test_team_score_state_before_episode_start_is_team_relative_candidate():
    episode, semantics, identities = _score_state_case()
    timeline = _score_state_timeline_candidates(episode, semantics, identities)
    team_a = _team_score_state_at_episode_start(
        timeline,
        team_identity_candidate_id="teamc_A",
        period_candidate="1",
        start_second_candidate=40.0,
    )
    team_b = _team_score_state_at_episode_start(
        timeline,
        team_identity_candidate_id="teamc_B",
        period_candidate="1",
        start_second_candidate=40.0,
    )
    assert team_a["score_state_candidate"] == "LEADING"
    assert team_a["team_score_candidate"] == 1
    assert team_a["opponent_score_candidate"] == 0
    assert team_b["score_state_candidate"] == "TRAILING"


def test_score_state_can_use_correlated_player_team_and_opponent_gk_goal_reflections():
    episode = {
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id": "tl_goal",
                "period_candidate": "1",
                "second_candidate": 100.0,
                "context_refs": ["player_goal", "team_goal", "gk_conceded"],
                "same_time_unordered": True,
            }
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {
                "context_id": "player_goal",
                "row_nucleus_candidate_id": "rn_player_goal",
                "source_role": "PLAYER",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_A",
            },
            {
                "context_id": "team_goal",
                "row_nucleus_candidate_id": "rn_team_goal",
                "source_role": "TEAM",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "unknown",
            },
            {
                "context_id": "gk_conceded",
                "row_nucleus_candidate_id": "rn_gk_conceded",
                "source_role": "GOALKEEPER",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "OPPONENT_ACTION_REFERENCE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "REFERENCE_ONLY",
                "context_team_candidate": "TEAM_B",
            },
        ]
    }
    identities = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "teamc_A", "team_aliases_raw": ["TEAM_A"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
            {"team_identity_candidate_id": "teamc_B", "team_aliases_raw": ["TEAM_B"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
        ]
    }
    timeline = _score_state_timeline_candidates(episode, semantics, identities)

    assert timeline["status"] == "AVAILABLE"
    assert timeline["goal_score_change_candidate_count"] == 1
    assert timeline["cross_surface_goal_candidate_count"] == 1
    goal = timeline["goal_score_change_candidates"][0]
    assert goal["team_identity_candidate_id"] == "teamc_A"
    assert goal["cross_surface_reflection_used"] is True
    assert goal["cross_surface_reflection_is_independent_evidence"] is False
    assert goal["score_change_binding_bases"] == [
        "PLAYER_GOAL_PLUS_TEAM_REFLECTION_PLUS_OPPONENT_GK_CONCEDED"
    ]
    assert set(goal["supporting_context_refs"]) == {
        "player_goal", "team_goal", "gk_conceded"
    }


def test_player_goal_without_required_reflections_does_not_create_score_change():
    episode = {
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id": "tl_goal",
                "period_candidate": "1",
                "second_candidate": 100.0,
                "context_refs": ["player_goal"],
                "same_time_unordered": False,
            }
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {
                "context_id": "player_goal",
                "row_nucleus_candidate_id": "rn_player_goal",
                "source_role": "PLAYER",
                "provider_semantics_review_status": "REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate": "TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate": "GOAL",
                "provider_downstream_eligibility": "TERMINAL_OUTCOME_ONLY",
                "context_team_candidate": "TEAM_A",
            }
        ]
    }
    identities = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "teamc_A", "team_aliases_raw": ["TEAM_A"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
            {"team_identity_candidate_id": "teamc_B", "team_aliases_raw": ["TEAM_B"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
        ]
    }
    timeline = _score_state_timeline_candidates(episode, semantics, identities)

    assert timeline["status"] == "DEGRADED"
    assert timeline["goal_score_change_candidate_count"] == 0
    assert timeline["cross_surface_goal_candidate_count"] == 0
    assert timeline["cross_surface_goal_rejected_count"] == 1


def test_degraded_score_timeline_does_not_invent_level_state():
    state = _team_score_state_at_episode_start(
        {
            "status": "DEGRADED",
            "bound_team_identity_candidate_ids": ["teamc_A", "teamc_B"],
            "goal_score_change_candidate_count": 0,
            "goal_score_change_candidates": [],
        },
        team_identity_candidate_id="teamc_A",
        period_candidate="1",
        start_second_candidate=40.0,
    )
    assert state["status"] == "NOT_EVALUATED"
    assert state["score_state_candidate"] == "NOT_EVALUATED"
    assert state["reason"] == "score_timeline_not_available"


def test_goal_at_exact_episode_start_keeps_score_state_unresolved():
    episode, semantics, identities = _score_state_case()
    timeline = _score_state_timeline_candidates(episode, semantics, identities)
    state = _team_score_state_at_episode_start(
        timeline,
        team_identity_candidate_id="teamc_B",
        period_candidate="1",
        start_second_candidate=50.0,
    )
    assert state["status"] == "CONTEXT_UNRESOLVED"
    assert state["score_state_candidate"] == "UNRESOLVED"


def test_player_goal_surface_does_not_create_score_change():
    episode, semantics, identities = _score_state_case()
    timeline = _score_state_timeline_candidates(episode, semantics, identities)
    assert timeline["goal_score_change_candidate_count"] == 2
    assert all(
        "rn_goal_b_player" not in row["supporting_row_nucleus_refs"]
        for row in timeline["goal_score_change_candidates"]
    )



def _comparison_team_item(item_id: str, *, team_id: str = "teamc_A", period: str = "1", score_state: str = "LEVEL", start_zone: str = "MIDDLE_THIRD"):
    return {
        "pool_item_id": item_id,
        "team_identity_candidate_id": team_id,
        "episode_candidate_id": f"episode_{item_id}",
        "game_state": score_state,
        "comparison_context": {
            "period_candidate": period,
            "score_state_candidate": score_state,
        },
        "process_signature_fields": {
            "team_specific_start_zone": start_zone,
            "team_specific_zone_advancement_steps_candidate": 1,
            "team_episode_terminal_activity_candidate": "SHOT_ACTIVITY_VISIBLE",
        },
    }


def test_p02_comparison_population_requires_two_exact_context_members():
    one = _build_p02_comparison_populations([_comparison_team_item("p1")])
    assert one["comparison_population_count"] == 1
    assert one["eligible_comparison_population_count"] == 0
    assert one["comparison_populations"][0]["status"] == "INSUFFICIENT_COMPARABLE_MEMBERS"

    two = _build_p02_comparison_populations([
        _comparison_team_item("p1"),
        _comparison_team_item("p2"),
    ])
    assert two["eligible_comparison_population_count"] == 1
    population = two["comparison_populations"][0]
    assert population["status"] == "POPULATION_ELIGIBLE"
    assert population["member_count"] == 2
    assert population["outcome_admission_authority"] is False
    assert population["counterevidence_admission_authority"] is False


def test_p02_comparison_population_does_not_mix_score_state_or_start_zone():
    result = _build_p02_comparison_populations([
        _comparison_team_item("p1", score_state="LEVEL", start_zone="MIDDLE_THIRD"),
        _comparison_team_item("p2", score_state="TRAILING", start_zone="MIDDLE_THIRD"),
        _comparison_team_item("p3", score_state="LEVEL", start_zone="DEFENSIVE_THIRD"),
    ])
    assert result["comparison_population_count"] == 3
    assert result["eligible_comparison_population_count"] == 0


def test_p02_terminal_activity_candidate_is_not_process_outcome_truth():
    p02 = _progression_pool_p02(
        _p02_features(),
        _p02_temporal(),
        _p02_episode(),
        _p02_team_consequence(),
        _p02_semantics(),
        _p02_identities(),
    )
    for item in p02["p02_team_pool_items"]:
        sig = item["process_signature_fields"]
        assert sig["team_episode_terminal_activity_is_process_outcome_truth"] is False



def _sequence_process_unit_case():
    sequence = {
        "visible_action_time_layer_candidates": [
            {
                "visible_action_time_layer_candidate_id": "vl1",
                "start_candidate": 10.0,
                "trackable_action_trace_candidate_ids": ["tr1"],
            },
            {
                "visible_action_time_layer_candidate_id": "vl2",
                "start_candidate": 20.0,
                "trackable_action_trace_candidate_ids": ["tr2a", "tr2b"],
            },
            {
                "visible_action_time_layer_candidate_id": "vl3",
                "start_candidate": 30.0,
                "trackable_action_trace_candidate_ids": ["tr3"],
            },
            {
                "visible_action_time_layer_candidate_id": "vl4",
                "start_candidate": 40.0,
                "trackable_action_trace_candidate_ids": ["tr4"],
            },
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id": "vasq_1",
                "team_identity_candidate_id": "teamc_A",
                "period_candidate": "1",
                "start_time_candidate": 10.0,
                "end_time_candidate": 40.0,
                "duration_candidate_seconds": 30.0,
                "time_layer_candidate_ids": ["vl1", "vl2", "vl3", "vl4"],
                "time_layer_count": 4,
                "trackable_action_trace_candidate_ids": ["tr1", "tr2a", "tr2b", "tr3", "tr4"],
                "trace_candidate_count": 5,
                "action_family_counts": {"PASS": 3, "DRIBBLE": 1, "SHOT": 1},
                "consequence_candidate_counts": {"FOLLOW_UP_VISIBLE": 3},
                "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate": "PERIOD_START",
                "end_reason_candidate": "TERMINAL_OUTCOME_SUPPORT_BOUNDARY",
            }
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id":"tr1","pos_x_candidate":10.0,"pos_y_candidate":10.0,"coordinate_evidence_status":"VISIBLE_COORDINATE_CANDIDATE"},
            {"trackable_action_trace_candidate_id":"tr2a","pos_x_candidate":15.0,"pos_y_candidate":10.0,"coordinate_evidence_status":"VISIBLE_COORDINATE_CANDIDATE"},
            {"trackable_action_trace_candidate_id":"tr2b","pos_x_candidate":16.0,"pos_y_candidate":11.0,"coordinate_evidence_status":"VISIBLE_COORDINATE_CANDIDATE"},
            {"trackable_action_trace_candidate_id":"tr3","pos_x_candidate":20.0,"pos_y_candidate":10.0,"coordinate_evidence_status":"VISIBLE_COORDINATE_CANDIDATE"},
            {"trackable_action_trace_candidate_id":"tr4","pos_x_candidate":20.0,"pos_y_candidate":20.0,"coordinate_evidence_status":"VISIBLE_COORDINATE_CANDIDATE"},
        ]
    }
    score_timeline = {
        "bound_team_identity_candidate_ids": ["teamc_A", "teamc_B"],
        "goal_score_change_candidates": [],
    }
    return sequence, trace, score_timeline


def test_p02_sequence_process_unit_uses_only_single_trace_coordinate_layers():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    assert out["p02_process_unit_candidate_count"] == 1
    unit = out["p02_process_unit_candidates"][0]
    assert unit["coordinate_station_count"] == 3
    assert unit["ambiguous_coordinate_layer_count"] == 1
    assert [x["trackable_action_trace_candidate_id"] for x in unit["coordinate_stations"]] == ["tr1", "tr3", "tr4"]


def test_p02_sequence_process_unit_geometric_path_is_provider_coordinate_proxy_only():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    unit = _build_p02_sequence_process_units(sequence, trace, score_timeline)["p02_process_unit_candidates"][0]
    assert unit["provider_coordinate_path_length_proxy"] == 20.0
    assert unit["provider_coordinate_raw_x_displacement"] == 10.0
    assert unit["provider_coordinate_raw_y_displacement"] == 10.0
    assert round(unit["geometric_directness_proxy"], 6) == 0.707107
    assert unit["metric_distance_metres"] is None
    assert unit["goalward_progression"] is None
    assert unit["attacking_direction"] == "NOT_EVALUATED"
    assert unit["coordinate_is_tracking"] is False
    assert unit["provider_coordinate_path_is_physical_trajectory_truth"] is False


def test_p02_sequence_terminal_boundary_remains_visible_activity_candidate():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    unit = _build_p02_sequence_process_units(sequence, trace, score_timeline)["p02_process_unit_candidates"][0]
    assert unit["team_episode_terminal_activity_candidate"] == "TERMINAL_SUPPORT_BOUNDARY_VISIBLE"
    assert unit["visible_exit_class_candidate"] == "TERMINAL_SUPPORT_BOUNDARY_VISIBLE"
    assert unit["visible_exit_zone_candidate"] == unit["process_end_zone_candidate"]
    assert unit["visible_exit_access_state_candidate"] == unit["advanced_access_state_candidate"]
    assert unit["visible_exit_class_is_failure_truth"] is False
    assert unit["visible_exit_class_is_causal_truth"] is False
    assert unit["visible_exit_class_is_process_outcome_truth"] is False
    assert unit["terminal_activity_is_process_outcome_truth"] is False
    assert unit["comparison_candidate_ready"] is False


def test_p02_exact_handover_links_first_visible_opponent_process_without_causal_promotion():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    first = sequence["visible_action_sequence_candidates"][0]
    first["end_reason_candidate"] = "TEAM_HANDOVER_BOUNDARY"
    first["end_boundary_time_candidate"] = 45.0
    first["next_team_identity_candidate_id"] = "teamc_B"
    sequence["visible_action_time_layer_candidates"].append({
        "visible_action_time_layer_candidate_id": "vl5",
        "start_candidate": 45.0,
        "trackable_action_trace_candidate_ids": ["tr5"],
    })
    trace["trackable_action_trace_candidates"].append({
        "trackable_action_trace_candidate_id": "tr5",
        "pos_x_candidate": 30.0,
        "pos_y_candidate": 20.0,
        "coordinate_evidence_status": "VISIBLE_COORDINATE_CANDIDATE",
    })
    sequence["visible_action_sequence_candidates"].append({
        "visible_action_sequence_candidate_id": "vasq_2",
        "team_identity_candidate_id": "teamc_B",
        "period_candidate": "1",
        "start_time_candidate": 45.0,
        "end_time_candidate": 45.0,
        "end_boundary_time_candidate": 50.0,
        "duration_candidate_seconds": 0.0,
        "time_layer_candidate_ids": ["vl5"],
        "time_layer_count": 1,
        "trackable_action_trace_candidate_ids": ["tr5"],
        "trace_candidate_count": 1,
        "action_family_counts": {"PASS": 1},
        "consequence_candidate_counts": {},
        "sequence_record_status": "PASS_SINGLE_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "start_reason_candidate": "AFTER_TEAM_HANDOVER",
        "end_reason_candidate": "TIME_GAP_BOUNDARY",
    })
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    by_source = {row["source_visible_action_sequence_candidate_id"]: row for row in out["p02_process_unit_candidates"]}
    source = by_source["vasq_1"]
    target = by_source["vasq_2"]
    response = source["opponent_response_candidate"]
    assert response["status"] == "EXACT_HANDOVER_BOUNDARY_LINKED"
    assert response["source_process_unit_candidate_id"] == target["p02_process_unit_candidate_id"]
    assert response["team_identity_candidate_id"] == "teamc_B"
    assert source["opponent_response_is_causal_truth"] is False
    assert source["opponent_response_is_tactical_response_truth"] is False
    assert source["opponent_response_is_counterattack_truth"] is False
    assert source["opponent_response_adds_independent_support"] is False
    profile = source["visible_variant_outcome_profile"]
    assert profile["opponent_response_status"] == "EXACT_HANDOVER_BOUNDARY_LINKED"
    assert profile["success_failure_label"] == "NOT_ASSIGNED"
    assert profile["profile_is_process_outcome_truth"] is False
    assert profile["profile_is_tactical_quality_truth"] is False
    assert profile["profile_is_causal_truth"] is False


def test_p02_handover_does_not_guess_nearest_opponent_process():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    first = sequence["visible_action_sequence_candidates"][0]
    first["end_reason_candidate"] = "TEAM_HANDOVER_BOUNDARY"
    first["end_boundary_time_candidate"] = 45.0
    first["next_team_identity_candidate_id"] = "teamc_B"
    sequence["visible_action_time_layer_candidates"].append({
        "visible_action_time_layer_candidate_id": "vl5",
        "start_candidate": 46.0,
        "trackable_action_trace_candidate_ids": ["tr5"],
    })
    trace["trackable_action_trace_candidates"].append({
        "trackable_action_trace_candidate_id": "tr5",
        "pos_x_candidate": 30.0,
        "pos_y_candidate": 20.0,
        "coordinate_evidence_status": "VISIBLE_COORDINATE_CANDIDATE",
    })
    sequence["visible_action_sequence_candidates"].append({
        "visible_action_sequence_candidate_id": "vasq_2",
        "team_identity_candidate_id": "teamc_B",
        "period_candidate": "1",
        "start_time_candidate": 46.0,
        "end_time_candidate": 46.0,
        "duration_candidate_seconds": 0.0,
        "time_layer_candidate_ids": ["vl5"],
        "time_layer_count": 1,
        "trackable_action_trace_candidate_ids": ["tr5"],
        "trace_candidate_count": 1,
        "action_family_counts": {"PASS": 1},
        "consequence_candidate_counts": {},
        "sequence_record_status": "PASS_SINGLE_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "start_reason_candidate": "AFTER_TEAM_HANDOVER",
        "end_reason_candidate": "TIME_GAP_BOUNDARY",
    })
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    source = next(row for row in out["p02_process_unit_candidates"] if row["source_visible_action_sequence_candidate_id"] == "vasq_1")
    assert source["opponent_response_candidate"]["status"] == "UNRESOLVED_HANDOVER_TARGET"



def test_p02_turnover_response_summary_uses_explicit_denominator_and_no_causal_promotion():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    first = sequence["visible_action_sequence_candidates"][0]
    first["action_family_counts"]["TURNOVER"] = 1
    first["end_reason_candidate"] = "TEAM_HANDOVER_BOUNDARY"
    first["end_boundary_time_candidate"] = 45.0
    first["next_team_identity_candidate_id"] = "teamc_B"
    sequence["visible_action_time_layer_candidates"].append({
        "visible_action_time_layer_candidate_id": "vl5",
        "start_candidate": 45.0,
        "trackable_action_trace_candidate_ids": ["tr5"],
    })
    trace["trackable_action_trace_candidates"].append({
        "trackable_action_trace_candidate_id": "tr5",
        "pos_x_candidate": 30.0,
        "pos_y_candidate": 20.0,
        "coordinate_evidence_status": "VISIBLE_COORDINATE_CANDIDATE",
    })
    sequence["visible_action_sequence_candidates"].append({
        "visible_action_sequence_candidate_id": "vasq_2",
        "team_identity_candidate_id": "teamc_B",
        "period_candidate": "1",
        "start_time_candidate": 45.0,
        "end_time_candidate": 45.0,
        "end_boundary_time_candidate": 50.0,
        "duration_candidate_seconds": 0.0,
        "time_layer_candidate_ids": ["vl5"],
        "time_layer_count": 1,
        "trackable_action_trace_candidate_ids": ["tr5"],
        "trace_candidate_count": 1,
        "action_family_counts": {"PASS": 1},
        "consequence_candidate_counts": {},
        "sequence_record_status": "PASS_SINGLE_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "start_reason_candidate": "AFTER_TEAM_HANDOVER",
        "end_reason_candidate": "TIME_GAP_BOUNDARY",
    })
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    by_team = {row["team_identity_candidate_id"]: row for row in out["opponent_response_summary_by_team"]}
    summary = by_team["teamc_A"]
    assert summary["exact_handover_linked_count"] == 1
    assert summary["turnover_process_unit_count"] == 1
    assert summary["turnover_handover_linked_count"] == 1
    assert summary["turnover_handover_opponent_access_unresolved_count"] == 1
    assert summary["handover_is_turnover_truth"] is False
    assert summary["opponent_response_is_causal_truth"] is False
    assert summary["opponent_advanced_access_is_dangerous_transition_truth"] is False
    assert summary["counts_are_independent_support_votes"] is False
    source = next(
        row for row in out["p02_process_unit_candidates"]
        if row["source_visible_action_sequence_candidate_id"] == "vasq_1"
    )
    profile = source["visible_variant_outcome_profile"]
    assert profile["turnover_visible"] is True
    assert profile["opponent_response_status"] == "EXACT_HANDOVER_BOUNDARY_LINKED"
    assert profile["success_failure_label"] == "NOT_ASSIGNED"


def test_p02_partial_order_signature_preserves_layer_multisets_without_internal_order():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["partial_order_process_signature_id"].startswith("p02_posig_")
    assert len(unit["action_layer_signature"]) == 4
    assert all(row["same_timestamp_internal_ordering_allowed"] is False for row in unit["action_layer_signature"])


def test_p02_recurrence_groups_exact_partial_order_signatures_without_tactical_truth():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    duplicate = dict(sequence["visible_action_sequence_candidates"][0])
    duplicate["visible_action_sequence_candidate_id"] = "vasq_2"
    duplicate["start_time_candidate"] = 50.0
    duplicate["end_time_candidate"] = 80.0
    sequence["visible_action_sequence_candidates"].append(duplicate)

    out = _build_p02_sequence_process_units(sequence, trace, score_timeline)
    repeated = next(
        row for row in out["partial_order_signature_groups"]
        if row["recurrence_status"] == "REPEATED_VISIBLE_SIGNATURE"
    )
    assert repeated["member_count"] == 2
    assert repeated["recurrence_is_causality"] is False
    assert repeated["recurrence_is_tactical_truth"] is False



def _sequence_evidence_atoms():
    return {
        "evidence_atoms": [
            {"evidence_atom_id":"ea1","zone_candidate":"OWN_HALF"},
            {"evidence_atom_id":"ea3","zone_candidate":"FINAL_THIRD"},
            {"evidence_atom_id":"ea4","zone_candidate":"PENALTY_AREA"},
        ]
    }


def _sequence_trace_with_zone_lineage():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    by_id = {row["trackable_action_trace_candidate_id"]: row for row in trace["trackable_action_trace_candidates"]}
    by_id["tr1"]["supporting_evidence_atom_ids"] = ["ea1"]
    by_id["tr3"]["supporting_evidence_atom_ids"] = ["ea3"]
    by_id["tr4"]["supporting_evidence_atom_ids"] = ["ea4"]
    return sequence, trace, score_timeline, _sequence_evidence_atoms()


def test_p02_process_unit_semantic_zone_path_uses_trace_evidence_atom_lineage():
    sequence, trace, score_timeline, evidence = _sequence_trace_with_zone_lineage()
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline, evidence)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["semantic_zone_path_candidate"] == ["OWN_HALF", "FINAL_THIRD", "PENALTY_AREA"]
    assert unit["process_start_zone_candidate"] == "OWN_HALF"
    assert unit["process_end_zone_candidate"] == "PENALTY_AREA"
    assert unit["process_zone_basis"] == "EVIDENCE_ATOM_SEMANTIC_ZONE_CANDIDATE"
    assert all(row["coordinate_zone_truth"] is False for row in unit["semantic_zone_stations"])


def test_p02_process_unit_ambiguous_semantic_zone_layer_is_not_forced():
    sequence, trace, score_timeline, evidence = _sequence_trace_with_zone_lineage()
    evidence["evidence_atoms"].append({"evidence_atom_id":"ea1b","zone_candidate":"OPPONENT_HALF"})
    by_id = {row["trackable_action_trace_candidate_id"]: row for row in trace["trackable_action_trace_candidates"]}
    by_id["tr1"]["supporting_evidence_atom_ids"] = ["ea1", "ea1b"]
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline, evidence)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["ambiguous_semantic_zone_layer_count"] >= 1
    assert unit["process_start_zone_candidate"] == "FINAL_THIRD"



def _process_unit_for_comparison(
    unit_id: str,
    *,
    signature: str = "sig_a",
    zone_path=None,
    end_zone: str = "FINAL_THIRD",
    terminal: str = "TEAM_HANDOVER_BOUNDARY_VISIBLE",
):
    return {
        "p02_process_unit_candidate_id": unit_id,
        "team_identity_candidate_id": "teamc_A",
        "period_candidate": "1",
        "score_state_candidate": "LEVEL",
        "process_start_zone_candidate": "OWN_HALF",
        "process_end_zone_candidate": end_zone,
        "partial_order_process_signature_id": signature,
        "semantic_zone_path_candidate": list(zone_path or ["OWN_HALF", "FINAL_THIRD"]),
        "team_episode_terminal_activity_candidate": terminal,
    }


def test_p02_process_unit_variant_population_groups_exact_context_and_separates_variants():
    process_units = {
        "p02_process_unit_candidates": [
            _process_unit_for_comparison("u1", signature="sig_a", zone_path=["OWN_HALF", "FINAL_THIRD"]),
            _process_unit_for_comparison("u2", signature="sig_b", zone_path=["OWN_HALF", "PENALTY_AREA"], end_zone="PENALTY_AREA"),
        ]
    }
    out = _build_p02_process_unit_comparison_populations(process_units)
    assert out["eligible_process_unit_comparison_population_count"] == 1
    population = out["process_unit_comparison_populations"][0]
    assert population["member_count"] == 2
    assert population["variant_family_count"] == 2
    assert population["visible_branch_divergence_candidate"] is True
    assert population["branch_divergence_is_causality"] is False
    assert population["branch_divergence_is_tactical_truth"] is False
    assert population["counterevidence_admission_authority"] is False


def test_p02_process_unit_same_variant_recurrence_does_not_create_branch_divergence():
    process_units = {
        "p02_process_unit_candidates": [
            _process_unit_for_comparison("u1"),
            _process_unit_for_comparison("u2"),
        ]
    }
    out = _build_p02_process_unit_comparison_populations(process_units)
    population = out["process_unit_comparison_populations"][0]
    assert population["variant_family_count"] == 1
    assert population["visible_branch_divergence_candidate"] is False
    assert population["outcome_relation_admitted"] is False
    assert out["counterevidence_candidates"] == []



def _complete_zone_process_case():
    sequence, trace, score_timeline = _sequence_process_unit_case()
    by_id = {row["trackable_action_trace_candidate_id"]: row for row in trace["trackable_action_trace_candidates"]}
    by_id["tr1"]["supporting_evidence_atom_ids"] = ["ea1"]
    by_id["tr2a"]["supporting_evidence_atom_ids"] = ["ea2a"]
    by_id["tr2b"]["supporting_evidence_atom_ids"] = ["ea2b"]
    by_id["tr3"]["supporting_evidence_atom_ids"] = ["ea3"]
    by_id["tr4"]["supporting_evidence_atom_ids"] = ["ea4"]
    evidence = {
        "evidence_atoms": [
            {"evidence_atom_id":"ea1","row_nucleus_candidate_id":"rn1"},
            {"evidence_atom_id":"ea2a","row_nucleus_candidate_id":"rn2a"},
            {"evidence_atom_id":"ea2b","row_nucleus_candidate_id":"rn2b"},
            {"evidence_atom_id":"ea3","row_nucleus_candidate_id":"rn3"},
            {"evidence_atom_id":"ea4","row_nucleus_candidate_id":"rn4"},
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {"row_nucleus_candidate_id":"rn1","context_zone_candidate":"OWN_HALF"},
            {"row_nucleus_candidate_id":"rn2a","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn2b","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn3","context_zone_candidate":"FINAL_THIRD"},
            {"row_nucleus_candidate_id":"rn4","context_zone_candidate":"FINAL_THIRD"},
        ]
    }
    return sequence, trace, score_timeline, evidence, semantics


def test_p02_advanced_access_resolves_when_all_time_layers_have_single_zone_state():
    sequence, trace, score_timeline, evidence, semantics = _complete_zone_process_case()
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline, evidence, semantics)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["semantic_zone_layer_coverage_complete"] is True
    assert unit["semantic_zone_path_candidate"] == ["OWN_HALF", "MIDDLE_THIRD", "FINAL_THIRD"]
    assert unit["advanced_access_state_candidate"] == "ADVANCED_ACCESS_VISIBLE"
    assert unit["advanced_access_state_is_tactical_truth"] is False
    profile = unit["visible_variant_outcome_profile"]
    assert profile["target_relative_variant_state_candidate"] == "TARGET_OBSERVED_VISIBLE"
    assert profile["success_failure_label"] == "NOT_ASSIGNED"
    assert profile["target_relative_state_is_general_attack_success_failure"] is False


def test_p02_advanced_access_unresolved_when_one_layer_has_conflicting_zones():
    sequence, trace, score_timeline, evidence, semantics = _complete_zone_process_case()
    semantics["context_action_semantic_records"][2]["context_zone_candidate"] = "FINAL_THIRD"
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline, evidence, semantics)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["semantic_zone_layer_coverage_complete"] is False
    assert unit["ambiguous_semantic_zone_layer_count"] >= 1
    assert unit["advanced_access_state_candidate"] == "UNRESOLVED"
    profile = unit["visible_variant_outcome_profile"]
    assert profile["target_relative_variant_state_candidate"] == "TARGET_STATE_UNRESOLVED"
    assert profile["success_failure_label"] == "NOT_ASSIGNED"



def test_p02_target_not_observed_state_requires_complete_admitted_zone_path():
    sequence, trace, score_timeline, evidence, semantics = _complete_zone_process_case()
    for row in semantics["context_action_semantic_records"]:
        if row["row_nucleus_candidate_id"] in {"rn3", "rn4"}:
            row["context_zone_candidate"] = "MIDDLE_THIRD"
    out = _build_p02_sequence_process_units(sequence, trace, score_timeline, evidence, semantics)
    unit = out["p02_process_unit_candidates"][0]
    assert unit["semantic_zone_layer_coverage_complete"] is True
    assert unit["advanced_access_state_candidate"] == "NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH"
    profile = unit["visible_variant_outcome_profile"]
    assert profile["target_relative_variant_state_candidate"] == "TARGET_NOT_OBSERVED_IN_COMPLETE_ADMITTED_PATH"
    assert profile["target_relative_state_is_general_attack_success_failure"] is False
    assert profile["target_relative_state_is_tactical_quality_truth"] is False
    assert profile["success_failure_label"] == "NOT_ASSIGNED"



def test_p02_opposite_advanced_access_emits_comparison_intent_without_independence_admission():
    reference = _process_unit_for_comparison("u_ref")
    candidate = _process_unit_for_comparison("u_cand")
    reference["advanced_access_state_candidate"] = "ADVANCED_ACCESS_VISIBLE"
    candidate["advanced_access_state_candidate"] = "NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH"
    reference["source_visible_action_sequence_candidate_id"] = "vasq_ref"
    candidate["source_visible_action_sequence_candidate_id"] = "vasq_cand"

    out = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    assert out["opposite_outcome_comparison_candidate_count"] == 1
    comparison = out["counterevidence_candidates"][0]
    assert comparison["outcome_relation"] == "OPPOSITE"
    assert comparison["counterevidence_admission_ready"] is False
    assert comparison["independence_group"] is None
    assert comparison["reference_independence_group"] is None


def test_p02_opposite_advanced_access_reaches_fusion_but_stays_unresolved_without_independence():
    reference = _process_unit_for_comparison("u_ref")
    candidate = _process_unit_for_comparison("u_cand")
    reference["advanced_access_state_candidate"] = "ADVANCED_ACCESS_VISIBLE"
    candidate["advanced_access_state_candidate"] = "NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH"
    reference["source_visible_action_sequence_candidate_id"] = "vasq_ref"
    candidate["source_visible_action_sequence_candidate_id"] = "vasq_cand"

    comparisons = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    comparison = comparisons["counterevidence_candidates"][0]

    packet = {
        "packet_id": "p02_progression_comparison_packet",
        "packet_family": "progression",
        "input_features": ["advanced_access_state_candidate"],
        "input_windows": ["p02_exact_context_population"],
        "input_sequences": ["vasq_ref", "vasq_cand"],
        "input_metrics": [],
        "supporting_signals": ["p02_visible_progression_context"],
        "contradicting_signals": [comparison],
        "claim_ceiling": "P02_COMPARISON_CANDIDATE_ONLY",
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }
    fusion = fuse_packet(packet)
    assert fusion["contradiction_signal_count"] == 0
    assert fusion["unresolved_counterevidence_count"] == 1
    row = next(
        row for row in fusion["relation_records"]
        if row["signal_ref"] == comparison["signal_id"]
    )
    assert row["comparison_status"] == "ELIGIBLE"
    assert row["counterevidence_class"] == "UNRESOLVED"
    assert row["counterevidence_admission_reason"] == "counterevidence_dependency_not_admitted"


def test_p02_same_advanced_access_state_is_same_relation_not_counterevidence():
    reference = _process_unit_for_comparison("u_ref")
    candidate = _process_unit_for_comparison("u_cand")
    reference["advanced_access_state_candidate"] = "ADVANCED_ACCESS_VISIBLE"
    candidate["advanced_access_state_candidate"] = "ADVANCED_ACCESS_VISIBLE"
    reference["source_visible_action_sequence_candidate_id"] = "vasq_ref"
    candidate["source_visible_action_sequence_candidate_id"] = "vasq_cand"
    out = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    assert out["opposite_outcome_comparison_candidate_count"] == 0
    assert out["pairwise_comparison_candidates"][0]["outcome_relation"] == "SAME"











def _independent_process_unit(
    unit_id: str,
    *,
    sequence_id: str,
    trace_ids,
    start: float,
    end: float,
    advanced_access: str,
):
    row = _process_unit_for_comparison(unit_id)
    row["source_visible_action_sequence_candidate_id"] = sequence_id
    row["source_trackable_action_trace_candidate_ids"] = list(trace_ids)
    row["start_time_candidate"] = start
    row["end_time_candidate"] = end
    row["advanced_access_state_candidate"] = advanced_access
    return row


def test_p02_disjoint_nonoverlapping_process_units_admit_evidence_unit_independence():
    reference = _independent_process_unit(
        "u_ref",
        sequence_id="vasq_ref",
        trace_ids=["tr_ref_1", "tr_ref_2"],
        start=10.0,
        end=20.0,
        advanced_access="ADVANCED_ACCESS_VISIBLE",
    )
    candidate = _independent_process_unit(
        "u_cand",
        sequence_id="vasq_cand",
        trace_ids=["tr_cand_1", "tr_cand_2"],
        start=30.0,
        end=40.0,
        advanced_access="NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH",
    )
    comparisons = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    comparison = comparisons["counterevidence_candidates"][0]
    assert comparison["outcome_relation"] == "OPPOSITE"
    assert comparison["independence_admission_status"] == "ADMITTED"
    assert comparison["counterevidence_admission_ready"] is True
    assert comparison["statistical_independence_claimed"] is False

    packet = {
        "packet_id": "p02_independent_progression_comparison_packet",
        "packet_family": "progression",
        "input_features": ["advanced_access_state_candidate"],
        "input_windows": ["p02_exact_context_population"],
        "input_sequences": ["vasq_ref", "vasq_cand"],
        "input_metrics": [],
        "supporting_signals": ["p02_visible_progression_context"],
        "contradicting_signals": [comparison],
        "claim_ceiling": "P02_COMPARISON_CANDIDATE_ONLY",
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }
    fusion = fuse_packet(packet)
    assert fusion["contradiction_signal_count"] == 1
    assert fusion["admitted_counterevidence_count"] == 1
    row = next(
        row for row in fusion["relation_records"]
        if row["signal_ref"] == comparison["signal_id"]
    )
    assert row["counterevidence_class"] == "COUNTEREVIDENCE"
    assert row["independence_admission_status"] == "ADMITTED"


def test_p02_shared_trace_root_blocks_independence_admission():
    reference = _independent_process_unit(
        "u_ref",
        sequence_id="vasq_ref",
        trace_ids=["tr_shared", "tr_ref_2"],
        start=10.0,
        end=20.0,
        advanced_access="ADVANCED_ACCESS_VISIBLE",
    )
    candidate = _independent_process_unit(
        "u_cand",
        sequence_id="vasq_cand",
        trace_ids=["tr_shared", "tr_cand_2"],
        start=30.0,
        end=40.0,
        advanced_access="NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH",
    )
    comparisons = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    comparison = comparisons["counterevidence_candidates"][0]
    assert comparison["independence_admission_status"] == "NOT_ADMITTED"
    assert "trace_roots_overlap" in comparison["independence_admission_basis"]
    assert comparison["counterevidence_admission_ready"] is False


def test_p02_overlapping_time_intervals_block_independence_admission():
    reference = _independent_process_unit(
        "u_ref",
        sequence_id="vasq_ref",
        trace_ids=["tr_ref_1"],
        start=10.0,
        end=25.0,
        advanced_access="ADVANCED_ACCESS_VISIBLE",
    )
    candidate = _independent_process_unit(
        "u_cand",
        sequence_id="vasq_cand",
        trace_ids=["tr_cand_1"],
        start=20.0,
        end=30.0,
        advanced_access="NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH",
    )
    comparisons = _build_p02_process_unit_comparison_populations({
        "p02_process_unit_candidates": [reference, candidate]
    })
    comparison = comparisons["counterevidence_candidates"][0]
    assert comparison["independence_admission_status"] == "NOT_ADMITTED"
    assert "admitted_time_intervals_overlap" in comparison["independence_admission_basis"]
    assert comparison["counterevidence_admission_ready"] is False



def _p02_c4_bridge_case():
    identities = {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "teamc_A",
                "team_aliases_raw": ["TEAM_A"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
            {
                "team_identity_candidate_id": "teamc_B",
                "team_aliases_raw": ["TEAM_B"],
                "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            },
        ]
    }
    visible_sequence = {
        "visible_action_time_layer_candidates": [
            {
                "visible_action_time_layer_candidate_id": "r1",
                "start_candidate": 10.0,
                "trackable_action_trace_candidate_ids": ["tr_r1"],
                "action_family_counts": {"PASS": 1},
            },
            {
                "visible_action_time_layer_candidate_id": "r2",
                "start_candidate": 20.0,
                "trackable_action_trace_candidate_ids": ["tr_r2"],
                "action_family_counts": {"PASS": 1},
            },
            {
                "visible_action_time_layer_candidate_id": "c1",
                "start_candidate": 30.0,
                "trackable_action_trace_candidate_ids": ["tr_c1"],
                "action_family_counts": {"PASS": 1},
            },
            {
                "visible_action_time_layer_candidate_id": "c2",
                "start_candidate": 40.0,
                "trackable_action_trace_candidate_ids": ["tr_c2"],
                "action_family_counts": {"PASS": 1},
            },
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id": "vasq_ref",
                "team_identity_candidate_id": "teamc_A",
                "period_candidate": "1",
                "start_time_candidate": 10.0,
                "end_time_candidate": 20.0,
                "duration_candidate_seconds": 10.0,
                "time_layer_candidate_ids": ["r1", "r2"],
                "time_layer_count": 2,
                "trackable_action_trace_candidate_ids": ["tr_r1", "tr_r2"],
                "trace_candidate_count": 2,
                "action_family_counts": {"PASS": 2},
                "consequence_candidate_counts": {},
                "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate": "PERIOD_START",
                "end_reason_candidate": "TEAM_HANDOVER_BOUNDARY",
            },
            {
                "visible_action_sequence_candidate_id": "vasq_cand",
                "team_identity_candidate_id": "teamc_A",
                "period_candidate": "1",
                "start_time_candidate": 30.0,
                "end_time_candidate": 40.0,
                "duration_candidate_seconds": 10.0,
                "time_layer_candidate_ids": ["c1", "c2"],
                "time_layer_count": 2,
                "trackable_action_trace_candidate_ids": ["tr_c1", "tr_c2"],
                "trace_candidate_count": 2,
                "action_family_counts": {"PASS": 2},
                "consequence_candidate_counts": {},
                "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate": "TIME_GAP_BOUNDARY",
                "end_reason_candidate": "TEAM_HANDOVER_BOUNDARY",
            },
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id":"tr_r1","supporting_evidence_atom_ids":["ea_r1"]},
            {"trackable_action_trace_candidate_id":"tr_r2","supporting_evidence_atom_ids":["ea_r2"]},
            {"trackable_action_trace_candidate_id":"tr_c1","supporting_evidence_atom_ids":["ea_c1"]},
            {"trackable_action_trace_candidate_id":"tr_c2","supporting_evidence_atom_ids":["ea_c2"]},
        ]
    }
    evidence = {
        "evidence_atoms": [
            {"evidence_atom_id":"ea_r1","row_nucleus_candidate_id":"rn_r1"},
            {"evidence_atom_id":"ea_r2","row_nucleus_candidate_id":"rn_r2"},
            {"evidence_atom_id":"ea_c1","row_nucleus_candidate_id":"rn_c1"},
            {"evidence_atom_id":"ea_c2","row_nucleus_candidate_id":"rn_c2"},
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {"row_nucleus_candidate_id":"rn_r1","context_zone_candidate":"OWN_HALF"},
            {"row_nucleus_candidate_id":"rn_r2","context_zone_candidate":"FINAL_THIRD"},
            {"row_nucleus_candidate_id":"rn_c1","context_zone_candidate":"OWN_HALF"},
            {"row_nucleus_candidate_id":"rn_c2","context_zone_candidate":"MIDDLE_THIRD"},
            {
                "context_id":"goal_after_all_sequences",
                "row_nucleus_candidate_id":"rn_goal_after_all_sequences",
                "source_role":"TEAM",
                "provider_semantics_review_status":"REVIEWED_CANDIDATE",
                "provider_semantic_role_candidate":"TERMINAL_OUTCOME_CANDIDATE",
                "provider_terminal_outcome_candidate":"GOAL",
                "provider_downstream_eligibility":"TERMINAL_OUTCOME_ONLY",
                "context_team_candidate":"TEAM_A",
            },
        ]
    }
    episode = {
        "episode_time_layer_candidates": [
            {
                "episode_time_layer_candidate_id":"tl_goal_after_all_sequences",
                "period_candidate":"1",
                "second_candidate":120.0,
                "context_refs":["goal_after_all_sequences"],
                "same_time_unordered":False,
            }
        ]
    }
    return episode, identities, visible_sequence, trace, evidence, semantics


def test_p02_independence_admitted_comparison_builds_c4_packet_and_reaches_fusion():
    episode, identities, visible_sequence, trace, evidence, semantics = _p02_c4_bridge_case()
    p02 = _progression_pool_p02(
        {},
        {},
        episode,
        {},
        semantics,
        identities,
        visible_sequence,
        trace,
        evidence,
    )
    assert p02["p02_c4_packet_candidate_count"] == 1
    candidate = p02["p02_c4_packet_candidates"][0]
    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["contradicting_signal_count"] == 1

    fusion = fuse_packet(packet)
    assert fusion["contradiction_signal_count"] == 1
    assert fusion["admitted_counterevidence_count"] == 1
    comparison = next(
        row for row in fusion["relation_records"]
        if row["relation_type"] == "CONTRADICTS"
    )
    assert comparison["counterevidence_class"] == "COUNTEREVIDENCE"
    assert comparison["independence_admission_status"] == "ADMITTED"


def test_p02_professional_finding_target_is_exact_context_bounded_and_not_success_failure_truth():
    episode, identities, visible_sequence, trace, evidence, semantics = _p02_c4_bridge_case()
    p02 = _progression_pool_p02(
        {},
        {},
        episode,
        {},
        semantics,
        identities,
        visible_sequence,
        trace,
        evidence,
    )
    assert p02["professional_finding_target_candidate_count"] == 1
    finding = p02["professional_finding_target_candidates"][0]
    assert finding["finding_status"] == "REVIEW_REQUIRED"
    assert finding["target_estimand"] == "ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_SEMANTIC_ZONE_PATH"
    assert finding["resolved_target_state_denominator"] == 2
    assert finding["target_observed_visible_count"] == 1
    assert finding["target_not_observed_complete_path_count"] == 1
    assert finding["target_state_unresolved_count"] == 0
    assert finding["admitted_opposite_counterevidence_pair_count"] == 1
    assert finding["target_relative_state_is_general_attack_success_failure"] is False
    assert finding["finding_is_tactical_quality_truth"] is False
    assert finding["finding_is_causal_truth"] is False
    assert finding["pairwise_comparison_is_independent_evidence_vote"] is False
    assert finding["claim_output_allowed"] is False
    assert finding["report_language_allowed"] is True
    assert "general_attack_success_failure" in finding["FORBIDDEN_INFERENCE"]


def test_p02_c4_packet_is_claim_bounded_and_does_not_invent_support():
    episode, identities, visible_sequence, trace, evidence, semantics = _p02_c4_bridge_case()
    p02 = _progression_pool_p02(
        {},
        {},
        episode,
        {},
        semantics,
        identities,
        visible_sequence,
        trace,
        evidence,
    )
    candidate = p02["p02_c4_packet_candidates"][0]
    assert candidate["supporting_signals"] == []
    assert candidate["claim_ceiling"] == "composite_candidate_only"
    assert candidate["claim_output_allowed"] is False
    assert candidate["report_language_allowed"] is False
    assert candidate["production_release"] is False



def test_p02_acceptance_counters_are_explicit_and_reconciled():
    episode, identities, visible_sequence, trace, evidence, semantics = _p02_c4_bridge_case()
    p02 = _progression_pool_p02(
        {},
        {},
        episode,
        {},
        semantics,
        identities,
        visible_sequence,
        trace,
        evidence,
    )
    counters = p02["acceptance_counters"]
    assert counters["p02_process_unit_candidate_count"] == 2
    assert counters["p02_pairwise_comparison_candidate_count"] == 1
    assert counters["p02_opposite_outcome_comparison_candidate_count"] == 1
    assert counters["p02_independence_admitted_comparison_count"] == 1
    assert counters["p02_independence_not_admitted_comparison_count"] == 0
    assert counters["p02_c4_packet_candidate_count"] == 1
    assert counters["p02_semantic_zone_complete_process_unit_count"] == 2
    assert counters["p02_advanced_access_visible_count"] == 1
    assert counters["p02_no_advanced_access_visible_count"] == 1
    assert counters["p02_advanced_access_unresolved_count"] == 0
    assert counters["p02_invented_semantics_count"] == 0
    assert counters["p02_lost_atom_count"] == 0



def test_p02_population_collapse_prevents_pairwise_counterevidence_vote_explosion():
    episode, identities, visible_sequence, trace, evidence, semantics = _p02_c4_bridge_case()

    visible_sequence["visible_action_time_layer_candidates"].extend([
        {
            "visible_action_time_layer_candidate_id": "d1",
            "start_candidate": 50.0,
            "trackable_action_trace_candidate_ids": ["tr_d1"],
            "action_family_counts": {"PASS": 1},
        },
        {
            "visible_action_time_layer_candidate_id": "d2",
            "start_candidate": 60.0,
            "trackable_action_trace_candidate_ids": ["tr_d2"],
            "action_family_counts": {"PASS": 1},
        },
    ])
    visible_sequence["visible_action_sequence_candidates"].append({
        "visible_action_sequence_candidate_id": "vasq_cand_2",
        "team_identity_candidate_id": "teamc_A",
        "period_candidate": "1",
        "start_time_candidate": 50.0,
        "end_time_candidate": 60.0,
        "duration_candidate_seconds": 10.0,
        "time_layer_candidate_ids": ["d1", "d2"],
        "time_layer_count": 2,
        "trackable_action_trace_candidate_ids": ["tr_d1", "tr_d2"],
        "trace_candidate_count": 2,
        "action_family_counts": {"PASS": 2},
        "consequence_candidate_counts": {},
        "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "start_reason_candidate": "TIME_GAP_BOUNDARY",
        "end_reason_candidate": "TEAM_HANDOVER_BOUNDARY",
    })
    trace["trackable_action_trace_candidates"].extend([
        {"trackable_action_trace_candidate_id":"tr_d1","supporting_evidence_atom_ids":["ea_d1"]},
        {"trackable_action_trace_candidate_id":"tr_d2","supporting_evidence_atom_ids":["ea_d2"]},
    ])
    evidence["evidence_atoms"].extend([
        {"evidence_atom_id":"ea_d1","row_nucleus_candidate_id":"rn_d1"},
        {"evidence_atom_id":"ea_d2","row_nucleus_candidate_id":"rn_d2"},
    ])
    semantics["context_action_semantic_records"].extend([
        {"row_nucleus_candidate_id":"rn_d1","context_zone_candidate":"OWN_HALF"},
        {"row_nucleus_candidate_id":"rn_d2","context_zone_candidate":"MIDDLE_THIRD"},
    ])

    p02 = _progression_pool_p02(
        {},
        {},
        episode,
        {},
        semantics,
        identities,
        visible_sequence,
        trace,
        evidence,
    )

    assert p02["p02_pairwise_admitted_opposite_count"] == 2
    assert p02["p02_counterevidence_population_count"] == 1
    assert p02["p02_c4_packet_candidate_count"] == 1
    assert p02["p02_pairwise_counterevidence_collapsed_count"] == 1
    assert p02["population_emits_max_one_c4_counterevidence_packet"] is True
    assert p02["pairwise_comparison_is_independent_evidence_vote"] is False

    record = p02["p02_counterevidence_population_records"][0]
    assert record["admitted_opposite_pair_count"] == 2
    assert record["population_emits_max_one_c4_counterevidence_packet"] is True


def test_p02_recurring_consequence_path_binds_to_opponent_advanced_access() -> None:
    identities = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "teamc_A", "team_aliases_raw": ["TEAM_A"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
            {"team_identity_candidate_id": "teamc_B", "team_aliases_raw": ["TEAM_B"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
        ]
    }
    visible_sequence = {
        "visible_action_time_layer_candidates": [
            {"visible_action_time_layer_candidate_id":"a1","start_candidate":10.0,"trackable_action_trace_candidate_ids":["tr_turn"],"action_family_counts":{"TURNOVER":1}},
            {"visible_action_time_layer_candidate_id":"b1","start_candidate":20.0,"trackable_action_trace_candidate_ids":["tr_b1"],"action_family_counts":{"PASS":1}},
            {"visible_action_time_layer_candidate_id":"b2","start_candidate":24.0,"trackable_action_trace_candidate_ids":["tr_b2"],"action_family_counts":{"PASS":1}},
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id":"vasq_A",
                "team_identity_candidate_id":"teamc_A","period_candidate":"1",
                "start_time_candidate":10.0,"end_time_candidate":10.0,"duration_candidate_seconds":0.0,
                "time_layer_candidate_ids":["a1"],"time_layer_count":1,
                "trackable_action_trace_candidate_ids":["tr_turn"],"trace_candidate_count":1,
                "action_family_counts":{"TURNOVER":1},"consequence_candidate_counts":{},
                "sequence_record_status":"PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE",
                "start_reason_candidate":"PERIOD_START","end_reason_candidate":"TEAM_HANDOVER_BOUNDARY",
                "end_boundary_time_candidate":20.0,"next_team_identity_candidate_id":"teamc_B",
            },
            {
                "visible_action_sequence_candidate_id":"vasq_B",
                "team_identity_candidate_id":"teamc_B","period_candidate":"1",
                "start_time_candidate":20.0,"end_time_candidate":24.0,"duration_candidate_seconds":4.0,
                "time_layer_candidate_ids":["b1","b2"],"time_layer_count":2,
                "trackable_action_trace_candidate_ids":["tr_b1","tr_b2"],"trace_candidate_count":2,
                "action_family_counts":{"PASS":2},"consequence_candidate_counts":{},
                "sequence_record_status":"PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate":"AFTER_TEAM_HANDOVER","end_reason_candidate":"TIME_GAP_BOUNDARY",
            },
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id":"tr_turn","supporting_evidence_atom_ids":["ea_turn"]},
            {"trackable_action_trace_candidate_id":"tr_b1","supporting_evidence_atom_ids":["ea_b1"]},
            {"trackable_action_trace_candidate_id":"tr_b2","supporting_evidence_atom_ids":["ea_b2"]},
        ]
    }
    evidence = {
        "evidence_atoms": [
            {"evidence_atom_id":"ea_turn","row_nucleus_candidate_id":"rn_turn"},
            {"evidence_atom_id":"ea_b1","row_nucleus_candidate_id":"rn_b1"},
            {"evidence_atom_id":"ea_b2","row_nucleus_candidate_id":"rn_b2"},
        ]
    }
    semantics = {
        "context_zone_ontology_id": "TEST_EXPLICIT_BOX_ZONE_V1",
        "context_zone_domain": ["DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD", "PENALTY_AREA"],
        "context_zone_final_third_observable": True,
        "context_zone_penalty_area_observable": True,
        "context_action_semantic_records": [
            {"row_nucleus_candidate_id":"rn_turn","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn_b1","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn_b2","context_zone_candidate":"FINAL_THIRD"},
        ]
    }
    consequence = {
        "visible_consequence_path_recurrence_candidates": [
            {
                "team_identity_candidate_id":"teamc_A",
                "anchor_action_family_candidates":["TURNOVER"],
                "visible_consequence_path_signature":"ANCHOR:TURNOVER -> L1:OPPONENT:PASS -> L2:OPPONENT:PASS",
                "visible_occurrence_count":2,
                "eligible_anchor_population_count":2,
                "anchor_trace_refs":["tr_turn"],
            }
        ]
    }

    p02 = _progression_pool_p02(
        {}, {}, {}, consequence, semantics, identities, visible_sequence, trace, evidence
    )
    row = p02["visible_consequence_path_severity_candidates"][0]

    assert row["visible_consequence_path_signature"] == (
        "ANCHOR:TURNOVER -> L1:OPPONENT:PASS -> L2:OPPONENT:PASS"
    )
    assert row["exact_process_response_bound_count"] == 1
    assert row["advanced_access_visible_count"] == 1
    assert row["no_advanced_access_visible_count"] == 0
    assert row["access_unresolved_count"] == 0
    assert row["final_third_visible_count"] == 1
    assert row["no_final_third_visible_count"] == 0
    assert row["penalty_area_access_evaluation_status"] == "EVALUABLE"
    assert row["penalty_area_visible_count"] == 0
    assert row["no_penalty_area_visible_count"] == 1
    assert row["zone_path_unresolved_count"] == 0
    assert row["shot_activity_visible_count"] == 0
    assert row["no_shot_activity_visible_count"] == 1
    assert row["response_zone_route_counts"] == {"MIDDLE_THIRD->FINAL_THIRD": 1}
    assert row["response_zone_route_unresolved_count"] == 0
    assert row["response_zone_route_is_physical_trajectory_truth"] is False
    assert row["response_zone_route_is_tactical_route_truth"] is False
    assert row["severity_evaluation_scope"] == "POST_LOSS_OPPONENT_RESPONSE_ONLY"
    assert row["severity_evaluation_status"] == "EVALUATED"
    assert p02["visible_consequence_path_severity_scope"] == "POST_LOSS_OPPONENT_RESPONSE_ONLY"
    assert p02["recovery_continuation_requires_separate_same_team_process_evaluation"] is True
    assert row["severity_is_transition_defence_quality_truth"] is False
    assert row["severity_is_causal_truth"] is False


def test_p02_recovery_recurrence_is_not_misread_as_post_loss_severity() -> None:
    consequence = {
        "visible_consequence_path_recurrence_candidates": [
            {
                "team_identity_candidate_id": "teamc_A",
                "anchor_action_family_candidates": ["RECOVERY"],
                "visible_consequence_path_signature": (
                    "ANCHOR:RECOVERY -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS"
                ),
                "visible_occurrence_count": 2,
                "eligible_anchor_population_count": 2,
                "anchor_trace_refs": ["tr_recovery"],
            }
        ]
    }
    p02 = _progression_pool_p02({}, {}, {}, consequence)

    assert p02["visible_consequence_path_severity_candidate_count"] == 0
    assert p02["non_loss_recurrence_severity_not_evaluated_count"] == 1
    assert p02["recovery_continuation_requires_separate_same_team_process_evaluation"] is True


def test_p02_recovery_continuation_reads_only_post_anchor_same_team_access() -> None:
    identities = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "teamc_A", "team_aliases_raw": ["TEAM_A"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
        ],
        "actor_identity_candidates": [
            {"actor_identity_candidate_id":"actor_p0","actor_normalized_key":"player_zero","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p1","actor_normalized_key":"player_one","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p2","actor_normalized_key":"player_entry","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p3","actor_normalized_key":"player_after","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
        ],
    }
    visible_sequence = {
        "visible_action_time_layer_candidates": [
            {"visible_action_time_layer_candidate_id":"r0","start_candidate":10.0,"trackable_action_trace_candidate_ids":["tr_rec"],"action_family_counts":{"RECOVERY":1}},
            {"visible_action_time_layer_candidate_id":"r1","start_candidate":14.0,"trackable_action_trace_candidate_ids":["tr_p1"],"action_family_counts":{"PASS":1}},
            {"visible_action_time_layer_candidate_id":"r2","start_candidate":18.0,"trackable_action_trace_candidate_ids":["tr_p2"],"action_family_counts":{"PASS":1}},
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id":"vasq_recovery",
                "team_identity_candidate_id":"teamc_A","period_candidate":"1",
                "start_time_candidate":10.0,"end_time_candidate":18.0,"duration_candidate_seconds":8.0,
                "time_layer_candidate_ids":["r0","r1","r2"],"time_layer_count":3,
                "trackable_action_trace_candidate_ids":["tr_rec","tr_p1","tr_p2"],"trace_candidate_count":3,
                "action_family_counts":{"RECOVERY":1,"PASS":2},"consequence_candidate_counts":{},
                "sequence_record_status":"PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate":"TIME_GAP_BOUNDARY","end_reason_candidate":"TIME_GAP_BOUNDARY",
            }
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id":"tr_rec","start_candidate":10.0,"supporting_evidence_atom_ids":["ea_rec"]},
            {"trackable_action_trace_candidate_id":"tr_p1","start_candidate":14.0,"supporting_evidence_atom_ids":["ea_p1"]},
            {"trackable_action_trace_candidate_id":"tr_p2","start_candidate":18.0,"supporting_evidence_atom_ids":["ea_p2"]},
        ]
    }
    evidence = {
        "evidence_atoms": [
            {"evidence_atom_id":"ea_rec","row_nucleus_candidate_id":"rn_rec"},
            {"evidence_atom_id":"ea_p1","row_nucleus_candidate_id":"rn_p1"},
            {"evidence_atom_id":"ea_p2","row_nucleus_candidate_id":"rn_p2"},
        ]
    }
    semantics = {
        "context_zone_ontology_id": "TEST_EXPLICIT_BOX_ZONE_V1",
        "context_zone_domain": ["DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD", "PENALTY_AREA"],
        "context_zone_final_third_observable": True,
        "context_zone_penalty_area_observable": True,
        "context_action_semantic_records": [
            {"row_nucleus_candidate_id":"rn_rec","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn_p1","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn_p2","context_zone_candidate":"FINAL_THIRD"},
        ]
    }
    consequence = {
        "visible_consequence_path_recurrence_candidates": [
            {
                "team_identity_candidate_id":"teamc_A",
                "anchor_action_family_candidates":["RECOVERY"],
                "visible_consequence_path_signature":"ANCHOR:RECOVERY -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS",
                "visible_occurrence_count":2,
                "eligible_anchor_population_count":2,
                "anchor_trace_refs":["tr_rec"],
            }
        ]
    }

    p02 = _progression_pool_p02(
        {}, {}, {}, consequence, semantics, identities, visible_sequence, trace, evidence
    )
    assert p02["visible_consequence_path_severity_candidate_count"] == 0
    assert p02["recovery_continuation_severity_candidate_count"] == 1
    row = p02["recovery_continuation_severity_candidates"][0]
    assert row["severity_evaluation_scope"] == "POST_RECOVERY_SAME_TEAM_CONTINUATION_ONLY"
    assert row["same_team_process_bound_count"] == 1
    assert row["final_third_visible_count"] == 1
    assert row["penalty_area_access_evaluation_status"] == "EVALUABLE"
    assert row["penalty_area_visible_count"] == 0
    assert row["shot_activity_visible_count"] == 0
    assert row["post_recovery_zone_route_counts"] == {"MIDDLE_THIRD->FINAL_THIRD": 1}
    assert row["recovery_anchor_zone_is_access_outcome"] is False
    assert row["severity_is_recovery_quality_truth"] is False


def test_p02_same_team_pass_windows_collapse_to_unique_process_units() -> None:
    identities = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "teamc_A", "team_aliases_raw": ["TEAM_A"], "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND"},
        ],
        "actor_identity_candidates": [
            {"actor_identity_candidate_id":"actor_p0","actor_normalized_key":"player_zero","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p1","actor_normalized_key":"player_one","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p2","actor_normalized_key":"player_entry","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
            {"actor_identity_candidate_id":"actor_p3","actor_normalized_key":"player_after","decision_state":"ACTOR_IDENTITY_CANDIDATE_BOUND"},
        ],
    }
    visible_sequence = {
        "visible_action_time_layer_candidates": [
            {"visible_action_time_layer_candidate_id":"p0","start_candidate":10.0,"trackable_action_trace_candidate_ids":["tr_p0"],"action_family_counts":{"PASS":1}},
            {"visible_action_time_layer_candidate_id":"p1","start_candidate":14.0,"trackable_action_trace_candidate_ids":["tr_p1"],"action_family_counts":{"PASS":1}},
            {"visible_action_time_layer_candidate_id":"p2","start_candidate":18.0,"trackable_action_trace_candidate_ids":["tr_p2"],"action_family_counts":{"PASS":1,"CROSS":1}},
            {"visible_action_time_layer_candidate_id":"p3","start_candidate":22.0,"trackable_action_trace_candidate_ids":["tr_p3"],"action_family_counts":{"PASS":1,"SHOT":1,"TURNOVER":1}},
        ],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id":"vasq_pass_chain",
                "team_identity_candidate_id":"teamc_A","period_candidate":"1",
                "start_time_candidate":10.0,"end_time_candidate":22.0,"duration_candidate_seconds":12.0,
                "time_layer_candidate_ids":["p0","p1","p2","p3"],"time_layer_count":4,
                "trackable_action_trace_candidate_ids":["tr_p0","tr_p1","tr_p2","tr_p3"],"trace_candidate_count":4,
                "action_family_counts":{"PASS":4,"CROSS":1,"SHOT":1,"TURNOVER":1},"consequence_candidate_counts":{},
                "sequence_record_status":"PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate":"PERIOD_START","end_reason_candidate":"TIME_GAP_BOUNDARY",
            }
        ],
    }
    trace = {
        "trackable_action_trace_candidates": [
            {"trackable_action_trace_candidate_id":"tr_p0","start_candidate":10.0,"actor_identity_candidate_id":"actor_p0","supporting_evidence_atom_ids":["ea_p0"]},
            {"trackable_action_trace_candidate_id":"tr_p1","start_candidate":14.0,"actor_identity_candidate_id":"actor_p1","supporting_evidence_atom_ids":["ea_p1"]},
            {"trackable_action_trace_candidate_id":"tr_p2","start_candidate":18.0,"actor_identity_candidate_id":"actor_p2","supporting_evidence_atom_ids":["ea_p2"]},
            {"trackable_action_trace_candidate_id":"tr_p3","start_candidate":22.0,"actor_identity_candidate_id":"actor_p3","supporting_evidence_atom_ids":["ea_p3"]},
        ]
    }
    evidence = {
        "evidence_atoms": [
            {"evidence_atom_id":"ea_p0","row_nucleus_candidate_id":"rn_p0"},
            {"evidence_atom_id":"ea_p1","row_nucleus_candidate_id":"rn_p1"},
            {"evidence_atom_id":"ea_p2","row_nucleus_candidate_id":"rn_p2"},
            {"evidence_atom_id":"ea_p3","row_nucleus_candidate_id":"rn_p3"},
        ]
    }
    semantics = {
        "context_action_semantic_records": [
            {"row_nucleus_candidate_id":"rn_p0","context_zone_candidate":"DEFENSIVE_THIRD"},
            {"row_nucleus_candidate_id":"rn_p1","context_zone_candidate":"MIDDLE_THIRD"},
            {"row_nucleus_candidate_id":"rn_p2","context_zone_candidate":"FINAL_THIRD"},
            {"row_nucleus_candidate_id":"rn_p3","context_zone_candidate":"FINAL_THIRD"},
        ]
    }
    consequence = {
        "visible_consequence_path_recurrence_candidates": [
            {
                "team_identity_candidate_id":"teamc_A",
                "anchor_action_family_candidates":["PASS"],
                "visible_consequence_path_signature":"ANCHOR:PASS -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS",
                "visible_occurrence_count":2,
                "eligible_anchor_population_count":4,
                "anchor_trace_refs":["tr_p0","tr_p1"],
            }
        ]
    }

    p02 = _progression_pool_p02(
        {}, {}, {}, consequence, semantics, identities, visible_sequence, trace, evidence
    )
    profile = p02["same_team_continuation_process_profiles"][0]

    assert profile["anchor_visible_occurrence_count"] == 2
    assert profile["unique_process_unit_count"] == 1
    assert profile["process_unit_with_final_third_entry_count"] == 1
    assert profile["final_third_entry_process_unit_count"] == 1
    assert profile["final_third_entry_process_end_reason_counts"] == {"TIME_GAP_BOUNDARY": 1}
    assert profile["final_third_entry_process_with_shot_activity_count"] == 1
    assert profile["final_third_entry_process_with_turnover_activity_count"] == 1
    assert profile["final_third_entry_process_with_cross_activity_count"] == 1
    assert profile["final_third_entry_process_with_post_entry_shot_count"] == 1
    assert profile["final_third_entry_process_with_post_entry_turnover_count"] == 1
    assert profile["final_third_entry_process_with_post_entry_cross_count"] == 0
    assert profile["final_third_entry_process_with_entry_layer_cross_count"] == 1
    assert profile["final_third_entry_process_with_entry_layer_shot_count"] == 0
    assert profile["final_third_entry_process_with_entry_layer_turnover_count"] == 0
    assert profile["final_third_entry_process_with_no_later_visible_layer_count"] == 0
    assert profile["post_entry_activity_excludes_entry_timestamp_layer"] is True
    assert profile["same_timestamp_entry_layer_internal_order_claimed"] is False
    assert profile["final_third_entry_process_variant_candidate_count"] == 1
    variant = profile["final_third_entry_process_variant_candidates"][0]
    assert set(variant["post_entry_variant_facets"]) == {
        "POST_ENTRY_SHOT_VISIBLE",
        "POST_ENTRY_TURNOVER_VISIBLE",
    }
    assert variant["entry_layer_facets"] == ["ENTRY_LAYER_CROSS_VISIBLE"]
    assert variant["variant_facets_are_mutually_exclusive"] is False
    assert variant["variant_is_success_failure_truth"] is False
    assert profile["final_third_entry_post_entry_variant_facet_counts"] == {
        "POST_ENTRY_SHOT_VISIBLE": 1,
        "POST_ENTRY_TURNOVER_VISIBLE": 1,
    }
    assert profile["final_third_entry_entry_layer_facet_counts"] == {
        "ENTRY_LAYER_CROSS_VISIBLE": 1,
    }
    assert profile["terminal_boundary_is_process_outcome_truth"] is False
    assert profile["shot_activity_is_chance_quality_truth"] is False
    assert profile["max_anchor_windows_within_single_process_unit"] == 2
    assert profile["anchor_window_count_is_process_denominator"] is False
    assert profile["unique_process_unit_count_is_independent_evidence_count"] is False
    assert profile["same_process_multiple_anchor_reflection_possible"] is True
    participants = {
        row["actor_identity_candidate_id"]: row
        for row in profile["final_third_entry_actor_participation_candidates"]
    }
    assert set(participants) == {"actor_p0", "actor_p1", "actor_p2", "actor_p3"}
    assert participants["actor_p0"]["final_third_entry_process_participation_count"] == 1
    assert participants["actor_p1"]["final_third_entry_process_participation_count"] == 1
    assert participants["actor_p2"]["final_third_entry_layer_participation_count"] == 1
    assert participants["actor_p2"]["post_entry_participation_count"] == 0
    assert participants["actor_p2"]["actor_label_candidate"] == "player_entry"
    assert participants["actor_p3"]["post_entry_participation_count"] == 1
    assert participants["actor_p3"]["post_entry_variant_facet_counts"] == {
        "POST_ENTRY_SHOT_VISIBLE": 1,
        "POST_ENTRY_TURNOVER_VISIBLE": 1,
    }
    assert profile["actor_participation_is_causal_credit"] is False
    assert profile["actor_participation_is_quality_truth"] is False


def test_p02_thirds_only_zone_surface_marks_penalty_area_unobservable() -> None:
    p02 = _progression_pool_p02(
        {},
        {},
        {},
        {},
        {
            "context_zone_ontology_id": "THIRDS_ONLY_V1",
            "context_zone_domain": ["DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD"],
            "context_zone_final_third_observable": True,
            "context_zone_penalty_area_observable": False,
            "context_zone_penalty_area_unobservable_reason": "THIRDS_ONLY_ZONE_ONTOLOGY",
        },
    )

    assert p02["final_third_access_evaluable"] is True
    assert p02["penalty_area_access_evaluable"] is False
    assert p02["penalty_area_access_evaluation_status"] == "UNOBSERVABLE_WITH_CURRENT_DATA"
    assert p02["penalty_area_access_unobservable_reason"] == "THIRDS_ONLY_ZONE_ONTOLOGY"


def test_p02_explicit_box_capability_can_be_evaluable_without_provider_hardcoding() -> None:
    p02 = _progression_pool_p02(
        {},
        {},
        {},
        {},
        {
            "context_zone_ontology_id": "ANY_FUTURE_EXPLICIT_BOX_ZONE",
            "context_zone_domain": ["DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD", "PENALTY_AREA"],
            "context_zone_final_third_observable": True,
            "context_zone_penalty_area_observable": True,
        },
    )

    assert p02["penalty_area_access_evaluable"] is True
    assert p02["penalty_area_access_evaluation_status"] == "EVALUABLE"
    assert p02["penalty_area_access_unobservable_reason"] is None
