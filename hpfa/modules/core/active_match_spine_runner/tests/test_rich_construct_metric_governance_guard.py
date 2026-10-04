from hpfa.modules.core.active_match_spine_runner.src.rich_construct_metric_governance_guard import (
    assess_rich_construct_candidate,
)


def _candidate(label="Passes accurate, %"):
    return {
        "packet_family": "progression",
        "input_metrics": [
            {
                "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
                "raw_metric_label": label,
            }
        ],
    }


def _governance(*, decision="DEFINITION_ALIGNMENT_CANDIDATE", bound=True, observed=True, rate=True):
    return {
        "status": "SMOKE_PASS",
        "aggregate_definition_alignment": {
            "alignment_rows": [
                {
                    "aggregate_label": "Passes accurate, %",
                    "alignment_decision": decision,
                    "metric_definition_bound": bound,
                    "aggregate_label_observed": observed,
                    "rate_calculation_admitted": rate,
                }
            ]
        },
    }


def test_matching_admitted_aggregate_definition_allows_candidate_without_truth_promotion():
    result = assess_rich_construct_candidate(_candidate(), _governance())
    assert result["status"] == "PASS"
    assert result["admitted"] is True
    assert result["matched_alignment_count"] == 1
    assert result["construct_truth"] is False
    assert result["aggregate_equivalence_truth"] is False
    assert result["same_provider_multiformat_is_independent_support"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_label_navigation_without_alignment_is_review_required():
    result = assess_rich_construct_candidate(_candidate("Progressive passes"), _governance())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["admitted"] is False
    assert result["reason"] == "aggregate_metric_semantic_authority_missing"


def test_unbound_definition_cannot_admit_rich_construct():
    result = assess_rich_construct_candidate(_candidate(), _governance(bound=False))
    assert result["admitted"] is False


def test_rate_with_open_denominator_cannot_admit_rich_construct():
    result = assess_rich_construct_candidate(_candidate(), _governance(rate=False))
    assert result["admitted"] is False


def test_non_xlsx_candidate_is_not_blocked_by_metric_guard():
    result = assess_rich_construct_candidate(
        {"input_metrics": [{"source_surface": "episode_feature_vector_lite_v1"}]},
        _governance(),
    )
    assert result["status"] == "NOT_APPLICABLE"
    assert result["admitted"] is True


def test_metric_governance_fail_closed_blocks_aggregate_backed_construct():
    governance = _governance()
    governance["status"] = "FAIL_CLOSED"
    result = assess_rich_construct_candidate(_candidate(), governance)
    assert result["status"] == "FAIL_CLOSED"
    assert result["admitted"] is False
