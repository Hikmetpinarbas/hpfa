import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
sys.path.insert(0, str(SRC))

from minimum_viable_context import build_report, write_outputs


def test_semicolon_csv_context_extraction(tmp_path):
    path = tmp_path / "surface.csv"
    path.write_text("minute;team;action;pos_x;pos_y\n10;A;Pass;80;50\n", encoding="utf-8")
    report = build_report(tmp_path, root=ROOT)
    sample = report["context_candidates_sample"][0]
    assert report["surface_row_count"] == 1
    assert sample["action_family"] == "PASS"
    assert sample["zone_candidate"] == "FINAL_THIRD"
    assert sample["channel_candidate"] == "RIGHT_CHANNEL"
    assert sample["context_completeness"] == "high"


def test_previous_next_action_context(tmp_path):
    path = tmp_path / "surface.csv"
    path.write_text(
        "minute,team,action,x,y\n10,A,Pass,50,34\n11,A,Shot,80,34\n",
        encoding="utf-8",
    )
    report = build_report(tmp_path, root=ROOT)
    sample = report["context_candidates_sample"]
    assert sample[0]["next_action_family"] == "SHOT"
    assert sample[1]["previous_action_family"] == "PASS"


def test_claim_boundaries_remain_false(tmp_path):
    path = tmp_path / "surface.csv"
    path.write_text("minute,team,action,x,y\n10,A,Pass,50,34\n", encoding="utf-8")
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False
    assert report["tactical_truth"] is False
    assert report["claim_allowed"] is False


def test_flat_outputs(tmp_path):
    path = tmp_path / "surface.csv"
    path.write_text("minute,team,action,x,y\n10,A,Pass,50,34\n", encoding="utf-8")
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "minimum_viable_context_lite_v1.json").exists()
    assert (out / "minimum_viable_context_lite_v1.txt").exists()
    assert report["claim_safety"] == "CONTEXT_CANDIDATE_ONLY"


def test_no_sample_match_identity_leak():
    src = (SRC / "minimum_viable_context.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "minimum_viable_context_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
        assert token not in contract
