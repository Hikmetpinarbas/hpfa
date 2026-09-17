from hpfa.modules.core.cross_role_relation_candidate_resolver_lite.src.surface_dependency_topology import (
    AGGREGATE_DERIVATION_UNRESOLVED,
    PARTIAL_SEMANTIC_PROJECTION,
    ROLE_TRANSFORMATION,
    SERIALIZATION_REFLECTION,
    build_surface_dependency_topology,
)


def _reconciliation():
    return {
        "module_id": "cross_format_reconciliation_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "pair_reports": [
            {
                "pair_id": "player_pair",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "decision": "PASS_ALIGNMENT_CANDIDATE",
                "exact_surface_alignment_candidate_count": 10,
                "required_field_mismatch_candidate_count": 0,
                "xlsx_support": {
                    "source_dependency_status": "DERIVATION_DEPENDENCY_UNRESOLVED",
                    "independent_confirmation_allowed": False,
                },
            }
        ],
    }


def _cross_role():
    return {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "resolved_relation_candidates": [
            {
                "resolved_relation_candidate_id": "player_team_1",
                "relation_record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "source_roles": ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
            },
            {
                "resolved_relation_candidate_id": "gk_team_1",
                "relation_record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "source_roles": ["GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
            },
        ],
    }


def test_exact_csv_xml_pair_is_serialization_reflection_not_independent_support():
    payload = build_surface_dependency_topology(_reconciliation(), _cross_role())
    row = next(
        item for item in payload["surface_dependency_records"]
        if item["source_ref"] == "player_pair"
    )
    assert row["dependency_type"] == SERIALIZATION_REFLECTION
    assert row["independent_support_allowed"] is False
    assert payload["cross_format_alignment_is_independent_evidence"] is False


def test_player_team_and_goalkeeper_team_receive_distinct_dependency_types():
    payload = build_surface_dependency_topology(_reconciliation(), _cross_role())
    by_ref = {item["source_ref"]: item for item in payload["surface_dependency_records"]}
    assert by_ref["player_team_1"]["dependency_type"] == PARTIAL_SEMANTIC_PROJECTION
    assert by_ref["gk_team_1"]["dependency_type"] == ROLE_TRANSFORMATION
    assert payload["goalkeeper_surface_is_player_filtered_subset_truth"] is False
    assert payload["independent_support_created"] is False


def test_xlsx_support_stays_aggregate_derivation_unresolved():
    payload = build_surface_dependency_topology(_reconciliation(), _cross_role())
    row = next(
        item for item in payload["surface_dependency_records"]
        if item["source_ref"] == "player_pair:xlsx_support"
    )
    assert row["dependency_type"] == AGGREGATE_DERIVATION_UNRESOLVED
    assert row["occurrence_identity_created"] is False
    assert payload["aggregate_is_action_identity"] is False


def test_unknown_cross_role_pair_stays_unresolved_and_review_required():
    cross_role = _cross_role()
    cross_role["resolved_relation_candidates"].append(
        {
            "resolved_relation_candidate_id": "player_gk_1",
            "relation_record_status": "PASS_CANDIDATE_CLASSIFICATION",
            "source_roles": ["PLAYER_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE"],
        }
    )
    payload = build_surface_dependency_topology(_reconciliation(), cross_role)
    row = next(
        item for item in payload["surface_dependency_records"]
        if item["source_ref"] == "player_gk_1"
    )
    assert row["dependency_type"] == "UNRESOLVED"
    assert row["review_required"] is True
    assert payload["status"] == "REVIEW_REQUIRED"
