from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.rich_event_metric_primitives import run


def _write_surfaces(
    root: Path,
    *,
    receiver: str = "Player B",
    xml_end_x: str = "80",
    provider_id: str = "101",
    stem: str = "Match Players",
    coordinate_system: str = "105x68",
    pitch_length: str = "105",
    pitch_width: str = "68",
    attacking_direction: str = "LEFT_TO_RIGHT",
    period: str = "1",
    coordinate_system_admission_status: str = "ADMITTED",
    attacking_direction_admission_status: str = "ADMITTED",
    start_y: str = "30",
    end_y: str = "35",
) -> None:
    (root / f"{stem}.csv").write_text(
        "ID,start,end,action,team,player,receiver,outcome,period,start_x,start_y,end_x,end_y,coordinate_system,pitch_length,pitch_width,attacking_direction,coordinate_system_admission_status,attacking_direction_admission_status,provider_qualifier\n"
        f"{provider_id},10,11,Pass,Team A,Player A,{receiver},successful,{period},30,{start_y},80,{end_y},{coordinate_system},{pitch_length},{pitch_width},{attacking_direction},{coordinate_system_admission_status},{attacking_direction_admission_status},through\n",
        encoding="utf-8",
    )
    receiver_label = f"<label><group>receiver</group><text>{receiver}</text></label>" if receiver else ""
    id_xml = f"<ID>{provider_id}</ID>" if provider_id else ""
    labels = [
        ("action", "Pass"), ("team", "Team A"), ("player", "Player A"),
        ("outcome", "successful"), ("period", period), ("start_x", "30"), ("start_y", start_y),
        ("end_x", xml_end_x), ("end_y", end_y),
        ("coordinate_system", coordinate_system), ("pitch_length", pitch_length),
        ("pitch_width", pitch_width), ("attacking_direction", attacking_direction),
        ("coordinate_system_admission_status", coordinate_system_admission_status),
        ("attacking_direction_admission_status", attacking_direction_admission_status),
        ("provider_qualifier", "through"),
    ]
    label_xml = "".join(
        f"<label><group>{group}</group><text>{value}</text></label>"
        for group, value in labels if value != ""
    )
    (root / f"{stem}.xml").write_text(
        "<file><ALL_INSTANCES><instance>"
        f"{id_xml}<start>10</start><end>11</end>{label_xml}{receiver_label}"
        "</instance></ALL_INSTANCES></file>",
        encoding="utf-8",
    )


def test_lossless_projection_preserves_unmapped_provider_field(tmp_path: Path) -> None:
    _write_surfaces(tmp_path)
    result = run(tmp_path)
    projection = result["projection"]
    assert projection["projection_count"] == 1
    item = projection["projections"][0]
    assert "provider_qualifier" in item["raw_field_union"]
    assert item["reflection_surface_count"] == 2
    assert item["independent_source_vote_allowed"] is False
    assert item["aggregate_primitives_eligible"] is True


def test_csv_xml_reflection_does_not_double_geometry_or_pass_edge(tmp_path: Path) -> None:
    _write_surfaces(tmp_path)
    primitives = run(tmp_path)["primitives"]
    assert primitives["geometry_action_candidate_count"] == 1
    assert primitives["pass_network_edge_count"] == 1
    edge = primitives["pass_network_edges"][0]
    assert edge["explicit_edge_count"] == 1
    assert edge["passer_candidate"] == "Player A"
    assert edge["receiver_candidate"] == "Player B"
    assert edge["receiver_edge_basis"] == "EXPLICIT_RECEIVER_FIELD_ONLY"


