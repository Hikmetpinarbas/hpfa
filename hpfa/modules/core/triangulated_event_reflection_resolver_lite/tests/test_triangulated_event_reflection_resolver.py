import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "triangulated_event_reflection_resolver_lite" / "src"
sys.path.insert(0, str(SRC))

from triangulated_event_reflection_resolver import build_report, write_outputs


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["minute", "team", "player", "event_type", "x", "y"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_groups_same_action_across_surfaces(tmp_path):
    row = {"minute": 10, "team": "A", "player": "P1", "event_type": "Pass", "x": 25, "y": 40}
    write_csv(tmp_path / "a.csv", [row])
    write_csv(tmp_path / "b.csv", [row])
    report = build_report(tmp_path, root=ROOT)
    assert report["surface_row_count"] == 2
    assert report["reflection_group_count"] == 1
    assert report["multi_surface_group_count"] == 1
    assert report["true_action_count"] == "UNKNOWN"


def test_keeps_surface_rows_separate_from_candidate_groups(tmp_path):
    write_csv(tmp_path / "a.csv", [
        {"minute": 10, "team": "A", "player": "P1", "event_type": "Pass", "x": 25, "y": 40},
        {"minute": 11, "team": "A", "player": "P2", "event_type": "Shot", "x": 80, "y": 34},
    ])
    report = build_report(tmp_path, root=ROOT)
    assert report["surface_row_count"] == 2
    assert report["reflection_group_count"] == 2
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["action_count_claim_allowed"] is False


def test_flat_outputs(tmp_path):
    write_csv(tmp_path / "a.csv", [{"minute": 10, "team": "A", "player": "P1", "event_type": "Pass", "x": 25, "y": 40}])
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
