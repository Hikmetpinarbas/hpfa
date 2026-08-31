from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.rich_event_metric_primitives import run


def _write_surfaces(root: Path, *, receiver: str = "Player B", xml_end_x: str = "80") -> None:
    (root / "Match Players.csv").write_text(
        "ID,start,end,action,team,player,receiver,outcome,start_x,start_y,end_x,end_y,provider_qualifier\n"
        f"101,10,11,Pass,Team A,Player A,{receiver},successful,30,30,80,35,through\n",
        encoding="utf-8",
    )
    receiver_label = f"<label><group>receiver</group><text>{receiver}</text></label>" if receiver else ""
    (root / "Match Players.xml").write_text(
        "<file><ALL_INSTANCES><instance>"
        "<ID>101</ID><start>10</start><end>11</end>"
        "<label><group>action</group><text>Pass</text></label>"
        "<label><group>team</group><text>Team A</text></label>"
        "<label><group>player</group><text>Player A</text></label>"
        f"{receiver_label}"
        "<label><group>outcome</group><text>successful</text></label>"
        "<label><group>start_x</group><text>30</text></label>"
        "<label><group>start_y</group><text>30</text></label>"
        f"<label><group>end_x</group><text>{xml_end_x}</text></label>"
        "<label><group>end_y</group><text>35</text></label>"
        "<label><group>provider_qualifier</group><text>through</text></label>"
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


def test_geometry_direction_and_zone_transition_are_deterministic_candidates(tmp_path: Path) -> None:
    _write_surfaces(tmp_path)
    primitives = run(tmp_path)["primitives"]
    row = primitives["geometry_action_candidates"][0]
    assert row["forward_gain"] == 50.0
    assert row["direction_candidate"] == "FORWARD_CANDIDATE"
    assert row["origin_zone_candidate"] == "DEFENSIVE_THIRD:CENTRAL"
    assert row["destination_zone_candidate"] == "FINAL_THIRD:CENTRAL"
    assert row["geometric_third_skip_count"] == 1
    assert row["defensive_line_bypass_truth"] is False


def test_receiver_edge_requires_explicit_receiver(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, receiver="")
    primitives = run(tmp_path)["primitives"]
    assert primitives["pass_network_edge_count"] == 0


def test_cross_surface_semantic_conflict_withholds_geometry(tmp_path: Path) -> None:
    _write_surfaces(tmp_path, xml_end_x="75")
    result = run(tmp_path)
    item = result["projection"]["projections"][0]
    assert "end_x" in item["semantic_conflict_fields"]
    assert item["resolved_semantic_fields"]["end_x"] is None
    assert result["primitives"]["geometry_action_candidate_count"] == 0


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
