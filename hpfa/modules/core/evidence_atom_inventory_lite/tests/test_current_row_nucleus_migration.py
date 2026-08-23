from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.evidence_atom_inventory_lite.src import evidence_atom_inventory as mod


def _registry() -> dict:
    return {
        "registry_id": "sportsbase_label_semantics_reviewed_v2",
        "exact_rules": [
            {
                "label": "Passes accurate",
                "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
                "semantic_role": "ACTION_ANCHOR",
                "action_family": "PASS",
                "outcome": "SUCCESSFUL",
                "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                "semantics_decision": "EXACT_REVIEWED_ACTION",
                "review_status": "REVIEWED_CANDIDATE",
                "rule_id": "test_player_pass",
            },
            {
                "label": "Shots saved",
                "source_roles": ["GOALKEEPER_SURFACE_CANDIDATE"],
                "semantic_role": "ACTION_ANCHOR",
                "action_family": "GOALKEEPER_ACTION",
                "outcome": "SUCCESSFUL",
                "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                "semantics_decision": "EXACT_REVIEWED_ACTION",
                "review_status": "REVIEWED_CANDIDATE",
                "rule_id": "test_gk_save",
            },
            {
                "label": "start of the 1st half",
                "source_roles": ["TEAM_SURFACE_CANDIDATE"],
                "semantic_role": "PERIOD_OR_META",
                "downstream_eligibility": "ADMIN_ONLY",
                "semantics_decision": "META_ALIAS_PRESERVED",
                "review_status": "REVIEWED_CANDIDATE",
                "rule_id": "test_admin_start",
            },
        ],
        "prefix_rules": [],
        "anchor_tokens": [],
        "outcome_tokens": [],
        "direction_tokens": [],
        "distance_tokens": [],
        "zone_tokens": [],
        "meta_labels": [],
    }


def _write_sources(root: Path) -> None:
    for name in (
        "player_surface.csv",
        "player_surface.xml",
        "goalkeeper_surface.csv",
        "goalkeeper_surface.xml",
        "team_surface.csv",
        "team_surface.xml",
    ):
        (root / name).write_text(f"source={name}\n", encoding="utf-8")


def _nucleus(
    *,
    nucleus_id: str,
    role: str,
    provider_id: str,
    label: str,
    status: str = "PASS",
    relation: str = "REFLECTION_CANDIDATE_EXACT",
    review_reasons: list[str] | None = None,
    mismatch_fields: list[str] | None = None,
) -> dict:
    prefix = {
        "PLAYER": "player_surface",
        "GOALKEEPER": "goalkeeper_surface",
        "TEAM": "team_surface",
    }[role]
    fields = {
        "start": "1.0",
        "end": "1.0",
        "code": "subject - " + label.casefold(),
        "team": "team candidate (10)",
        "action": label.casefold(),
        "half": "1",
        "pos_x": "10",
        "pos_y": "20",
    }
    if status == "REVIEW_REQUIRED":
        fields["pos_x"] = None
        fields["pos_y"] = None
    return {
        "row_nucleus_candidate_id": nucleus_id,
        "status": status,
        "source_role": role,
        "role_projection_candidate": {
            "PLAYER": "PLAYER_ACTOR_CANDIDATE",
            "GOALKEEPER": "GOALKEEPER_REACTION_ACTOR_CANDIDATE",
            "TEAM": "TEAM_CONTEXT_CANDIDATE",
        }[role],
        "provider_row_id_candidate": provider_id,
        "provider_row_id_is_validated_identity": False,
        "serialization_family_candidates": ["csv", "xml"],
        "serialization_relation_candidate": relation,
        "independence_status": "INDEPENDENCE_UNRESOLVED",
        "lineage_admission_status": (
            "LINEAGE_REVIEW_REQUIRED"
            if status == "REVIEW_REQUIRED"
            else "CANDIDATE_EXACT_VISIBLE_FIELDS"
        ),
        "lineage_review_reasons": (
            ["visible_field_serialization_discrepancy"]
            if status == "REVIEW_REQUIRED"
            else []
        ),
        "review_reasons": review_reasons or [],
        "mismatch_fields": mismatch_fields or [],
        "visible_field_candidates": {key: ([value] if value is not None else []) for key, value in fields.items()},
        "resolved_visible_fields": fields,
        "missing_required_visible_fields": [],
        "missing_coordinate_fields": (["pos_x", "pos_y"] if status == "REVIEW_REQUIRED" else []),
        "source_refs": [
            {
                "source_file": prefix + ".csv",
                "source_format": "csv",
                "source_role": role,
                "source_row_index": 5,
            },
            {
                "source_file": prefix + ".xml",
                "source_format": "xml",
                "source_role": role,
                "source_row_index": 5,
            },
        ],
        "source_timeline_evidence_only": True,
        "row_nucleus_is_canonical_event": False,
        "physical_action_identity_truth": False,
        "validated_event_identity": False,
        "independent_source_vote_allowed": False,
    }


