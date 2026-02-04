import json
from pathlib import Path
import pytest

from adapters.engine.unmapped_baseline import assert_no_new_actions


def test_baseline_gate(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"provider": "hp_engine", "provider_actions": ["A"]}), encoding="utf-8")

    report_ok = tmp_path / "report_ok.json"
    report_ok.write_text(json.dumps({
        "provider": "hp_engine",
        "generated_at_utc": "2026-02-04T12:00:00Z",
        "unmapped_actions": [{"provider_action": "A", "count": 999, "examples": []}]
    }), encoding="utf-8")
    assert_no_new_actions(report_path=report_ok, baseline_path=baseline)

    report_bad = tmp_path / "report_bad.json"
    report_bad.write_text(json.dumps({
        "provider": "hp_engine",
        "generated_at_utc": "2026-02-04T12:00:00Z",
        "unmapped_actions": [{"provider_action": "A", "count": 1, "examples": []},
                            {"provider_action": "B", "count": 1, "examples": []}]
    }), encoding="utf-8")

    with pytest.raises(AssertionError):
        assert_no_new_actions(report_path=report_bad, baseline_path=baseline)
