from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory import build_report


CSV_HEADER = "ID,start,end,code,team,action,half,pos_x,pos_y\n"


def write_pair(root: Path, stem: str, csv_rows: list[str], xml_instances: list[str]) -> None:
    (root / f"{stem}.csv").write_text(CSV_HEADER + "".join(csv_rows), encoding="utf-8")
    xml = "<file><ALL_INSTANCES>" + "".join(xml_instances) + "</ALL_INSTANCES></file>"
    (root / f"{stem}.xml").write_text(xml, encoding="utf-8")


def csv_row(
    row_id: str,
    action: str = "Pass",
    team: str = "Team A",
    x: str = "20",
    y: str = "30",
    start: str = "10",
    end: str = "11",
    half: str = "1",
) -> str:
    return f"{row_id},{start},{end},{team} - {action},{team},{action},{half},{x},{y}\n"


def xml_instance(
    row_id: str,
    action: str = "Pass",
    team: str = "Team A",
    x: str = "20",
    y: str = "30",
    start: str = "10",
    end: str = "11",
    half: str = "1",
) -> str:
    return f"""
    <instance>
      <ID>{row_id}</ID><start>{start}</start><end>{end}</end><code>{team} - {action}</code>
      <label><group>Team</group><text>{team}</text></label>
      <label><group>Action</group><text>{action}</text></label>
      <label><group>Half</group><text>{half}</text></label>
      <label><group>pos_x</group><text>{x}</text></label>
      <label><group>pos_y</group><text>{y}</text></label>
    </instance>
    """


def test_provider_id_representation_preserved(tmp_path: Path) -> None:
    write_pair(
        tmp_path,
        "Match Players",
        [csv_row("001"), csv_row("1")],
        [xml_instance("001"), xml_instance("1")],
    )
    report = build_report(tmp_path)
    ids = {item["provider_row_id_candidate"] for item in report["row_nuclei"]}
    assert ids == {"001", "1"}
    assert report["row_nucleus_candidate_count"] == 2
    assert report["provider_row_id_policy"] == "TEXT_CANDIDATE_NO_NUMERIC_CANONICALIZATION"


def test_dependent_reflection_not_double_counted(tmp_path: Path) -> None:
    write_pair(tmp_path, "Match Players", [csv_row("001")], [xml_instance("001")])
    (tmp_path / "Copy Players.csv").write_text(
        (tmp_path / "Match Players.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report = build_report(tmp_path)
    assert report["surface_row_count"] == 2
    assert report["row_nucleus_candidate_count"] == 1
    assert report["duplicate_surface_file_reflection_count"] == 1
    nucleus = report["row_nuclei"][0]
    assert nucleus["serialization_relation_candidate"] == "REFLECTION_CANDIDATE_EXACT"
    assert nucleus["independent_source_vote_allowed"] is False


def test_lineage_discrepancy_propagates_review(tmp_path: Path) -> None:
    write_pair(
        tmp_path,
        "Match Players",
        [csv_row("001", action="Pass")],
        [xml_instance("001", action="Long pass")],
    )
    report = build_report(tmp_path)
    nucleus = report["row_nuclei"][0]
    assert nucleus["status"] == "REVIEW_REQUIRED"
    assert nucleus["lineage_admission_status"] == "LINEAGE_REVIEW_REQUIRED"
    assert "action" in nucleus["mismatch_fields"]
    assert report["g01_g18_rollup"]["status"] == "REVIEW_REQUIRED"


def test_team_role_projects_to_context_not_actor(tmp_path: Path) -> None:
    write_pair(tmp_path, "Match Teams", [csv_row("10")], [xml_instance("10")])
    report = build_report(tmp_path)
    nucleus = report["row_nuclei"][0]
    assert nucleus["source_role"] == "TEAM"
    assert nucleus["role_projection_candidate"] == "TEAM_CONTEXT_CANDIDATE"


def test_same_anchor_multilabel_remains_separate_before_bundle(tmp_path: Path) -> None:
    write_pair(
        tmp_path,
        "Match Players",
        [csv_row("101", action="Pass"), csv_row("102", action="Passes accurate")],
        [xml_instance("101", action="Pass"), xml_instance("102", action="Passes accurate")],
    )
    report = build_report(tmp_path)
    assert report["row_nucleus_candidate_count"] == 2
    assert {item["provider_row_id_candidate"] for item in report["row_nuclei"]} == {"101", "102"}


def test_missing_coordinate_review_required_without_explicit_admin_exemption(tmp_path: Path) -> None:
    write_pair(
        tmp_path,
        "Match Players",
        [csv_row("201", x="", y="")],
        [xml_instance("201", x="", y="")],
    )
    report = build_report(tmp_path)
    nucleus = report["row_nuclei"][0]
    assert nucleus["status"] == "REVIEW_REQUIRED"
    assert "coordinate_surface_unresolved_no_explicit_admin_exemption" in nucleus["review_reasons"]
    g07 = next(item for item in report["g01_g18_rollup"]["gates"] if item["gate_id"] == "G07")
    assert g07["status"] == "REVIEW_REQUIRED"
    assert g07["evidence"]["admin_exemption_admitted"] is False


def test_xlsx_not_used_for_row_nucleus_identity(tmp_path: Path) -> None:
    write_pair(tmp_path, "Match Goalkeepers", [csv_row("301")], [xml_instance("301")])
    (tmp_path / "Match Goalkeepers.xlsx").write_bytes(b"not-an-event-surface")
    report = build_report(tmp_path)
    assert report["row_nucleus_candidate_count"] == 1
    assert report["xlsx_file_count"] == 1
    assert report["xlsx_used_for_row_nucleus_identity"] is False


def test_no_sample_match_identity_leak() -> None:
    src = Path(
        "hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "australia 2-0 turkey",
        "juventus fc 3-2 galatasaray",
        "sturm graz",
        "world cup 13.06.2026",
    )
    lowered = src.casefold()
    assert all(token not in lowered for token in forbidden)
