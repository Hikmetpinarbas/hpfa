from pathlib import Path
from adapters.engine.unmapped_baseline import assert_no_new_actions


def test_repo_report_has_no_new_actions_vs_baseline():
    root = Path(__file__).resolve().parents[2]
    report_path = root / "reports" / "unmapped_actions.json"
    baseline_path = root / "reports" / "unmapped_actions.baseline.json"
    assert report_path.exists()
    assert baseline_path.exists()
    assert_no_new_actions(report_path=report_path, baseline_path=baseline_path)
