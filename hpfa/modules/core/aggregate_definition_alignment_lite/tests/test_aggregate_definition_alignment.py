import json

from hpfa.modules.core.aggregate_definition_alignment_lite.src.aggregate_definition_alignment import (
    build_alignment,
    normalize_label,
)

METRIC_FP = "42b89dca3e3e07580a3267bba6388fe44fbb81048962d145bd74f9c615a1bb42"
NUMERATOR = "Provider-version rows eligible under the declared successful-pass candidate definition."
DENOMINATOR = "Provider-version rows eligible under the declared attempted-pass candidate definition in the same entity, period and observation window."
XLSX_SHA = "a" * 64
CSV_SHA = "b" * 64
XML_SHA = "c" * 64


def xlsx_payload(label: str = "Passes accurate, %"):
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "files": [
            {
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "relative_path": "Players.xlsx",
                "sha256": XLSX_SHA,
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


def label_payload(include_failure: bool = True, status: str = "PASS"):
    records = [
        {
            "record_id": "csv:player:pass-success",
            "source_format": "csv",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "source_sha256": CSV_SHA,
            "raw_label": "Pass Success",
            "normalized_label": normalize_label("Pass Success"),
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "action_family_candidate": "PASS",
            "outcome_candidate": "SUCCESS",
        }
    ]
    if include_failure:
        records.append(
            {
                "record_id": "xml:player:pass-failure",
                "source_format": "xml",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "source_sha256": XML_SHA,
                "raw_label": "Pass Failure",
                "normalized_label": normalize_label("Pass Failure"),
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "action_family_candidate": "PASS",
                "outcome_candidate": "FAILURE",
            }
        )
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "provider_label_records": records,
    }


def _prov(sha, label, *, provider_id="sportsbase", provider_version="reviewed_surface_v1", admitted=True):
    row = {
        "source_sha256": sha,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "normalized_label": normalize_label(label),
        "provider_candidate": "SPORTSBASE_PROVIDER_CANDIDATE",
    }
    if provider_id is not None:
        row["provider_id"] = provider_id
    if provider_version is not None:
        row["provider_version"] = provider_version
    if admitted is not None:
        row["provider_provenance_admitted"] = admitted
    return row


def reconciliation_payload(
    status: str = "PASS",
    *,
    validated_provider_semantics: bool = True,
    provider_id: str | None = "sportsbase",
    provider_version: str | None = "reviewed_surface_v1",
    admitted: bool | None = True,
):
    return {
        "module_id": "cross_format_reconciliation_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "validated_cross_format_equivalence": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_provider_semantics": validated_provider_semantics,
        "provider_semantic_provenance_records": [
            _prov(
                XLSX_SHA,
                "Passes accurate, %",
                provider_id=provider_id,
                provider_version=provider_version,
                admitted=admitted,
            ),
            _prov(
                CSV_SHA,
                "Pass Success",
                provider_id=provider_id,
                provider_version=provider_version,
                admitted=admitted,
            ),
            _prov(
                XML_SHA,
                "Pass Failure",
                provider_id=provider_id,
                provider_version=provider_version,
                admitted=admitted,
            ),
        ],
    }


def metric_payload(*, closed: bool = True, ready: bool = True):
    return {
        "module_id": "metric_definition_policy_lite_v1",
        "status": "SMOKE_PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "metrics": [
            {
                "metric_id": "pass_completion_rate_candidate",
                "definition_status": "DEFINITION_CANDIDATE_READY" if ready else "BLOCKED",
                "definition_fingerprint_sha256": METRIC_FP,
                "value_type": "percentage",
                "unit": "percent",
                "numerator_definition": NUMERATOR,
                "denominator_definition": DENOMINATOR,
                "denominator_closure_status": "CLOSED" if closed else "UNKNOWN",
                "rate_calculation_admitted": closed,
            }
        ],
    }


