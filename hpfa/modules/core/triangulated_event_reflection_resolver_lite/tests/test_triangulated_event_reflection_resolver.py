import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "triangulated_event_reflection_resolver_lite" / "src"
sys.path.insert(0, str(SRC))

from triangulated_event_reflection_resolver import build_report, read_xml, write_outputs


def write_csv(path: Path, rows):
    fields = ["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_xml(path: Path, rows):
    parts = ["<file>"]
    for row in rows:
        parts.extend([
            "<instance>",
            f"<ID>{row['ID']}</ID>",
            f"<start>{row['start']}</start>",
            f"<end>{row['end']}</end>",
            f"<code>{row['code']}</code>",
            f"<label><group>Team</group><text>{row['team']}</text></label>",
            f"<label><group>Action</group><text>{row['action']}</text></label>",
            f"<label><group>Half</group><text>{row['half']}</text></label>",
            f"<label><group>pos_x</group><text>{row['pos_x']}</text></label>",
            f"<label><group>pos_y</group><text>{row['pos_y']}</text></label>",
            "</instance>",
        ])
    parts.append("</file>")
    path.write_text("".join(parts), encoding="utf-8")


def base_row(action="Passes accurate", start="10.0", x="25"):
    return {"ID": "7", "start": start, "end": "10.5", "code": "P1", "team": "A", "action": action, "half": "1", "pos_x": x, "pos_y": "40"}


def test_groups_same_action_across_surfaces(tmp_path):
    row = base_row()
    write_csv(tmp_path / "Full match Players.csv", [row])
    write_xml(tmp_path / "Full match Players.xml", [row])
    report = build_report(tmp_path, root=ROOT)
    assert report["surface_row_count"] == 2
    assert report["reflection_group_count"] == 1
    assert report["multi_surface_group_count"] == 1
    assert report["true_action_count"] == "UNKNOWN"


def test_exact_csv_xml_multiset_equivalence(tmp_path):
    row = base_row()
    write_csv(tmp_path / "Full match Players.csv", [row])
    write_xml(tmp_path / "Full match Players.xml", [row])
    report = build_report(tmp_path, root=ROOT)
    assert report["decision"] == "EXACT_VISIBLE_FIELD_MULTISET_EQUIVALENCE"
    assert report["serialization_exact_role_count"] == 1
    audit = report["serialization_role_audits"][0]
    assert audit["matched_surface_row_count"] == 1
    assert audit["discrepancy_count"] == 0
    assert audit["independent_source_vote_allowed"] is False


def test_nearby_time_or_coordinate_is_not_bucket_merged(tmp_path):
    write_csv(tmp_path / "Full match Players.csv", [base_row(start="10.0", x="25")])
    write_xml(tmp_path / "Full match Players.xml", [base_row(start="10.1", x="25.1")])
    report = build_report(tmp_path, root=ROOT)
    assert report["decision"] == "VISIBLE_FIELD_SERIALIZATION_DISCREPANCY"
    assert report["reflection_group_count"] == 2
    assert report["serialization_discrepancy_role_count"] == 1


def test_multi_label_same_anchor_is_not_collapsed_into_one_action(tmp_path):
    rows = [base_row(action="Passes accurate"), base_row(action="Progressive passes accurate")]
    write_csv(tmp_path / "Full match Players.csv", rows)
    write_xml(tmp_path / "Full match Players.xml", rows)
    report = build_report(tmp_path, root=ROOT)
    assert report["reflection_group_count"] == 2
    assert report["surface_row_count"] == 4
    assert report["true_action_count"] == "UNKNOWN"
    assert report["physical_action_identity_truth"] is False


def test_duplicate_same_content_file_is_reflection_not_extra_volume(tmp_path):
    row = base_row()
    first = tmp_path / "Full match Players.csv"
    duplicate = tmp_path / "Copy Players.csv"
    write_csv(first, [row])
    shutil.copyfile(first, duplicate)
    write_xml(tmp_path / "Full match Players.xml", [row])
    report = build_report(tmp_path, root=ROOT)
    assert report["surface_file_count"] == 3
    assert report["unique_surface_file_count"] == 2
    assert report["duplicate_surface_file_reflection_count"] == 1
    assert report["surface_row_count"] == 2


def test_xml_group_text_labels_map_to_canonical_fields(tmp_path):
    row = base_row()
    path = tmp_path / "Full match Goalkeepers.xml"
    write_xml(path, [row])
    parsed = read_xml(path)
    assert parsed[0]["provider_row_id"] == "7"
    assert parsed[0]["action"] == "passes accurate"
    assert parsed[0]["team"] == "a"
    assert parsed[0]["pos_x"] == "25"
    assert parsed[0]["_source_role"] == "GOALKEEPER"


def test_keeps_surface_rows_separate_from_candidate_groups(tmp_path):
    write_csv(tmp_path / "Full match Players.csv", [base_row(), {**base_row(), "ID": "8", "start": "11", "end": "11.5", "code": "P2", "action": "Shot"}])
    report = build_report(tmp_path, root=ROOT)
    assert report["surface_row_count"] == 2
    assert report["reflection_group_count"] == 2
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["action_count_claim_allowed"] is False


def test_counts_and_claims_remain_fail_closed(tmp_path):
    write_csv(tmp_path / "Full match Players.csv", [base_row()])
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["action_count_claim_allowed"] is False
    assert report["same_upstream_origin_truth"] is False
    assert report["independent_source_vote_allowed"] is False


def test_flat_outputs(tmp_path):
    write_csv(tmp_path / "Full match Players.csv", [base_row()])
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "triangulated_event_reflection_resolver_lite_v1.json").exists()
    assert (out / "triangulated_event_reflection_resolver_lite_v1.txt").exists()
    assert report["reflection_group_truth"] is False


def test_no_sample_match_identity_leak():
    src = (SRC / "triangulated_event_reflection_resolver.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "triangulated_event_reflection_resolver_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
        assert token not in contract