def _payload() -> dict:
    nuclei = [
        _nucleus(
            nucleus_id="rn_player",
            role="PLAYER",
            provider_id="001",
            label="Passes accurate",
        ),
        _nucleus(
            nucleus_id="rn_gk",
            role="GOALKEEPER",
            provider_id="1",
            label="Shots saved",
        ),
        _nucleus(
            nucleus_id="rn_admin",
            role="TEAM",
            provider_id="900",
            label="start of the 1st half",
            status="REVIEW_REQUIRED",
            relation="REFLECTION_CANDIDATE_DISCREPANCY",
            review_reasons=[
                "coordinate_surface_unresolved_no_explicit_admin_exemption",
                "visible_field_serialization_discrepancy",
            ],
            mismatch_fields=["team"],
        ),
    ]
    return {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "content_source_role_bridge_status": "PASS",
        "filename_support_used_for_role_admission": False,
        "filename_role_used_for_nucleus_grouping": False,
        "xlsx_used_for_row_nucleus_identity": False,
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_pass_count": 2,
        "row_nucleus_review_required_count": 1,
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "physical_action_identity_truth": False,
        "independent_source_vote_allowed": False,
        "production_release": False,
    }


def test_one_current_nucleus_maps_to_one_atom_and_admin_review_is_preserved(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    result = mod.build_evidence_atom_inventory(_payload(), tmp_path, _registry())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["evidence_atom_count"] == 3
    assert result["source_row_nucleus_candidate_count"] == 3
    assert result["one_row_nucleus_one_evidence_atom_candidate"] is True
    admin = next(item for item in result["evidence_atoms"] if item["row_nucleus_candidate_id"] == "rn_admin")
    assert admin["atom_class"] == "ADMINISTRATIVE_ATOM"
    assert admin["atom_status"] == "REVIEW_REQUIRED"
    assert admin["downstream_eligibility"] == "ADMIN_ONLY"
    assert admin["action_eligible"] is False
    assert admin["sequence_eligible"] is False
    assert admin["spatial_eligible"] is False
    assert admin["metric_event_denominator_eligible"] is False
    assert admin["reflection_discrepancy_preserved"] is True
    assert admin["identity_not_applicable"] is True


def test_provider_id_representation_is_not_numeric_canonicalized(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    result = mod.build_evidence_atom_inventory(_payload(), tmp_path, _registry())
    player = next(item for item in result["evidence_atoms"] if item["row_nucleus_candidate_id"] == "rn_player")
    goalkeeper = next(item for item in result["evidence_atoms"] if item["row_nucleus_candidate_id"] == "rn_gk")
    assert player["provider_row_id_candidate"] == "001"
    assert goalkeeper["provider_row_id_candidate"] == "1"
    assert player["provider_row_id_candidate"] != goalkeeper["provider_row_id_candidate"]
    assert player["provider_row_id_representation_preserved"] is True


def test_dependent_csv_xml_reflection_does_not_add_independent_support_vote(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    result = mod.build_evidence_atom_inventory(_payload(), tmp_path, _registry())
    for atom in result["evidence_atoms"]:
        assert atom["independent_support_vote_count"] == 0
        assert atom["independent_source_vote_allowed"] is False
        assert atom["reflection_dependency_state"] == "DEPENDENT_SERIALIZATION_REFLECTION"
    assert result["dependent_reflection_adds_support_vote"] is False


def test_same_time_and_source_row_index_cannot_create_order(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    result = mod.build_evidence_atom_inventory(_payload(), tmp_path, _registry())
    assert result["source_row_index_is_temporal_order_truth"] is False
    assert result["same_time_artificial_order_allowed"] is False
    for atom in result["evidence_atoms"]:
        assert atom["same_time_link_allowed"] is False
        assert atom["negative_time_link_allowed"] is False
        assert atom["cross_period_link_allowed"] is False
        assert all(item["source_row_index_is_order_truth"] is False for item in atom["source_lineage_records"])


def test_xlsx_source_ref_is_rejected_from_evidence_atom_lineage(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    payload = _payload()
    payload["row_nuclei"][0]["source_refs"].append(
        {
            "source_file": "player_surface.xlsx",
            "source_format": "xlsx",
            "source_role": "PLAYER",
            "source_row_index": 5,
        }
    )
    (tmp_path / "player_surface.xlsx").write_text("aggregate only", encoding="utf-8")
    result = mod.build_evidence_atom_inventory(payload, tmp_path, _registry())
    assert result["status"] == "FAIL_CLOSED"
    assert result["evidence_atom_count"] == 0
    assert any("source_format_rejected:xlsx" in item for item in result["hard_block_hits"])


def test_filename_role_admission_reintroduction_fails_closed(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    payload = _payload()
    payload["filename_support_used_for_role_admission"] = True
    result = mod.build_evidence_atom_inventory(payload, tmp_path, _registry())
    assert result["status"] == "FAIL_CLOSED"
    assert "filename_role_admission_reintroduced" in result["hard_block_hits"]


def test_claim_ceiling_stays_closed(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    result = mod.build_evidence_atom_inventory(_payload(), tmp_path, _registry())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["physical_action_identity_truth"] is False
    assert result["validated_event_identity"] is False
    assert result["event_instance_allowed"] is False
    assert result["cross_role_fusion_allowed"] is False
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False
    assert result["phase_truth"] is False
    assert result["tactical_truth"] is False
    assert result["claim_allowed"] is False
    assert result["production_release"] is False


def test_nested_phone_output_is_rejected(tmp_path: Path) -> None:
    nested = tmp_path / "HPFA" / "nested"
    try:
        mod.validate_output_root(nested)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested HPFA output must be rejected")
