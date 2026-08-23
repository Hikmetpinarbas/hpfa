from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_metric_definition_policy_v1.sh"


def test_runner_binds_duplicate_group_count_to_current_inventory_key():
    text = RUNNER.read_text(encoding="utf-8")
    assert 'dup.get("exact_duplicate_group_count")' in text
    assert '"duplicate_reflection_group_count":duplicate_reflection_group_count' in text
    assert 'duplicate_reflection_group_count=' in text


def test_runner_preserves_current_duplicate_reflection_count_binding():
    text = RUNNER.read_text(encoding="utf-8")
    assert 'dup.get("duplicate_reflection_path_count")' in text
    assert 'dup.get("exact_duplicate_reflection_count", legacy_dup)' in text
