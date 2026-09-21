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
    _construct_c01,
    _phase_state_candidates,
    _progression_pool_p02,
)
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
    assert unit["terminal_activity_is_process_outcome_truth"] is False
    assert unit["comparison_candidate_ready"] is False



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
