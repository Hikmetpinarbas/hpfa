from hpfa.modules.core.aggregate_definition_alignment_lite.src.aggregate_definition_alignment import (
    build_alignment,
    normalize_label,
)


def xlsx_payload(label: str = "Passes accurate, %"):
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "files": [
            {
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "sheets": [
                    {
                        "source_role": "PLAYER_SURFACE_CANDIDATE",
                        "metric_inventory": [
                            {
                                "raw_metric_label": label,
                                "normalized_metric_label": normalize_label(label),
                            }
                        ],
                    }
                ],
            }
        ],
    }


def label_payload(include_failure: bool = True):
    records = [
        {
            "record_id": "csv:player:pass-success",
            "source_format": "csv",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "action_family_candidate": "PASS",
            "outcome_candidate": "SUCCESS",
        }
    ]
    if include_failure:
        records.append(
            {
                "record_id": "csv:player:pass-failure",
                "source_format": "csv",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "action_family_candidate": "PASS",
                "outcome_candidate": "FAILURE",
            }
        )
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "provider_label_records": records,
    }


def metric_payload(status: str = "DEFINITION_CANDIDATE_READY"):
    return {
        "module_id": "metric_definition_policy_lite_v1",
        "status": "SMOKE_PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "metrics": [
            {
                "metric_id": "pass_completion_rate_candidate",
                "definition_status": status,
            }
        ],
    }


def registry(
    evidence: str = "REVIEWED_PROVIDER_DEFINITION_CANDIDATE",
    dependency=None,
):
    return {
        "registry_version": "1.0.0",
        "definitions": [
            {
                "definition_id": "sportsbase_pass_completion_candidate_v1",
                "provider_id": "sportsbase",
                "provider_version": "reviewed_surface_v1",
                "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                "aggregate_label": "Passes accurate, %",
                "metric_id": "pass_completion_rate_candidate",
                "value_type": "percentage",
                "unit": "percent",
                "numerator_definition": "PASS + SUCCESS candidate",
                "denominator_definition": "PASS + SUCCESS or FAILURE candidate",
                "required_occurrence_semantics": [
                    {
                        "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                        "action_family_candidate": "PASS",
                        "outcome_candidate": "SUCCESS",
                    },
                    {
                        "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                        "action_family_candidate": "PASS",
                        "outcome_candidate": "FAILURE",
                    },
                ],
                "definition_evidence_status": evidence,
                "derivation_dependency": dependency or ["SAME_PROVIDER_DERIVED_SURFACE"],
                "independence_status": "NON_INDEPENDENT_SAME_PROVIDER",
                "claim_ceiling": "AGGREGATE_DEFINITION_ALIGNMENT_CANDIDATE_ONLY",
            }
        ],
    }


def test_exact_reviewed_definition_produces_candidate_not_truth():
    result = build_alignment(
        xlsx_payload(), label_payload(), metric_payload(), registry()
    )
    assert result["status"] == "SMOKE_PASS"
    assert result["alignment_rows"][0]["alignment_decision"] == (
        "DEFINITION_ALIGNMENT_CANDIDATE"
    )
    assert result["aggregate_equivalence_truth"] is False
    assert result["independent_confirmation_allowed"] is False
    assert result["comparison_allowed"] is False
    assert result["metric_value_output_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_same_label_without_provider_definition_requires_review():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        metric_payload(),
        registry(evidence="UNRESOLVED"),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["alignment_rows"][0]["alignment_decision"] == (
        "REVIEW_REQUIRED_DEFINITION_ALIGNMENT"
    )
    assert "provider_definition_evidence_unresolved" in {
        row["code"] for row in result["review_hits"]
    }


def test_missing_occurrence_semantics_requires_review():
    result = build_alignment(
        xlsx_payload(), label_payload(include_failure=False), metric_payload(), registry()
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert "required_occurrence_semantics_not_observed" in {
        row["code"] for row in result["review_hits"]
    }


def test_unready_metric_policy_fails_closed():
    result = build_alignment(
        xlsx_payload(), label_payload(), metric_payload("BLOCKED"), registry()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "metric_policy_not_ready" in {
        row["code"] for row in result["hard_block_hits"]
    }


def test_unresolved_derivation_dependency_requires_review():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        metric_payload(),
        registry(dependency=["DERIVATION_DEPENDENCY_UNRESOLVED"]),
    )
    assert result["status"] == "REVIEW_REQUIRED"


def test_upstream_fail_closed_propagates():
    payload = xlsx_payload()
    payload["status"] = "FAIL_CLOSED"
    result = build_alignment(payload, label_payload(), metric_payload(), registry())
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_fail_closed" in {
        row["code"] for row in result["hard_block_hits"]
    }


def test_registry_version_mismatch_fails_closed():
    data = registry()
    data["registry_version"] = "2.0.0"
    result = build_alignment(
        xlsx_payload(), label_payload(), metric_payload(), data
    )
    assert result["status"] == "FAIL_CLOSED"


def test_empty_registry_fails_closed():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        metric_payload(),
        {"registry_version": "1.0.0", "definitions": []},
    )
    assert result["status"] == "FAIL_CLOSED"


def test_no_sample_match_identity_leak():
    result = build_alignment(
        xlsx_payload(), label_payload(), metric_payload(), registry()
    )
    text = str(result).casefold()
    for forbidden in ("fenerbahce", "galatasaray", "gornik", "19721253"):
        assert forbidden not in text
