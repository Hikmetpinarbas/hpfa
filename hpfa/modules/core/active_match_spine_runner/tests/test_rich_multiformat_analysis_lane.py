from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich_multiformat_analysis_lane import _construct_c01, _entity_views, _phase_state_candidates
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


def _xlsx_player_row(binding_id="msb_generic"):
    return {
        "row_projection_id": "xrp_generic",
        "file_id": "file_generic",
        "relative_path": "players.xlsx",
        "source_sha256": "sha_generic",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "sheet_name": "Players",
        "source_row_number": 2,
        "match_surface_binding_id": binding_id,
        "identity_candidates": {
            "player_raw_candidate": "Actor Alpha",
            "team_raw_candidate": "Team One",
            "position_raw_candidate": "MF",
            "minutes_raw_candidate": 90,
        },
        "metric_values": {
            "shots": {"raw_metric_label": "Shots", "raw_value": 3, "value_status": "OBSERVED"},
        },
    }


def _identity_payload(binding_id="msb_generic", *, duplicate_actor=False):
    actors = [{
        "actor_identity_candidate_id": "actorc_generic_a",
        "team_identity_candidate_id": "teamc_generic",
        "match_surface_binding_id": binding_id,
        "team_normalized_key": "team_one",
        "actor_normalized_key": "actor_alpha",
        "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
        "validated_player_identity": False,
    }]
    if duplicate_actor:
        actors.append({
            "actor_identity_candidate_id": "actorc_generic_b",
            "team_identity_candidate_id": "teamc_generic",
            "match_surface_binding_id": binding_id,
            "team_normalized_key": "team_one",
            "actor_normalized_key": "actor_alpha",
            "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
            "validated_player_identity": False,
        })
    return {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "match_surface_binding_id": binding_id,
        "actor_identity_candidates": actors,
        "team_identity_candidates": [{
            "team_identity_candidate_id": "teamc_generic",
            "match_surface_binding_id": binding_id,
            "team_normalized_key": "team_one",
            "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
            "validated_team_identity": False,
        }],
        "validated_player_identity": False,
        "validated_team_identity": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _trace_payload(binding_id="msb_generic", *, claimed_truth=False):
    rows = []
    for index, family in enumerate(("PASS", "SHOT"), start=1):
        rows.append({
            "trackable_action_trace_candidate_id": f"tat_generic_{index}",
            "match_surface_binding_id": binding_id,
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "team_identity_candidate_id": "teamc_generic",
            "actor_identity_candidate_id": "actorc_generic_a",
            "action_family_candidates": [family],
            "trackable_action_candidate_is_event_truth": claimed_truth,
            "physical_action_identity_truth": False,
            "event_instance_allowed": False,
            "validated_event_identity": False,
            "count_value_output_allowed": False,
            "trace_count_is_physical_action_count": False,
        })
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": binding_id,
        "trackable_action_trace_candidates": rows,
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "trace_count_is_physical_action_count": False,
        "claim_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
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


def test_entity_view_preserves_xlsx_aggregate_support_lineage_without_truth_upgrade():
    rows = [_xlsx_player_row()]
    result = _entity_views(rows)
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_lineage"] == {
        "row_projection_id": "xrp_generic",
        "file_id": "file_generic",
        "relative_path": "players.xlsx",
        "source_sha256": "sha_generic",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "sheet_name": "Players",
        "source_row_number": 2,
        "match_surface_binding_id": "msb_generic",
    }
    assert view["aggregate_support_lineage_complete"] is True
    assert view["aggregate_support_is_timeline_identity"] is False
    assert view["aggregate_support_is_event_truth"] is False
    assert view["aggregate_support_is_independent_vote"] is False
    assert result["aggregate_support_lineage_incomplete_candidate_count"] == 0


def test_entity_view_marks_incomplete_aggregate_support_lineage_for_review():
    rows = [_xlsx_player_row(binding_id=None)]
    result = _entity_views(rows)
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_lineage_complete"] is False
    assert view["aggregate_support_attachment_state"] == "PROVENANCE_INCOMPLETE_REVIEW_REQUIRED"
    assert result["aggregate_support_lineage_incomplete_candidate_count"] == 1


def test_entity_view_links_unique_bound_match_local_identity_candidate_without_truth_upgrade():
    result = _entity_views([_xlsx_player_row()], _identity_payload())
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_attachment_state"] == "MATCH_LOCAL_IDENTITY_CANDIDATE_LINK_ONLY"
    assert view["aggregate_support_match_local_identity_candidate_ref"] == {
        "actor_identity_candidate_id": "actorc_generic_a",
        "team_identity_candidate_id": "teamc_generic",
        "team_normalized_key": "team_one",
        "actor_normalized_key": "actor_alpha",
    }
    assert view["aggregate_support_identity_relation_basis"] == [
        "same_match_surface_binding_id",
        "bound_match_local_actor_identity_candidate",
        "normalized_team_and_actor_candidate_match",
    ]
    assert view["aggregate_support_identity_relation_is_candidate_only"] is True
    assert view["aggregate_support_identity_relation_is_identity_truth"] is False
    assert view["aggregate_support_identity_relation_is_action_trace_attachment"] is False
    assert result["aggregate_support_identity_candidate_link_count"] == 1
    assert result["aggregate_support_identity_relation_review_required_count"] == 0
    assert result["aggregate_support_attachment_is_match_local_identity_truth"] is False
    assert result["aggregate_support_attachment_is_action_trace_identity"] is False


