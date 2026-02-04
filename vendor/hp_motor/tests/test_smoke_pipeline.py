from pathlib import Path

from hp_motor.pipeline import run_pipeline


def test_smoke_pipeline_generates_report():
    events_path = Path("tests/fixtures/events_min.json")
    report = run_pipeline(events_path=events_path, vendor="generic")

    # core keys
    assert "hp_motor_version" in report
    assert "ontology_version" in report
    assert "popper" in report
    assert "events_summary" in report
    assert "metrics_raw" in report
    assert "metrics_adjusted" in report
    assert "context_flags" in report
    assert "output_standard" in report

    # popper status sanity
    assert report["popper"]["status"] in {"OK", "DEGRADED", "BLOCKED"}
