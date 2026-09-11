from __future__ import annotations

import importlib.util
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
SOURCE = SRC / "provider_semantic_utilization_audit.py"
SPEC = importlib.util.spec_from_file_location("provider_semantic_utilization_audit", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_csv_and_xml_volumes_are_audited_separately_without_independence_promotion() -> None:
    payload = {
        "provider_label_records": [
            {
                "source_format": "csv",
                "surface_row_volume": 8,
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "PASS",
                "outcome_candidate": "SUCCESS",
                "terminal_outcome_candidate": "NOT_TERMINAL",
                "downstream_eligibility": "ELIGIBLE",
            },
            {
                "source_format": "xml",
                "surface_row_volume": 5,
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "PASS",
                "relation_candidate": "RELATED_ACTION",
                "downstream_eligibility": "ELIGIBLE",
            },
            {
                "source_format": "xml",
                "surface_row_volume": 3,
                "mapping_status": "UNKNOWN_UNREVIEWED",
                "semantic_role_candidate": "UNKNOWN_UNREVIEWED",
                "outcome_candidate": "SUCCESS",
                "downstream_eligibility": "BLOCKED_UNKNOWN",
            },
        ]
    }

    audit = MODULE.build_provider_semantic_utilization_audit(payload)

    assert audit["csv"]["surface_label_volume"] == 8
    assert audit["csv"]["mapped_semantic_label_volume"] == 8
    assert audit["xml"]["surface_label_volume"] == 8
    assert audit["xml"]["mapped_semantic_label_volume"] == 5
    assert audit["xml"]["review_required_label_volume"] == 3
    assert audit["xml"]["mapped_semantic_label_volume_ratio"] == 5 / 8
    assert audit["csv"]["mapped_semantic_dimension_label_volume"] == {
        "action_family_candidate": 8,
        "outcome_candidate": 8,
        "terminal_outcome_candidate": 8,
    }
    assert audit["xml"]["mapped_semantic_dimension_label_volume"] == {
        "action_family_candidate": 5,
        "relation_candidate": 5,
    }
    assert audit["xml"]["semantic_dimension_volumes_are_not_additive_or_independent_evidence"] is True
    assert audit["csv_xml_combined_surface_label_volume"] == 16
    assert audit["csv_xml_combined_is_independent_evidence_count"] is False
    assert audit["cross_format_volume_must_not_be_interpreted_as_action_count"] is True
    assert audit["canonical_event_count"] == "UNKNOWN"
    assert audit["true_action_count"] == "UNKNOWN"
    assert audit["production_release"] is False


def test_unknown_or_missing_volume_is_not_fabricated() -> None:
    payload = {
        "provider_label_records": [
            {
                "source_format": "xml",
                "surface_row_volume": None,
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "semantic_role_candidate": "ACTION_ANCHOR",
                "outcome_candidate": "SUCCESS",
            }
        ]
    }

    audit = MODULE.build_provider_semantic_utilization_audit(payload)

    assert audit["xml"]["label_record_count"] == 1
    assert audit["xml"]["volume_known_record_count"] == 0
    assert audit["xml"]["surface_label_volume"] == 0
    assert audit["xml"]["mapped_semantic_label_volume_ratio"] is None
    assert audit["xml"]["mapped_semantic_dimension_label_volume"] == {}


def test_review_required_semantics_do_not_enter_mapped_dimension_volume() -> None:
    payload = {
        "provider_label_records": [
            {
                "source_format": "csv",
                "surface_row_volume": 4,
                "mapping_status": "TOKEN_FALLBACK_REVIEW_REQUIRED",
                "semantic_role_candidate": "ACTION_ANCHOR",
                "outcome_candidate": "SUCCESS",
                "terminal_outcome_candidate": "TERMINAL",
            }
        ]
    }

    audit = MODULE.build_provider_semantic_utilization_audit(payload)

    assert audit["csv"]["mapped_semantic_dimension_label_volume"] == {}
    assert audit["csv"]["review_required_label_volume"] == 4


def test_semantic_dimension_volume_is_mapping_inventory_not_downstream_truth() -> None:
    audit = MODULE.build_provider_semantic_utilization_audit({"provider_label_records": []})

    assert "format_local_semantic_dimension_mapping_volume" in audit["does_measure"]
    for forbidden in (
        "episode_utilization",
        "process_utilization",
        "metric_utilization",
        "finding_utilization",
    ):
        assert forbidden in audit["does_not_measure"]


def test_audit_does_not_claim_downstream_utilization() -> None:
    audit = MODULE.build_provider_semantic_utilization_audit({"provider_label_records": []})

    for forbidden in (
        "episode_utilization",
        "process_utilization",
        "metric_utilization",
        "finding_utilization",
    ):
        assert forbidden in audit["does_not_measure"]


def test_no_sample_match_identity_leak() -> None:
    text = SOURCE.read_text(encoding="utf-8").casefold()
    forbidden = [
        "genclerbirligi",
        "gençlerbirliği",
        "fenerbahce",
        "fenerbahçe",
        "galatasaray",
    ]
    assert not any(token in text for token in forbidden)
