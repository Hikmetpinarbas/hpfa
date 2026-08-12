from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "provider_coordinate_attachment_semantics.py"
)
spec = importlib.util.spec_from_file_location("pcas", MODULE_PATH)
pcas = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(pcas)


def field_payload():
    return {
        "module_id": "provider_alias_field_semantics_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "field_semantic_records": [
            {
                "format": "csv",
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "normalized_field": "pos_x",
                "canonical_key_candidate": "event.start_x_candidate",
                "mapping_status": "EXACT_RULE_CANDIDATE",
                "alias_reliability": "HIGH",
            },
            {
                "format": "csv",
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "normalized_field": "pos_y",
                "canonical_key_candidate": "event.start_y_candidate",
                "mapping_status": "EXACT_RULE_CANDIDATE",
                "alias_reliability": "HIGH",
            },
        ],
    }


def label_payload():
    base = {
        "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
        "source_format": "csv",
        "mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "semantic_role_candidate": "ACTION_ANCHOR",
        "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
    }
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "provider_label_records": [
            {
                **base,
                "normalized_label": "successful cross and pass interception attempts",
                "action_family_candidate": "INTERCEPTION",
                "action_subtype_candidate": "CROSS_OR_PASS_INTERCEPTION",
                "object_action_family_candidate": "PASS_OR_CROSS",
                "outcome_candidate": "SUCCESS",
            },
            {
                **base,
                "normalized_label": "unsuccessful cross and pass interception attempts",
                "action_family_candidate": "INTERCEPTION",
                "action_subtype_candidate": "CROSS_OR_PASS_INTERCEPTION",
                "object_action_family_candidate": "PASS_OR_CROSS",
                "outcome_candidate": "FAILURE",
            },
            {
                **base,
                "normalized_label": "shots saved",
                "action_family_candidate": "GOALKEEPER_ACTION",
                "action_subtype_candidate": "SAVE",
                "object_action_family_candidate": "SHOT",
                "outcome_candidate": "SUCCESS",
            },
        ],
    }


def nucleus_payload():
    return {
        "module_id": "row_nucleus_inventory_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "match_surface_binding_id": "msb_test",
        "row_nuclei": [
            {
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "action_raw": "successful cross and pass interception attempts",
                "period_candidate": "1",
                "start_candidate": "10",
                "pos_x_candidate": "5",
                "pos_y_candidate": "30",
                "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
            },
            {
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "action_raw": "unsuccessful cross and pass interception attempts",
                "period_candidate": "1",
                "start_candidate": "20",
                "pos_x_candidate": "7",
                "pos_y_candidate": "31",
                "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
            },
            {
                "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                "action_raw": "shots saved",
                "period_candidate": "1",
                "start_candidate": "40",
                "pos_x_candidate": "95",
                "pos_y_candidate": "33",
                "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
            },
        ],
    }


def bundles_payload(reflect_interception=False, review_success=False):
    rows = [
        {
            "action_bundle_candidate_id": "g1",
            "action_family_candidate": "INTERCEPTION",
            "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
            "bundle_status": "REVIEW_REQUIRED" if review_success else "PASS",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "normalized_labels": ["successful cross and pass interception attempts"],
            "team_identity_candidate_id": "t1",
            "period_candidate": "1",
            "start_candidate": "10",
            "end_candidate": "22",
            "pos_x_candidate": "5",
            "pos_y_candidate": "30",
        },
        {
            "action_bundle_candidate_id": "g2",
            "action_family_candidate": "INTERCEPTION",
            "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
            "bundle_status": "PASS",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "normalized_labels": ["unsuccessful cross and pass interception attempts"],
            "team_identity_candidate_id": "t1",
            "period_candidate": "1",
            "start_candidate": "20",
            "end_candidate": "32",
            "pos_x_candidate": "7",
            "pos_y_candidate": "31",
        },
        {
            "action_bundle_candidate_id": "s1",
            "action_family_candidate": "GOALKEEPER_ACTION",
            "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
            "bundle_status": "PASS",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "normalized_labels": ["shots saved"],
            "team_identity_candidate_id": "t1",
            "period_candidate": "1",
            "start_candidate": "40",
            "end_candidate": "52",
            "pos_x_candidate": "95",
            "pos_y_candidate": "33",
        },
        {
            "action_bundle_candidate_id": "shot1",
            "action_family_candidate": "SHOT",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "bundle_status": "PASS",
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "normalized_labels": ["shots on target"],
            "team_identity_candidate_id": "t2",
            "period_candidate": "1",
            "start_candidate": "40",
            "end_candidate": "52",
            "pos_x_candidate": "95",
            "pos_y_candidate": "33",
        },
    ]
    if reflect_interception:
        rows.append(
            {
                "action_bundle_candidate_id": "p1",
                "action_family_candidate": "PASS",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "bundle_status": "PASS",
                "coordinate_evidence_status": "COORDINATE_PRESENT",
                "normalized_labels": ["passes accurate"],
                "team_identity_candidate_id": "t2",
                "period_candidate": "1",
                "start_candidate": "9",
                "end_candidate": "21",
                "pos_x_candidate": "5",
                "pos_y_candidate": "30",
            }
        )
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "match_surface_binding_id": "msb_test",
        "action_bundle_candidates": rows,
    }