def registry(*, reviewed: bool = True):
    evidence = (
        "REVIEWED_PROVIDER_DEFINITION_CANDIDATE"
        if reviewed
        else "PROVIDER_DEFINITION_REQUIRED"
    )
    dependency = (
        ["SAME_PROVIDER_DERIVED_SURFACE"]
        if reviewed
        else ["DERIVATION_DEPENDENCY_UNRESOLVED"]
    )
    return {
        "registry_version": "2.0.0",
        "definitions": [
            {
                "definition_id": "sportsbase_pass_completion_candidate_v2",
                "provider_id": "sportsbase",
                "provider_version": "reviewed_surface_v1" if reviewed else "provider_definition_unverified",
                "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                "aggregate_label": "Passes accurate, %",
                "metric_id": "pass_completion_rate_candidate",
                "metric_definition_fingerprint_sha256": METRIC_FP,
                "value_type": "percentage",
                "unit": "percent",
                "numerator_definition": NUMERATOR,
                "denominator_definition": DENOMINATOR,
                "required_occurrence_semantics": [
                    {
                        "source_formats": ["csv", "xml"],
                        "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                        "action_family_candidate": "PASS",
                        "outcome_candidate": "SUCCESS",
                    },
                    {
                        "source_formats": ["csv", "xml"],
                        "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                        "action_family_candidate": "PASS",
                        "outcome_candidate": "FAILURE",
                    },
                ],
                "definition_evidence_status": evidence,
                "derivation_dependency": dependency,
                "independence_status": "NON_INDEPENDENT_SAME_PROVIDER",
                "claim_ceiling": "AGGREGATE_DEFINITION_ALIGNMENT_CANDIDATE_ONLY",
            }
        ],
    }


