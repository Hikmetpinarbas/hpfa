from pathlib import Path

from hp_motor.pipeline import run_pipeline


def test_segmentation_counts_present():
    report = run_pipeline(Path("tests/fixtures/events_min.json"))

    es = report["events_summary"]
    assert "n_possessions" in es
    assert "n_sequences" in es

    assert es["n_possessions"] >= 1
    assert es["n_sequences"] >= 1
