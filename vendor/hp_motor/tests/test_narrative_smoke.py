from pathlib import Path
from hp_motor.pipeline import run_pipeline

def test_narrative_sections_present():
    report = run_pipeline(Path("tests/fixtures/events_min.json"))
    out = report["output_standard"]

    for k in ["findings", "reasons", "evidence", "actions", "risks_assumptions"]:
        assert k in out
        assert isinstance(out[k], list)
