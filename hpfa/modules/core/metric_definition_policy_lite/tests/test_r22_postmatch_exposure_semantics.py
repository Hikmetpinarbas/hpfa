import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
REPORT_SRC = ROOT / "hpfa" / "modules" / "reporting" / "postmatch_analyst_report_lite" / "src"
sys.path.insert(0, str(REPORT_SRC))

from postmatch_analyst_report import raw_exposure_report, raw_fitness_report


def test_minutes_played_never_appears_in_raw_physical_cost_block():
    summary = {
        "physical_available": True,
        "record_count": 2,
        "surface_counts": {"PHYSICAL_COST_SURFACE": 1, "EXPOSURE_NORMALIZATION_SURFACE": 1},
        "metric_family_counts": {"DISTANCE_TOTAL": 1},
        "exposure_family_counts": {"MINUTES_PLAYED": 1},
    }
    physical_lines = raw_fitness_report(summary)
    exposure_lines = raw_exposure_report(summary)
    assert not any("MINUTES_PLAYED" in line for line in physical_lines)
    assert any("MINUTES_PLAYED_CANDIDATE=1" in line for line in exposure_lines)
    assert any("validated on-pitch minutes değildir" in line for line in exposure_lines)


def test_legacy_injected_minutes_field_is_not_rendered_as_physical_cost():
    summary = {
        "physical_available": True,
        "record_count": 2,
        "surface_counts": {"PHYSICAL_COST_SURFACE": 2},
        "metric_family_counts": {"DISTANCE_TOTAL": 1, "MINUTES_PLAYED": 1},
        "exposure_family_counts": {},
    }
    assert not any("MINUTES_PLAYED" in line for line in raw_fitness_report(summary))


def test_no_sample_match_identity_leak():
    source = (REPORT_SRC / "postmatch_analyst_report.py").read_text(encoding="utf-8")
    for token in ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "Galatasaray"]:
        assert token not in source
