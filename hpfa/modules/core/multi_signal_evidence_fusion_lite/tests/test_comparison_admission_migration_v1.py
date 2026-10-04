import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "src"
sys.path.insert(0, str(SRC))

from multi_signal_evidence_fusion import fuse_packet


def _packet(signal):
    return {
        "packet_id": "comparison_migration_001",
        "packet_family": "progression",
        "input_features": ["feature_001"],
        "input_windows": ["window_001"],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": ["support_001"],
        "contradicting_signals": [signal],
        "claim_ceiling": "composite_candidate_only",
        "claim_output_allowed": False,
        "report_language_allowed": False,
    }


def _admitted_signal():
    return {
        "signal_id": "counter_001",
        "relation_type": "CONTRADICTS",
        "contradiction_basis": "comparable opposite visible outcome",
        "comparison_question_id": "progression_terminal_outcome",
        "comparison_unit": "episode_candidate",
        "exact_dimensions": ["team", "game_state", "start_zone"],
        "coarsened_dimensions": [],
        "test_dimensions": ["terminal_outcome"],
        "forbidden_leakage_dimensions": ["terminal_outcome"],
        "reference_context": {
            "team": "TEAM_A",
            "game_state": "LEVEL",
            "start_zone": "MIDDLE_THIRD",
        },
        "candidate_context": {
            "team": "TEAM_A",
            "game_state": "LEVEL",
            "start_zone": "MIDDLE_THIRD",
        },
        "reference_outcome": "SHOT_ENDING",
        "candidate_outcome": "LOSS",
        "outcome_relation": "OPPOSITE",
        "provenance_root": "candidate_root",
        "dependency_group": "candidate_dep",
        "independence_group": "candidate_ind",
        "reference_provenance_root": "reference_root",
        "reference_dependency_group": "reference_dep",
        "reference_independence_group": "reference_ind",
        "independence_admission_status": "ADMITTED",
        "independence_admission_basis": "fixture_explicit_independence_contract",
    }


def test_declared_contradiction_without_comparison_contract_is_not_counterevidence():
    signal = {
        "signal_id": "legacy_contradiction",
        "relation_type": "CONTRADICTS",
        "contradiction_basis": "legacy declaration only",
    }
    record = fuse_packet(_packet(signal))
    row = next(row for row in record["relation_records"] if row["signal_ref"] == "legacy_contradiction")
    assert record["contradiction_signal_count"] == 0
    assert row["relation_type"] == "QUALIFIES"
    assert row["comparison_status"] == "NOT_EVALUATED"
    assert row["counterevidence_class"] == "UNRESOLVED"


def test_comparable_opposite_dependency_separated_outcome_is_counterevidence():
    record = fuse_packet(_packet(_admitted_signal()))
    row = next(row for row in record["relation_records"] if row["signal_ref"] == "counter_001")
    assert record["contradiction_signal_count"] == 1
    assert record["admitted_counterevidence_count"] == 1
    assert row["relation_type"] == "CONTRADICTS"
    assert row["counterevidence_class"] == "COUNTEREVIDENCE"


def test_missing_outcome_remains_unresolved():
    signal = _admitted_signal()
    signal["candidate_outcome"] = "UNRESOLVED"
    record = fuse_packet(_packet(signal))
    assert record["contradiction_signal_count"] == 0
    assert record["unresolved_counterevidence_count"] == 1


def test_same_dependency_is_dependency_challenge_not_counterevidence():
    signal = _admitted_signal()
    signal["reference_provenance_root"] = "candidate_root"
    record = fuse_packet(_packet(signal))
    assert record["contradiction_signal_count"] == 0
    assert record["dependency_challenge_count"] == 1


def test_exact_context_mismatch_is_not_counterevidence():
    signal = _admitted_signal()
    signal["candidate_context"]["start_zone"] = "FINAL_THIRD"
    record = fuse_packet(_packet(signal))
    row = next(row for row in record["relation_records"] if row["signal_ref"] == "counter_001")
    assert record["contradiction_signal_count"] == 0
    assert row["comparison_status"] == "CONTEXT_MISMATCH"


def test_outcome_leakage_invalidates_comparison_contract():
    signal = _admitted_signal()
    signal["exact_dimensions"].append("terminal_outcome")
    record = fuse_packet(_packet(signal))
    row = next(row for row in record["relation_records"] if row["signal_ref"] == "counter_001")
    assert record["contradiction_signal_count"] == 0
    assert row["comparison_status"] == "INVALID_COMPARISON_CONTRACT"


def test_same_outcome_is_non_support_not_support():
    signal = _admitted_signal()
    signal["candidate_outcome"] = "SHOT_ENDING"
    signal["outcome_relation"] = "SAME"
    record = fuse_packet(_packet(signal))
    assert record["contradiction_signal_count"] == 0
    assert record["non_support_count"] == 1
    assert record["support_signal_count"] == 1
