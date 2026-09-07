from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import _sequence_lineage_complete


NARRATIVE_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY"
FINDING_CEILING = "DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY"
NULL_CEILING = "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY"
BLOCK_FAMILY = "sequence_narrative_analyst_reading_candidate"


def _lineage():
    return {
        "trace_family_refs": ["TRACE_A"],
        "trace_variant_refs": ["TRACE_A", "TRACE_B"],
        "observed_support": 2,
        "dependency_summary": {"independent_support_count": "UNKNOWN"},
        "robustness_summary": {"state": "ROBUST_WITHIN_TESTED_RANGE"},
        "uncertainty": {"ordering": "ORDER_INDETERMINATE"},
        "withdrawal_condition": "withdraw_if_trace_cohort_or_dependency_changes",
        "upstream_claim_ceiling": NARRATIVE_CEILING,
        "origin_claim_ceiling": FINDING_CEILING,
        "null_contrast_summary": {
            "state": "EVALUATED",
            "observed_recurrence": 2,
            "null_median": 1.0,
            "uncorrected_upper_tail_probability": 0.1,
            "simulation_count": 9,
            "empirical_upper_tail_resolution": 0.1,
            "finite_simulation_resolution_only": True,
            "claim_strengthened": False,
            "claim_ceiling": NULL_CEILING,
            "multiple_testing_corrected": False,
            "significance_claim_allowed": False,
            "tactical_pattern_truth_allowed": False,
            "causality_allowed": False,
            "withdrawal_condition": "withdraw_if_null_model_or_trace_cohort_changes",
        },
    }


def test_user_output_accepts_exact_finite_simulation_resolution():
    assert _sequence_lineage_complete(BLOCK_FAMILY, _lineage()) is True


def test_user_output_rejects_invalid_simulation_count():
    lineage = _lineage()
    lineage["null_contrast_summary"]["simulation_count"] = 0
    assert _sequence_lineage_complete(BLOCK_FAMILY, lineage) is False


def test_user_output_rejects_tail_resolution_mismatch():
    lineage = _lineage()
    lineage["null_contrast_summary"]["empirical_upper_tail_resolution"] = 0.01
    assert _sequence_lineage_complete(BLOCK_FAMILY, lineage) is False


def test_user_output_rejects_finite_resolution_lock_breach():
    lineage = _lineage()
    lineage["null_contrast_summary"]["finite_simulation_resolution_only"] = False
    assert _sequence_lineage_complete(BLOCK_FAMILY, lineage) is False