def test_reviewed_closed_definition_is_candidate_not_truth():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "SMOKE_PASS"
    row = result["alignment_rows"][0]
    assert row["alignment_decision"] == "DEFINITION_ALIGNMENT_CANDIDATE"
    assert row["metric_definition_bound"] is True
    assert row["aggregate_label_surface_observed"] is True
    assert row["aggregate_label_observed"] is True
    assert row["aggregate_equivalence_truth"] is False
    assert row["comparison_allowed"] is False
    assert row["measurement_invariance_truth"] is False
    assert row["cross_group_comparability_status"] == "R36_REQUIRED_BEFORE_GROUP_COMPARISON"
    assert result["same_label_is_same_definition"] is False
    assert result["count_parity_is_definition_equivalence"] is False
    assert result["same_provider_multi_surface_is_independent_confirmation"] is False
    assert result["provider_provenance_binding_required"] is True
    assert result["provider_candidate_is_validated_provider_identity"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_current_unresolved_provider_definition_requires_review():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(provider_version="provider_definition_unverified"),
        metric_payload(closed=True),
        registry(reviewed=False),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    codes = {hit["code"] for hit in result["review_hits"]}
    assert "provider_definition_evidence_unresolved" in codes
    assert "derivation_dependency_unresolved" in codes


def test_provider_candidate_only_cannot_confirm_definition():
    recon = reconciliation_payload(
        validated_provider_semantics=False,
        provider_id=None,
        provider_version=None,
        admitted=None,
    )
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        recon,
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["alignment_rows"][0]
    assert row["aggregate_label_surface_observed"] is True
    assert row["aggregate_label_observed"] is False
    assert row["alignment_decision"] == "REVIEW_REQUIRED_DEFINITION_ALIGNMENT"
    assert "aggregate_provider_binding_unresolved" in {
        hit["code"] for hit in result["review_hits"]
    }


def test_unknown_provider_cannot_confirm_definition():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(provider_id=None),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    row = result["alignment_rows"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["aggregate_label_observed"] is False
    assert "aggregate_provider_binding_unresolved" in {
        hit["code"] for hit in result["review_hits"]
    }


def test_provider_mismatch_cannot_confirm_definition():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(provider_id="another_provider"),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    row = result["alignment_rows"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["aggregate_label_observed"] is False
    serialized = json.dumps(result["review_hits"], ensure_ascii=False)
    assert "provider_id_mismatch" in serialized


def test_required_provider_version_missing_cannot_confirm_definition():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(provider_version=None),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    row = result["alignment_rows"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["aggregate_label_observed"] is False
    serialized = json.dumps(result["review_hits"], ensure_ascii=False)
    assert "provider_version_missing" in serialized


def test_provider_version_mismatch_cannot_confirm_definition():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(provider_version="different_version"),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    row = result["alignment_rows"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["aggregate_label_observed"] is False
    serialized = json.dumps(result["review_hits"], ensure_ascii=False)
    assert "provider_version_mismatch" in serialized


def test_occurrence_semantics_from_wrong_provider_cannot_confirm_definition():
    recon = reconciliation_payload()
    recon["provider_semantic_provenance_records"][1]["provider_id"] = "another_provider"
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        recon,
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["alignment_rows"][0]
    assert row["aggregate_label_observed"] is True
    support = row["semantic_support"][0]
    assert support["match_count"] == 1
    assert support["provider_bound_match_count"] == 0
    assert "required_occurrence_provider_binding_unresolved" in {
        hit["code"] for hit in result["review_hits"]
    }


def test_r19_open_denominator_keeps_rate_alignment_under_review():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=False),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["alignment_rows"][0]
    assert row["denominator_closure_status"] == "UNKNOWN"
    assert row["rate_calculation_admitted"] is False
    codes = {hit["code"] for hit in result["review_hits"]}
    assert "metric_denominator_closure_unresolved" in codes
    assert "metric_rate_calculation_not_admitted" in codes


def test_denominator_closure_cannot_cross_definition_boundary():
    data = registry(reviewed=True)
    data["definitions"][0]["denominator_definition"] = "Different denominator."
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=True),
        data,
    )
    assert result["status"] == "FAIL_CLOSED"
    row = result["alignment_rows"][0]
    assert row["metric_definition_bound"] is False
    assert row["denominator_closure_status"] == "UNBOUND"
    assert row["rate_calculation_admitted"] is False
    codes = {hit["code"] for hit in result["hard_block_hits"]}
    assert "metric_denominator_definition_mismatch" in codes
    assert "denominator_closure_not_bound_to_aligned_definition" in codes


def test_metric_fingerprint_mismatch_fails_closed():
    data = registry(reviewed=True)
    data["definitions"][0]["metric_definition_fingerprint_sha256"] = "b" * 64
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=True),
        data,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "metric_definition_fingerprint_mismatch" in {
        hit["code"] for hit in result["hard_block_hits"]
    }


def test_upstream_review_required_is_preserved_for_label_semantics():
    result = build_alignment(
        xlsx_payload(),
        label_payload(status="REVIEW_REQUIRED"),
        reconciliation_payload(),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required" in {hit["code"] for hit in result["review_hits"]}


def test_upstream_review_required_is_preserved_for_reconciliation():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(status="REVIEW_REQUIRED"),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required" in {hit["code"] for hit in result["review_hits"]}


def test_missing_occurrence_semantics_requires_review():
    result = build_alignment(
        xlsx_payload(),
        label_payload(include_failure=False),
        reconciliation_payload(),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert "required_occurrence_semantics_not_observed" in {
        hit["code"] for hit in result["review_hits"]
    }


def test_unready_metric_policy_fails_closed():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(ready=False),
        registry(reviewed=True),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "metric_policy_not_ready" in {
        hit["code"] for hit in result["hard_block_hits"]
    }


def test_cross_format_truth_promotion_fails_closed():
    recon = reconciliation_payload()
    recon["validated_event_identity"] = True
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        recon,
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "reconciliation_truth_overclaim" in {
        hit["code"] for hit in result["hard_block_hits"]
    }


def test_same_provider_cannot_be_declared_independent_confirmation():
    data = registry(reviewed=True)
    data["definitions"][0]["independence_status"] = "INDEPENDENT_CONFIRMATION"
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=True),
        data,
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "independence_overclaim_same_provider_surface" in {
        hit["code"] for hit in result["hard_block_hits"]
    }


def test_source_role_contract_never_promotes_xlsx_or_csv_xml_to_event_identity():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(),
        metric_payload(closed=True),
        registry(reviewed=True),
    )
    assert result["xlsx_row_is_event_identity"] is False
    assert result["csv_xml_candidate_linkage_is_physical_event_identity"] is False
    assert result["source_surface_contract"]["csv"]["role"] == "ACTION_COORDINATE_CANDIDATE_SURFACE"
    assert result["source_surface_contract"]["xml"]["role"] == "ACTION_TYPE_SOURCE_INTERVAL_CANDIDATE_SURFACE"
    assert result["source_surface_contract"]["xlsx"]["role"] == "AGGREGATE_CANDIDATE_SURFACE"


def test_no_sample_match_identity_leak():
    result = build_alignment(
        xlsx_payload(),
        label_payload(),
        reconciliation_payload(
            validated_provider_semantics=False,
            provider_id=None,
            provider_version=None,
            admitted=None,
        ),
        metric_payload(closed=False),
        registry(reviewed=False),
    )
    text = json.dumps(result, ensure_ascii=False).casefold()
    for forbidden in (
        "fenerbahce",
        "galatasaray",
        "gornik",
        "sturm graz",
        "heart of midlothian",
        "australia",
        "turkey",
        "13.06.2026",
    ):
        assert forbidden not in text
