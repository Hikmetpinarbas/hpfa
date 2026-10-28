from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.metric_anatomy_bridge import (
    build_metric_anatomy,
)


def _occurrence() -> dict:
    return {
        "module_id": "action_occurrence_admission_lite_v1",
        "status": "PASS",
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_progressive_success",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "primary_family_candidate": "PASS",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "semantic_components": [
                    {
                        "label": "Progressive passes accurate",
                        "semantic_rule_id": "plvs_v2_progressive_passes_accurate",
                        "outcome": "SUCCESS",
                        "progression": "PROGRESSIVE_CANDIDATE",
                    }
                ],
                "attributes": {"outcome_candidate": "SUCCESS"},
            },
            {
                "action_occurrence_candidate_id": "occ_pass_failure",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "primary_family_candidate": "PASS",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_b",
                "semantic_components": [
                    {
                        "label": "Incomplete progressive passes",
                        "semantic_rule_id": "plvs_v2_incomplete_progressive_passes",
                        "outcome": "FAILURE",
                        "progression": "PROGRESSIVE_CANDIDATE",
                    }
                ],
                "attributes": {"outcome_candidate": "FAILURE"},
            },
        ],
    }


def _xlsx() -> dict:
    return {
        "module_id": "xlsx_entity_metric_row_projection_lite_v1",
        "status": "PASS",
        "files": [
            {
                "sheets": [
                    {
                        "rows": [
                            {
                                "row_projection_id": "xrp_a",
                                "source_role": "PLAYER_SURFACE_CANDIDATE",
                                "source_sha256": "sha_a",
                                "identity_candidates": {"player_raw_candidate": "Player A"},
                                "metric_values": {
                                    "progressive_passes_accurate": {
                                        "raw_metric_label": "Progressive passes accurate",
                                        "raw_value": 7,
                                        "value_status": "OBSERVED",
                                    }
                                },
                            }
                        ]
                    }
                ]
            }
        ],
    }


def _dictionary() -> dict:
    return {
        "metrics": [
            {
                "metric_id": "progressive_pass_accurate",
                "provider_id": "sportsbase",
                "provider_version": "provider_definition_unverified",
                "raw_labels": ["Progressive passes accurate"],
                "metric_family": "progressive_pass",
                "construct": "provider progressive-pass successful occurrence candidate",
                "semantic_type": "count",
                "unit": "count",
                "definition_evidence_status": "PROVIDER_DEFINITION_REQUIRED",
            }
        ]
    }


def _alignment() -> dict:
    return {
        "alignment_rows": [
            {
                "definition_id": "pass_completion_definition",
                "metric_id": "pass_completion_rate_candidate",
                "aggregate_label": "Passes accurate, %",
                "alignment_decision": "REVIEW_REQUIRED_DEFINITION_ALIGNMENT",
                "definition_evidence_status": "PROVIDER_DEFINITION_REQUIRED",
                "semantic_support": [
                    {
                        "requirement": {
                            "action_family_candidate": "PASS",
                            "outcome_candidate": "SUCCESS",
                        },
                        "match_count": 10,
                        "provider_bound_match_count": 10,
                    },
                    {
                        "requirement": {
                            "action_family_candidate": "PASS",
                            "outcome_candidate": "FAILURE",
                        },
                        "match_count": 3,
                        "provider_bound_match_count": 3,
                    },
                ],
            }
        ]
    }


def test_progressive_pass_micro_and_aggregate_surfaces_form_anatomy_candidate() -> None:
    report = build_metric_anatomy(_occurrence(), _xlsx(), _dictionary(), _alignment())

    assert report["micro_aggregate_linked_label_candidate_count"] == 1
    row = report["label_surface_anatomy_candidates"][0]
    assert row["metric_id"] == "progressive_pass_accurate"
    assert row["micro_occurrence_candidate_count"] == 1
    assert row["aggregate_cell_candidate_count"] == 1
    assert row["aggregate_cell_candidates"][0]["raw_value"] == 7
    assert row["anatomy_status"] == "SURFACE_ANATOMY_CANDIDATE_PROVIDER_DEFINITION_REQUIRED"
    assert row["same_provider_cross_surface_dependency"] == "NON_INDEPENDENT"
    assert row["micro_to_aggregate_identity_binding_admitted"] is False
    assert row["numeric_reconciliation_performed"] is False
    assert row["count_parity_is_definition_equivalence"] is False


def test_definition_anatomy_exposes_success_failure_coverage_without_opening_denominator() -> None:
    report = build_metric_anatomy(_occurrence(), _xlsx(), _dictionary(), _alignment())
    row = report["definition_anatomy_candidates"][0]

    coverage = row["required_semantic_coverage"]
    assert coverage[0]["grammar_occurrence_candidate_count"] == 1
    assert coverage[1]["grammar_occurrence_candidate_count"] == 1
    assert row["denominator_coverage_complete"] is False
    assert row["rate_calculation_admitted"] is False
    assert row["numeric_reconciliation_performed"] is False
    assert row["aggregate_mismatch_action"] == "AUDIT_DEFINITION_SCOPE_DENOMINATOR_NOT_ROW_DELETION"


def test_xlsx_never_creates_action_identity_or_independent_vote() -> None:
    report = build_metric_anatomy(_occurrence(), _xlsx(), _dictionary(), _alignment())
    assert report["xlsx_creates_action_identity"] is False
    assert report["csv_xml_xlsx_are_independent_evidence_votes"] is False
    assert report["aggregate_mismatch_means_bad_rows"] is False
    assert report["aggregate_mismatch_requires_definition_scope_denominator_audit"] is True
    assert report["metric_value_output_allowed"] is False
    assert report["numeric_reconciliation_allowed"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_missing_dictionary_fails_closed() -> None:
    report = build_metric_anatomy(_occurrence(), _xlsx(), {}, _alignment())
    assert report["status"] == "FAIL_CLOSED"
    assert report["hard_block_hits"] == ["metric_dictionary_metrics_missing"]
