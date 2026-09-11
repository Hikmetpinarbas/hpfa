from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich_multiformat_analysis_lane import _entity_views


def test_xlsx_aggregate_can_bind_review_bounded_trace_cohort_without_truth_upgrade():
    binding_id = "msb_review_bound_generic"
    rows = [{
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
            "progressive_passes": {
                "raw_metric_label": "Progressive passes",
                "raw_value": 7,
                "value_status": "OBSERVED",
            },
        },
    }]
    identity_payload = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "match_surface_binding_id": binding_id,
        "actor_identity_candidates": [{
            "actor_identity_candidate_id": "actorc_generic",
            "team_identity_candidate_id": "teamc_generic",
            "match_surface_binding_id": binding_id,
            "team_normalized_key": "team_one",
            "actor_normalized_key": "actor_alpha",
            "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
        }],
        "team_identity_candidates": [{
            "team_identity_candidate_id": "teamc_generic",
            "match_surface_binding_id": binding_id,
            "team_normalized_key": "team_one",
            "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
        }],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": binding_id,
        "trackable_action_trace_candidates": [{
            "trackable_action_trace_candidate_id": "tat_generic",
            "match_surface_binding_id": binding_id,
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "team_identity_candidate_id": "teamc_generic",
            "actor_identity_candidate_id": "actorc_generic",
            "action_family_candidates": ["PASS"],
            "trackable_action_candidate_is_event_truth": False,
            "physical_action_identity_truth": False,
            "event_instance_allowed": False,
            "validated_event_identity": False,
            "count_value_output_allowed": False,
            "trace_count_is_physical_action_count": False,
        }],
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "trace_count_is_physical_action_count": False,
        "claim_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    result = _entity_views(rows, identity_payload, trace_payload)
    view = result["player_view_candidates"][0]

    assert view["aggregate_support_trace_context_state"] == "TRACE_CANDIDATE_COHORT_CONTEXT_REVIEW_BOUND"
    assert [ref["trackable_action_trace_candidate_id"] for ref in view["aggregate_support_trackable_trace_candidate_refs"]] == ["tat_generic"]
    assert view["aggregate_support_trace_relation_is_cohort_context_only"] is True
    assert view["aggregate_support_trace_relation_is_review_bound"] is True
    assert view["aggregate_support_trace_relation_is_individual_action_support"] is False
    assert view["aggregate_support_trace_relation_is_action_trace_identity"] is False
    assert view["aggregate_support_trace_relation_is_physical_action_truth"] is False
    assert view["aggregate_support_is_independent_vote"] is False
    assert result["aggregate_support_trace_cohort_context_link_count"] == 1
    assert result["aggregate_support_trace_candidate_ref_count"] == 1
    assert result["aggregate_support_trace_relation_review_required_count"] == 1
    assert result["aggregate_support_trace_relation_review_bound"] is True
