import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "data_quality_gate" / "src"
sys.path.insert(0, str(SRC))

from gate_report_reader import load_gate_report, get_gate_status, get_degraded_reasons
from downstream_policy import is_downstream_allowed, assert_downstream_allowed, DownstreamPolicyError


def write_report(tmp_path, status="PASS", next_action=None, findings=None):
    if next_action is None:
        next_action = {
            "phase_sequence_allowed": status != "FAIL_CLOSED",
            "metric_layer_allowed": True if status == "PASS" else False,
            "claim_layer_allowed": False,
            "reason": "test policy",
        }
    if findings is None:
        findings = [
            {
                "gate_id": "G00_PARSE",
                "status": status,
                "message": "test finding",
                "evidence": {},
            }
        ]

    report = {
        "tool": "hpfa_data_quality_gate_v1",
        "status": status,
        "input": "runtime/active_single_match/current/events.csv",
        "input_format": "csv",
        "row_count": 3,
        "valid_row_count": 3,
        "claim_safety": "NO_FOOTBALL_CLAIMS_EMITTED",
        "authority_note": "test authority note",
        "next_action": next_action,
        "findings": findings,
    }
    path = tmp_path / "gate_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_pass_allows_phase_sequence_and_metric(tmp_path):
    path = write_report(tmp_path, status="PASS")
    report = load_gate_report(path)

    assert get_gate_status(report) == "PASS"
    assert is_downstream_allowed(report, "phase_sequence")
    assert is_downstream_allowed(report, "metric")
    assert not is_downstream_allowed(report, "claim")


def test_fail_closed_blocks_downstream(tmp_path):
    path = write_report(tmp_path, status="FAIL_CLOSED")
    report = load_gate_report(path)

    assert not is_downstream_allowed(report, "phase_sequence")
    assert not is_downstream_allowed(report, "metric")
    assert not is_downstream_allowed(report, "claim")


def test_degraded_requires_degraded_mode(tmp_path):
    path = write_report(
        tmp_path,
        status="DEGRADED",
        next_action={
            "phase_sequence_allowed": True,
            "metric_layer_allowed": "CONDITIONAL",
            "claim_layer_allowed": False,
            "reason": "degraded test",
        },
        findings=[
            {
                "gate_id": "G03_COORDINATE",
                "status": "DEGRADED",
                "message": "Coordinate columns missing.",
                "evidence": {"x_col": None, "y_col": None},
            }
        ],
    )
    report = load_gate_report(path)

    assert not is_downstream_allowed(report, "phase_sequence")
    assert is_downstream_allowed(report, "phase_sequence", degraded_mode=True)
    assert get_degraded_reasons(report)[0]["gate_id"] == "G03_COORDINATE"


def test_assert_blocks_claim_layer(tmp_path):
    path = write_report(tmp_path, status="PASS")
    report = load_gate_report(path)

    try:
        assert_downstream_allowed(report, "claim")
    except DownstreamPolicyError:
        return

    raise AssertionError("Claim layer must remain blocked.")