def test_entity_view_does_not_link_across_match_surface_binding():
    result = _entity_views([_xlsx_player_row()], _identity_payload(binding_id="msb_other"))
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_match_local_identity_candidate_ref"] is None
    assert view["aggregate_support_identity_relation_is_candidate_only"] is False
    assert result["aggregate_support_identity_candidate_link_count"] == 0
    assert result["aggregate_support_identity_relation_input_state"] == "IDENTITY_CANDIDATE_BINDING_MISMATCH_REVIEW_REQUIRED"
    assert result["aggregate_support_identity_relation_review_required_count"] == 1


def test_entity_view_ambiguous_identity_candidate_match_fails_to_review_not_attachment():
    result = _entity_views([_xlsx_player_row()], _identity_payload(duplicate_actor=True))
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_attachment_state"] == "IDENTITY_CANDIDATE_AMBIGUOUS_REVIEW_REQUIRED"
    assert view["aggregate_support_match_local_identity_candidate_ref"] is None
    assert view["aggregate_support_identity_relation_is_identity_truth"] is False
    assert view["aggregate_support_identity_relation_is_action_trace_attachment"] is False
    assert result["aggregate_support_identity_candidate_link_count"] == 0
    assert result["aggregate_support_identity_relation_review_required_count"] == 1


def test_entity_view_links_xlsx_aggregate_to_same_identity_trace_cohort_context_only():
    result = _entity_views([_xlsx_player_row()], _identity_payload(), _trace_payload())
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_trace_context_state"] == "TRACE_CANDIDATE_COHORT_CONTEXT_ONLY"
    assert [
        row["trackable_action_trace_candidate_id"]
        for row in view["aggregate_support_trackable_trace_candidate_refs"]
    ] == ["tat_generic_1", "tat_generic_2"]
    assert view["aggregate_support_trace_context_basis"] == [
        "same_match_surface_binding_id",
        "same_bound_team_identity_candidate_id",
        "same_bound_actor_identity_candidate_id",
        "trackable_trace_candidate_claim_boundary_preserved",
    ]
    assert view["aggregate_support_trace_relation_is_cohort_context_only"] is True
    assert view["aggregate_support_trace_relation_is_individual_action_support"] is False
    assert view["aggregate_support_trace_relation_is_action_trace_identity"] is False
    assert view["aggregate_support_trace_relation_is_physical_action_truth"] is False
    assert result["aggregate_support_trace_cohort_context_link_count"] == 1
    assert result["aggregate_support_trace_candidate_ref_count"] == 2
    assert result["aggregate_support_trace_relation_review_required_count"] == 0
    assert result["aggregate_support_trace_relation_input_state"] == "TRACKABLE_ACTION_TRACE_CANDIDATES_AVAILABLE"


def test_entity_view_rejects_cross_binding_trace_context_relation():
    result = _entity_views(
        [_xlsx_player_row()],
        _identity_payload(),
        _trace_payload(binding_id="msb_other"),
    )
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_trackable_trace_candidate_refs"] == []
    assert view["aggregate_support_trace_relation_is_cohort_context_only"] is False
    assert result["aggregate_support_trace_cohort_context_link_count"] == 0
    assert result["aggregate_support_trace_relation_input_state"] == "TRACE_CANDIDATE_BINDING_MISMATCH_REVIEW_REQUIRED"
    assert result["aggregate_support_trace_relation_review_required_count"] == 1


def test_entity_view_rejects_trace_payload_that_claims_event_truth():
    result = _entity_views([_xlsx_player_row()], _identity_payload(), _trace_payload(claimed_truth=True))
    view = result["player_view_candidates"][0]
    assert view["aggregate_support_trackable_trace_candidate_refs"] == []
    assert view["aggregate_support_trace_relation_is_individual_action_support"] is False
    assert result["aggregate_support_trace_relation_input_state"] == "TRACE_CANDIDATE_ROW_CLAIM_BOUNDARY_MISMATCH_REVIEW_REQUIRED"
    assert result["aggregate_support_trace_relation_review_required_count"] == 1


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
            "progressive_passes": {"raw_metric_label": "Progressive passes", "raw_value": 12, "value_kind": "number", "value_status": "OBSERVED"},
            "shots": {"raw_metric_label": "Shots", "raw_value": 4, "value_kind": "number", "value_status": "OBSERVED"},
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