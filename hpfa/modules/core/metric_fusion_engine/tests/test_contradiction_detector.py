from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "metric_fusion_engine" / "src"
sys.path.insert(0, str(SRC))

from contradiction_detector import detect_metric_contradictions


def test_high_shots_low_box_actions_lowers_confidence():
    findings = detect_metric_contradictions({
        "M_SHOT_COUNT": 16,
        "M_ACTIONS_IN_BOX_COUNT": 4,
    })

    assert len(findings) == 1
    assert findings[0]["relation"] == "CONTRADICTS"
    assert findings[0]["claim_effect"] == "LOWER_CONFIDENCE"
    assert findings[0]["claim_safety"] == "EVIDENCE_ONLY"


def test_risky_progression_requires_context():
    findings = detect_metric_contradictions({
        "M_PROG_PASS_COUNT": 34,
        "M_TURNOVER_COUNT": 28,
    })

    assert len(findings) == 1
    assert findings[0]["relation"] == "CONTEXTUALIZES"
    assert findings[0]["claim_effect"] == "REQUIRE_CONTEXT"


def test_sterile_circulation_blocks_control_language():
    findings = detect_metric_contradictions({
        "M_PASS_COUNT": 510,
        "M_SEQUENCE_LENGTH": 11,
        "M_LOW_VALUE_LOOP_FRACTION": 0.72,
    })

    assert len(findings) == 1
    assert findings[0]["rule_id"] == "R_STERILE_CIRCULATION_CONTEXT"
    assert findings[0]["claim_effect"] == "BLOCK_CONTROL_LANGUAGE"


def test_no_findings_when_thresholds_not_met():
    findings = detect_metric_contradictions({
        "M_SHOT_COUNT": 9,
        "M_ACTIONS_IN_BOX_COUNT": 10,
        "M_PROG_PASS_COUNT": 18,
        "M_TURNOVER_COUNT": 10,
    })

    assert findings == []
