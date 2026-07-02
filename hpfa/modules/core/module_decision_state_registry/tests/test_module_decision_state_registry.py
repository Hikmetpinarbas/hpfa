import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "module_decision_state_registry" / "src"
sys.path.insert(0, str(SRC))

from module_decision_state_registry import build_decision, validate_decision


def test_status_has_release_status():
    record = build_decision("sample_module", "READY", "ready for next layer")
    assert record["release_status"] == "REVIEW_REQUIRED"
    assert record["validation"]["valid"] is True


def test_blocked_lists_downstream_modules():
    record = {
        "module_id": "sample_module",
        "decision_state": "BLOCKED",
        "reason": "missing input",
        "release_status": "REVIEW_REQUIRED",
        "blocked_downstream_modules": [],
    }
    result = validate_decision(record)
    assert result["valid"] is False
    assert "blocked_state_requires_downstream_list" in result["errors"]


def test_warning_has_reason():
    result = validate_decision({
        "module_id": "sample_module",
        "decision_state": "READY_WITH_WARNINGS",
        "reason": "",
        "release_status": "REVIEW_REQUIRED",
    })
    assert result["valid"] is False
    assert "missing_reason" in result["errors"]


def test_invalid_state_rejected():
    result = validate_decision({
        "module_id": "sample_module",
        "decision_state": "PASS",
        "reason": "legacy state",
        "release_status": "REVIEW_REQUIRED",
    })
    assert result["valid"] is False
    assert "invalid_decision_state" in result["errors"]


def test_no_sample_match_identity_leak():
    src = (SRC / "module_decision_state_registry.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