def frame_payload():
    return {
        "module_id": "coordinate_frame_precondition_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "match_surface_binding_id": "msb_test",
    }


def build(**kwargs):
    return pcas.build_provider_coordinate_attachment_semantics(
        kwargs.get("field", field_payload()),
        kwargs.get("labels", label_payload()),
        kwargs.get("nuclei", nucleus_payload()),
        kwargs.get("bundles", bundles_payload()),
        kwargs.get("frame", frame_payload()),
    )


def test_interception_attachment_candidate_passes_without_reflection():
    out = build()
    assert out["status"] == "PASS"
    assert (
        out["goalkeeper_interception_attachment_status"]
        == "EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED"
    )
    assert out["goalkeeper_interception_primary_direction_anchor_candidate_allowed"] is True
    assert out["outcome_stratified_support_pooling_allowed"] is True
    assert out["event_fusion_allowed"] is False


def test_same_coordinate_overlapping_pass_reflection_blocks_primary_candidate():
    out = build(bundles=bundles_payload(reflect_interception=True))
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["overlapping_same_coordinate_object_action_count"] == 1
    assert out["goalkeeper_interception_primary_direction_anchor_candidate_allowed"] is False


def test_save_control_detects_shot_reflection():
    out = build()
    assert out["save_control_exact_shot_surface_overlap_count"] >= 1
    assert out["save_control_status"] == "OBJECT_ACTION_REFLECTION_CONTROL_CONFIRMED"


def test_review_bundle_is_excluded_not_promoted():
    out = build(bundles=bundles_payload(review_success=True))
    assert out["interception_review_bundle_excluded_count"] == 1
    assert out["interception_pass_bundle_count"] == 1
    assert out["outcome_stratified_support_pooling_allowed"] is False


def test_missing_goalkeeper_pos_x_field_basis_keeps_attachment_unresolved():
    field = field_payload()
    field["field_semantic_records"] = field["field_semantic_records"][1:]
    out = build(field=field)
    assert out["field_attachment_basis_status"] == "FIELD_ATTACHMENT_BASIS_UNRESOLVED"
    assert out["goalkeeper_interception_primary_direction_anchor_candidate_allowed"] is False


def test_token_or_unreviewed_label_semantics_do_not_promote():
    labels = label_payload()
    labels["provider_label_records"][0]["mapping_status"] = "TOKEN_FALLBACK_REVIEW_REQUIRED"
    out = build(labels=labels)
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["goalkeeper_interception_primary_direction_anchor_candidate_allowed"] is False


def test_cross_format_support_required():
    nuclei = nucleus_payload()
    nuclei["row_nuclei"][0]["cross_format_support_status"] = "CSV_ONLY"
    out = build(nuclei=nuclei)
    assert out["row_cross_format_support_missing_count"] == 1
    assert out["goalkeeper_interception_primary_direction_anchor_candidate_allowed"] is False


def test_match_surface_binding_mismatch_fails_closed():
    frame = frame_payload()
    frame["match_surface_binding_id"] = "other"
    out = build(frame=frame)
    assert out["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_mismatch_or_missing" in out["hard_block_hits"]


def test_claim_boundaries_stay_closed():
    out = build()
    assert out["coordinate_attachment_is_validated_provider_truth"] is False
    assert out["coordinate_is_goalkeeper_physical_position_truth"] is False
    assert out["attack_direction_is_validated_truth"] is False
    assert out["progression_truth"] is False
    assert out["canonical_event_count"] == "UNKNOWN"
    assert out["production_release"] is False


def test_nested_phone_output_rejected(tmp_path):
    output = tmp_path / "HPFA" / "nested"
    try:
        pcas.validate_out(output)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("expected rejection")


def test_no_sample_match_identity_leak():
    text = MODULE_PATH.read_text(encoding="utf-8").casefold()
    forbidden = [
        "australia",
        "turkey",
        "ugurcan",
        "patrick beach",
        "13.06.2026",
        "6935",
        "77798",
    ]
    assert not any(token in text for token in forbidden)
