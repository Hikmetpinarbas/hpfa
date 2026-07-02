import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "field_semantic_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from field_semantic_reader import build_surface


def test_field_record_has_downstream_eligibility_seed():
    surface = build_surface([{"event_type": "pass", "period": "1", "outcome": "complete"}])
    for record in surface["field_semantic_records"]:
        assert "required_for_modules" in record
        assert "downstream_fail_action" in record
        assert "decision_state_seed" in record
        assert "claim_boundary" in record


def test_known_field_routes_to_candidate_use():
    surface = build_surface([{"event_type": "pass"}])
    record = surface["field_semantic_records"][0]
    assert record["semantic_family"] == "action"
    assert record["downstream_fail_action"] == "ALLOW_CANDIDATE"


def test_unknown_action_routes_to_audit_only():
    surface = build_surface([{"vendor_blob": "x"}])
    record = surface["field_semantic_records"][0]
    assert record["semantic_family"] == "unknown"
    assert record["downstream_fail_action"] == "AUDIT_ONLY"
    assert record["decision_state_seed"] == "REVIEW_REQUIRED"


def test_missing_period_blocks_sequence_analysis_seed():
    surface = build_surface([{"event_type": "pass", "team": "A"}])
    period_records = [r for r in surface["field_semantic_records"] if r["normalized_column"] == "period"]
    assert period_records == []
    assert surface["status"] == "REVIEW_REQUIRED"


def test_no_sample_match_identity_leak_downstream_file():
    src = (SRC / "field_semantic_reader.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
