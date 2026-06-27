import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "reporting" / "reasoning_grammar_spine_lite" / "src"
sys.path.insert(0, str(SRC))

from reasoning_grammar_spine import build_report, write_outputs


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def sample_postmatch():
    return {
        "team_comparison": {"left_team": "Team A", "right_team": "Team B"},
        "action_family_comparison": [
            {"metric": "PASS", "left": 120, "right": 80},
            {"metric": "CARRY_DRIBBLE", "left": 10, "right": 60},
            {"metric": "SHOT", "left": 8, "right": 6},
        ],
    }


def test_builds_primitive_candidates(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "postmatch_analyst_report_lite_v1.json", sample_postmatch())
    report = build_report(out)
    assert report["stage"] == "primitive_only"
    assert report["candidate_count"] == 6
    assert report["stage_gate"]["behaviour_candidate_allowed"] is False
    assert report["stage_gate"]["pattern_candidate_allowed"] is False
    assert any(item["primitive_candidate"] == "pass_surface_candidate" for item in report["primitive_candidates"])


def test_candidates_include_falsifier(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "postmatch_analyst_report_lite_v1.json", sample_postmatch())
    report = build_report(out)
    assert all(item.get("falsifier") for item in report["primitive_candidates"])


def test_write_outputs_flat_files(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "postmatch_analyst_report_lite_v1.json", sample_postmatch())
    report = write_outputs(out, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert (out / "reasoning_grammar_spine_lite_v1.json").exists()
    assert (out / "reasoning_grammar_spine_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/reasoning", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "reasoning_grammar_spine.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
