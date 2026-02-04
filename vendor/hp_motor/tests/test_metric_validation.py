from pathlib import Path
from hp_motor.pipeline import run_pipeline

def test_metrics_have_status_and_contract():
    report = run_pipeline(Path("tests/fixtures/events_min.json"))
    metrics = report["metrics_raw"]["metrics"]

    for mid, payload in metrics.items():
        assert "value" in payload
        assert "status" in payload
        assert payload["status"] in {"OK", "DEGRADED", "UNKNOWN"}
        assert "contract" in payload
        assert "layer" in payload["contract"]