def test_geometry_direction_and_zone_transition_require_admitted_coordinate_context(tmp_path: Path) -> None:
    _write_surfaces(tmp_path)
    primitives = run(tmp_path)["primitives"]
    row = primitives["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] == 50.0
    assert row["forward_gain"] == 50.0
    assert row["direction_candidate"] == "FORWARD_CANDIDATE"
    assert row["origin_zone_candidate"] == "DEFENSIVE_THIRD:CENTRAL"
    assert row["destination_zone_candidate"] == "FINAL_THIRD:CENTRAL"
    assert row["geometric_third_skip_count"] == 1
    assert row["defensive_line_bypass_truth"] is False
    assert primitives["zone_transition_matrix_candidates"][0]["zone_basis"] == "ATTACKING_DIRECTION_NORMALIZED_DECLARED_COORDINATE_SYSTEM"


def test_receiver_edge_requires_explicit_receiver(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, receiver="")
    primitives = run(tmp_path)["primitives"]
    assert primitives["pass_network_edge_count"] == 0


def test_cross_surface_semantic_conflict_withholds_only_dependent_geometry(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, xml_end_x="75")
    result = run(tmp_path)
    item = result["projection"]["projections"][0]
    assert "end_x" in item["semantic_conflict_fields"]
    assert item["resolved_semantic_fields"]["end_x"] is None
    row = result["primitives"]["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] is None
    assert row["raw_y_displacement"] == 5.0
    assert row["forward_gain"] is None
    assert row["euclidean_displacement"] is None
    assert row["direction_angle_degrees"] is None
    assert row["origin_zone_candidate"] is None
    assert row["destination_zone_candidate"] is None


def test_provider_ids_are_scoped_to_source_namespace_not_unknown_role(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, stem="Base Export", receiver="Player B")
    _write_surfaces(tmp_path, stem="Base Export (1)", receiver="Player C")
    result = run(tmp_path)
    assert result["projection"]["projection_count"] == 2
    namespaces = {item["source_namespace"] for item in result["projection"]["projections"]}
    assert namespaces == {"base_export", "base_export_(1)"}
    edges = {(row["passer_candidate"], row["receiver_candidate"], row["explicit_edge_count"]) for row in result["primitives"]["pass_network_edges"]}
    assert edges == {("Player A", "Player B", 1), ("Player A", "Player C", 1)}


def test_missing_provider_id_withholds_cross_format_aggregate_primitives(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, provider_id="")
    result = run(tmp_path)
    assert result["projection"]["projection_count"] == 2
    assert all(item["aggregate_primitives_eligible"] is False for item in result["projection"]["projections"])
    assert result["primitives"]["geometry_action_candidate_count"] == 0
    assert result["primitives"]["pass_network_edge_count"] == 0
    assert result["primitives"]["withheld_primitive_counts"]["identity_unreconciled"] == 2


def test_coordinate_semantics_are_withheld_without_explicit_coordinate_system(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, coordinate_system="", pitch_length="", pitch_width="", attacking_direction="")
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] == 50.0
    assert row["coordinate_system_admitted"] is False
    assert row["euclidean_displacement"] is None
    assert row["forward_gain"] is None
    assert row["direction_candidate"] is None
    assert row["origin_zone_candidate"] is None
    assert row["destination_zone_candidate"] is None


def test_raw_coordinate_fields_do_not_self_admit_coordinate_semantics(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, coordinate_system_admission_status="")
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] == 50.0
    assert row["coordinate_system_admitted"] is False
    assert row["euclidean_displacement"] is None
    assert row["forward_gain"] is None
    assert row["origin_zone_candidate"] is None


def test_direction_requires_explicit_admission_status(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, attacking_direction_admission_status="")
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["coordinate_system_admitted"] is True
    assert row["attacking_direction_admitted"] is False
    assert row["euclidean_displacement"] is not None
    assert row["forward_gain"] is None
    assert row["direction_candidate"] is None
    assert row["origin_zone_candidate"] is None


def test_direction_requires_team_period_source_scope(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, period="")
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["period_candidate"] is None
    assert row["attacking_direction_admitted"] is False
    assert row["forward_gain"] is None
    assert row["origin_zone_candidate"] is None


def test_attacking_direction_normalization_prevents_raw_plus_x_forward_claim(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, attacking_direction="RIGHT_TO_LEFT")
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] == 50.0
    assert row["forward_gain"] == -50.0
    assert row["direction_candidate"] == "BACKWARD_CANDIDATE"
    assert row["origin_zone_candidate"] == "FINAL_THIRD:CENTRAL"
    assert row["destination_zone_candidate"] == "DEFENSIVE_THIRD:CENTRAL"


def test_declared_normalized_coordinate_system_scales_zone_boundaries(tmp_path: Path) -> None:
    _write_surfaces(
        tmp_path,
        coordinate_system="0-100",
        pitch_length="",
        pitch_width="",
        attacking_direction="LEFT_TO_RIGHT",
        start_y="25",
        end_y="25",
    )
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["pitch_length"] == 100.0
    assert row["pitch_width"] == 100.0
    assert row["origin_zone_candidate"] == "DEFENSIVE_THIRD:LEFT"
    assert row["destination_zone_candidate"] == "FINAL_THIRD:LEFT"


def test_x_only_primitive_is_not_suppressed_by_missing_y_coordinates(tmp_path: Path) -> None:
    (tmp_path / "X Only.csv").write_text(
        "ID,action,team,player,period,start_x,end_x,coordinate_system,pitch_length,pitch_width,attacking_direction,coordinate_system_admission_status,attacking_direction_admission_status\n"
        "7,Pass,Team A,Player A,1,20,60,105x68,105,68,LEFT_TO_RIGHT,ADMITTED,ADMITTED\n",
        encoding="utf-8",
    )
    row = run(tmp_path)["primitives"]["geometry_action_candidates"][0]
    assert row["raw_x_displacement"] == 40.0
    assert row["forward_gain"] == 40.0
    assert row["euclidean_displacement"] is None
    assert row["direction_angle_degrees"] is None
    assert row["origin_zone_candidate"] is None


def test_no_canonical_event_or_physical_truth_promotion(tmp_path: Path) -> None:
    _write_surfaces(tmp_path)
    result = run(tmp_path)
    assert result["projection"]["canonical_event_count"] == "UNKNOWN"
    assert result["projection"]["true_action_count"] == "UNKNOWN"
    assert result["primitives"]["canonical_event_count"] == "UNKNOWN"
    assert result["primitives"]["true_action_count"] == "UNKNOWN"
    assert result["primitives"]["pass_network_is_team_shape_truth"] is False
    assert result["primitives"]["geometric_skip_is_defensive_line_bypass_truth"] is False


def test_no_sample_match_identity_leak() -> None:
    src = Path("hpfa/modules/core/active_match_spine_runner/src/rich_event_metric_primitives.py").read_text(encoding="utf-8").casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "galatasaray", "besiktas", "turkey 3-2 united states")
    assert all(token not in src for token in forbidden)
