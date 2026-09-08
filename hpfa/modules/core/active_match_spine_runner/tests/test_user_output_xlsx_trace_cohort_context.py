from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import _entity_summary, _representative_entities


def _rich_payload():
    return {
        "entity_views": {
            "player_view_candidates": [
                {
                    "player_raw_candidate": "Actor Alpha",
                    "team_raw_candidate": "Team One",
                    "source_role": "PLAYER_SURFACE_CANDIDATE",
                    "metric_values": {
                        "shots": {"raw_value": 2, "value_status": "OBSERVED"},
                    },
                    "aggregate_support_trace_context_state": "TRACE_CANDIDATE_COHORT_CONTEXT_ONLY",
                    "aggregate_support_trackable_trace_candidate_refs": [
                        {"trackable_action_trace_candidate_id": "tat_generic_1"},
                        {"trackable_action_trace_candidate_id": "tat_generic_2"},
                    ],
                    "aggregate_support_trace_relation_is_cohort_context_only": True,
                    "aggregate_support_trace_relation_is_individual_action_support": False,
                    "aggregate_support_trace_relation_is_physical_action_truth": False,
                }
            ],
            "team_view_candidates": [],
            "goalkeeper_view_candidates": [],
            "observed_metric_cell_count": 1,
            "aggregate_support_trace_cohort_context_link_count": 1,
            "aggregate_support_trace_candidate_ref_count": 2,
            "aggregate_support_trace_relation_review_required_count": 0,
        }
    }


def test_entity_summary_exposes_trace_cohort_context_counts_without_action_count_semantics():
    summary = _entity_summary(_rich_payload())
    assert summary["trace_cohort_context_links"] == 1
    assert summary["trace_candidate_refs"] == 2
    assert summary["trace_relation_review_required"] == 0
    assert "canonical_event_count" not in summary
    assert "true_action_count" not in summary


def test_representative_entity_surface_exposes_navigation_refs_with_claim_locks():
    lines = _representative_entities(_rich_payload())
    assert len(lines) == 1
    line = lines[0]
    assert "Actor Alpha" in line
    assert "trace_cohort_context_state=TRACE_CANDIDATE_COHORT_CONTEXT_ONLY" in line
    assert 'trace_candidate_refs=["tat_generic_1", "tat_generic_2"]' in line
    assert "trace_relation_is_cohort_context_only=true" in line
    assert "trace_relation_is_individual_action_support=false" in line
    assert "trace_relation_is_physical_action_truth=false" in line
