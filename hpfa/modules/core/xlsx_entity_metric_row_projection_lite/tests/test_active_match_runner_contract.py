from pathlib import Path


RUNNER = (
    Path(__file__).resolve().parents[5]
    / "tools"
    / "run_active_match_xlsx_entity_metric_row_projection_v1.sh"
)


def test_active_match_runner_requires_exact_expected_head():
    text = RUNNER.read_text(encoding="utf-8")

    required_fragments = (
        'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"',
        'fail "expected_head_not_set"',
        'fail "invalid_expected_head:$EXPECTED_HEAD"',
        'fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"',
        'payload["runtime_expected_head_sha"] = expected_head',
        '"exact_head_match": head.casefold() == expected_head.casefold()',
    )
    for fragment in required_fragments:
        assert fragment in text

    head_guard = text.index('fail "unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD"')
    active_match_execution = text.index("python xlsx_entity_metric_row_projection_lite.py")
    assert head_guard < active_match_execution


def test_active_match_runner_preserves_flat_phone_output_guard():
    text = RUNNER.read_text(encoding="utf-8")
    assert "/sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA" in text
    assert 'fail "nested_phone_output_directory_rejected"' in text
