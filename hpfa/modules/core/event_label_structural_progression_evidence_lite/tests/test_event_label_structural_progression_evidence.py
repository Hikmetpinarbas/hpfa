from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from event_label_structural_progression_evidence import (  # noqa: E402
    build_event_label_structural_progression_evidence,
    validate_out,
    write_outputs,
)

BINDING = "msb_test_candidate"


def provider_payload(records=None):
    records = records if records is not None else [
        {
            "record_id": "plr_1",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "normalized_label": "progressive passes accurate",
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "rule_id": "rule_progressive_accurate",
            "progression_candidate": "PROGRESSIVE_CANDIDATE",
            "outcome_candidate": "SUCCESS",
        }
    ]
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "status": "PASS",
        "provider_label_records": records,
        "provider_label_record_count": len(records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def bundle_record(bundle_id="bundle_1", labels=None):
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "normalized_labels": labels if labels is not None else ["progressive passes accurate"],
        "canonical_event_count": "UNKNOWN",
        "event_instance_allowed": False,
    }


def action_bundle_payload(records=None):
    records = records if records is not None else [bundle_record()]
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": records,
        "action_bundle_candidate_count": len(records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def action_node(
    *,
    node_id="node_1",
    bundle_ids=None,
    support_labels=None,
    start=10.0,
    end=10.2,
    outcome=False,
    derived=False,
):
    return {
        "selected_action_node_id": node_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_candidate_a",
        "actor_identity_candidate_id": "actor_candidate_a",
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": end,
        "action_family_candidates": ["PASS"],
        "selected_action_bundle_candidate_ids": bundle_ids if bundle_ids is not None else ["bundle_1"],
        "support_normalized_labels": support_labels if support_labels is not None else ["goal"],
        "terminal_outcome_support_visible": outcome,
        "derived_consequence_support_visible": derived,
    }


def action_payload(*, nodes=None, **node_kwargs):
    nodes = nodes if nodes is not None else [action_node(**node_kwargs)]
    return {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "selected_action_nodes": nodes,
        "selected_action_node_count": len(nodes),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def frame(*, resolved=True):
    return {
        "coordinate_scale_candidate": "PROVIDER_105X68_SCALE_CANDIDATE" if resolved else "UNRESOLVED_COORDINATE_SCALE_REVIEW_REQUIRED",
        "coordinate_bounds_status": "PASS_CANDIDATE_BOUNDS" if resolved else "UNRESOLVED",
        "team_period_attack_direction_candidates": [
            {
                "team_identity_candidate_id": "team_candidate_a",
                "period_candidate": "1",
                "attack_direction_candidate": "ATTACK_TOWARD_HIGH_X_CANDIDATE",
                "attack_direction_support_status": "PASS_SHOT_CONCENTRATION_CANDIDATE",
            }
        ] if resolved else [],
    }


def event_record(
    *,
    event_id="event_1",
    anchor_id="node_1",
    zone="ZONE_GAIN_CANDIDATE",
    zone_status="PASS_CANDIDATE_CLASSIFICATION",
    consequence="CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
    false_progression="VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE",
):
    return {
        "selected_event_consequence_candidate_id": event_id,
        "anchor_selected_action_node_id": anchor_id,
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_candidate_a",
        "actor_identity_candidate_id": "actor_candidate_a",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "anchor_action_family_candidates": ["PASS"],
        "zone_delta_class": zone,
        "zone_delta_status": zone_status,
        "consequence_class_candidate": consequence,
        "false_progression_candidate": false_progression,
    }


def event_payload(*, records=None, resolved_axis=True):
    records = records if records is not None else [event_record()]
    return {
        "module_id": "selected_event_consequence_surface_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "coordinate_frame_candidate": frame(resolved=resolved_axis),
        "selected_event_consequence_candidates": records,
        "selected_event_consequence_candidate_count": len(records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def sequence_payload():
    return {
        "module_id": "eventonly_sequence_consequence_engine_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "metric_records": [
            {"metric_id": "progression_to_final_third_support", "status": "BLOCKED_SEMANTICS_UNAVAILABLE"},
            {"metric_id": "progression_to_box_entry_support", "status": "BLOCKED_SEMANTICS_UNAVAILABLE"},
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def aggregate_payload(*, support=True, record_id="plr_1"):
    rows = [{
        "definition_id": "definition_1",
        "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
        "semantic_support": [{"record_ids": [record_id] if support else []}],
        "alignment_hits": [],
    }]
    return {
        "module_id": "aggregate_definition_alignment_lite_v1",
        "status": "SMOKE_PASS",
        "alignment_rows": rows,
        "definition_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def build(**overrides):
    payloads = {
        "provider_labels": provider_payload(),
        "action_bundles": action_bundle_payload(),
        "selected_action": action_payload(),
        "selected_event": event_payload(),
        "sequence_consequence": sequence_payload(),
        "aggregate_alignment": aggregate_payload(),
    }
    payloads.update(overrides)
    return build_event_label_structural_progression_evidence(**payloads)


def test_action_anchor_lineage_not_support_label_drives_provider_match():
    result = build(selected_action=action_payload(support_labels=["goal", "assist"]))
    row = result["evidence_records"][0]
    assert row["action_anchor_normalized_labels"] == ["progressive passes accurate"]
    assert row["support_normalized_labels"] == ["goal", "assist"]
    assert row["provider_label_record_ids"] == ["plr_1"]
    assert row["provider_progression_label_present"] is True


def test_failure_outcome_is_recognized_exactly():
    failure_record = {
        "record_id": "plr_failure",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "normalized_label": "incomplete progressive passes",
        "mapping_status": "EXACT_REVIEWED_CANDIDATE",
        "rule_id": "rule_progressive_failure",
        "progression_candidate": "PROGRESSIVE_CANDIDATE",
        "outcome_candidate": "FAILURE",
    }
    result = build(
        provider_labels=provider_payload([failure_record]),
        action_bundles=action_bundle_payload([bundle_record(labels=["incomplete progressive passes"])]),
        aggregate_alignment=aggregate_payload(record_id="plr_failure"),
    )
    row = result["evidence_records"][0]
    assert row["provider_successful_outcome_candidate"] is False
    assert row["provider_unsuccessful_outcome_candidate"] is True


def test_missing_action_bundle_reference_fails_closed():
    result = build(selected_action=action_payload(bundle_ids=["missing_bundle"]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("action_anchor_bundle_reference_missing") for hit in result["hard_block_hits"])


def test_provider_label_not_auto_truth_without_independent_support():
    result = build(
        selected_action=action_payload(start=None, end=None, outcome=False, derived=False),
        selected_event=event_payload(
            records=[event_record(
                zone="UNRESOLVED_ZONE_DELTA_REVIEW_REQUIRED",
                zone_status="UNRESOLVED",
                consequence="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED",
                false_progression="PROGRESSION_CONTEXT_UNRESOLVED",
            )],
            resolved_axis=False,
        ),
        aggregate_alignment=aggregate_payload(support=False),
    )
    row = result["evidence_records"][0]
    assert row["verification_status"] == "LABEL_ONLY"
    assert row["downstream_eligibility"] == "COMPONENT_ONLY_FALLBACK"
    assert row["claim_allowed"] is False


def test_supported_progression_uses_current_producer_status_mapping():
    result = build(selected_action=action_payload(outcome=True))
    row = result["evidence_records"][0]
    axis = row["axis_eligibility"]
    assert axis["producer_attack_direction_support_status"] == "PASS_SHOT_CONCENTRATION_CANDIDATE"
    assert axis["attack_direction_support_status"] == "SUPPORTED_CANDIDATE"
    assert axis["axis_eligibility_state"] == "AXIS_ELIGIBLE_CANDIDATE"
    assert row["verification_status"] == "LABEL_SUPPORTED"
    assert row["structural_progression_classification"] == "STRUCTURAL_PROGRESSION_CANDIDATE"


def test_explicit_successful_progression_geometry_conflict_blocks_downstream():
    result = build(selected_event=event_payload(records=[event_record(
        zone="RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE",
        consequence="NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
        false_progression="PROGRESSION_CONTEXT_UNRESOLVED",
    )]))
    row = result["evidence_records"][0]
    assert row["verification_status"] == "LABEL_CONFLICTED"
    assert row["downstream_eligibility"] == "LABEL_CONFLICTED_AND_DOWNSTREAM_BLOCKED"
    assert row["progression_truth"] is False


def test_unknown_label_is_preserved_and_blocked():
    result = build(
        action_bundles=action_bundle_payload([bundle_record(labels=["unreviewed provider label"])]),
        aggregate_alignment=aggregate_payload(support=False),
    )
    row = result["evidence_records"][0]
    assert row["provider_source_support"] == "UNKNOWN"
    assert row["verification_status"] == "LABEL_UNKNOWN"
    assert row["downstream_eligibility"] == "DOWNSTREAM_BLOCKED_REVIEW_REQUIRED"


def test_missing_axis_blocks_geometry_support_not_component_evidence():
    result = build(selected_event=event_payload(resolved_axis=False))
    row = result["evidence_records"][0]
    assert row["axis_eligibility"]["axis_eligibility_state"] == "COORDINATE_UNAVAILABLE"
    assert row["coordinate_support"] == "UNAVAILABLE"
    assert row["structural_progression_classification"] == "PROGRESSION_CONTEXT_UNRESOLVED"
    assert result["evidence_record_count"] == 1


def test_distinct_event_candidates_are_not_auto_merged():
    nodes = [action_node(), action_node(node_id="node_2", bundle_ids=["bundle_2"], start=20.0, end=20.2)]
    bundles = [bundle_record(), bundle_record(bundle_id="bundle_2")]
    result = build(
        action_bundles=action_bundle_payload(bundles),
        selected_action=action_payload(nodes=nodes),
        selected_event=event_payload(records=[
            event_record(event_id="event_1", anchor_id="node_1"),
            event_record(event_id="event_2", anchor_id="node_2"),
        ]),
    )
    assert result["evidence_record_count"] == 2
    assert len({row["evidence_record_id"] for row in result["evidence_records"]}) == 2


def test_progression_rates_remain_blocked():
    gate = build()["progression_metric_gate"]
    assert gate["metric_rate_output_allowed"] is False
    assert gate["denominator_gate_status"] == "METRIC_BLOCKED"
    assert gate["source_progression_metric_status_counts"] == {"BLOCKED_SEMANTICS_UNAVAILABLE": 2}


def test_line_break_components_are_disclosed_without_truth_promotion():
    evidence = build(selected_action=action_payload(outcome=True))["evidence_records"][0]["label_assisted_line_break_evidence"]
    assert set(evidence["components"]) == {
        "provider_label_evidence",
        "geometry_support",
        "outcome_support",
        "consequence_support",
        "aggregate_support",
    }
    assert evidence["line_break_evidence_score_candidate"] is None
    assert evidence["line_break_truth"] is False
    assert evidence["packing_truth"] is False


def test_upstream_production_claim_fails_closed():
    bad = provider_payload()
    bad["production_release"] = True
    result = build(provider_labels=bad)
    assert result["status"] == "FAIL_CLOSED"
    assert "provider_labels_production_release_claimed" in result["hard_block_hits"]


def test_flat_phone_output_policy_and_outputs(tmp_path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out("/sdcard/Download/HPFA/nested")
    out = tmp_path / "HPFA"
    paths = write_outputs(build(), out)
    assert set(paths) == {"json", "summary", "analyst"}
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_claim_boundaries_remain_false():
    result = build()
    for key in (
        "progression_truth",
        "line_break_truth",
        "packing_truth",
        "opponent_structure_truth",
        "possession_truth",
        "sequence_truth",
        "tactical_truth",
        "causality_truth",
        "claim_allowed",
        "production_release",
    ):
        assert result[key] is False
    assert result["canonical_event_count"] == "UNKNOWN"
