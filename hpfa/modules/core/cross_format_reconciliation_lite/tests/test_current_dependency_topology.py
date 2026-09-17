import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SPEC = importlib.util.spec_from_file_location(
    "cross_format_reconciliation_current_entry",
    ROOT / "cross_format_reconciliation_lite.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_format_dependency_typing_keeps_reflection_and_aggregate_non_independent():
    payload = {
        "pair_reports": [
            {
                "decision": "PASS_ALIGNMENT_CANDIDATE",
                "xlsx_support": {
                    "source_dependency_status": "DERIVATION_DEPENDENCY_UNRESOLVED",
                    "independent_confirmation_allowed": False,
                },
            },
            {
                "decision": "REVIEW_REQUIRED_MISMATCH",
                "xlsx_support": {},
            },
        ]
    }

    out = MODULE._attach_format_dependency_topology(payload)

    assert out["pair_reports"][0]["dependency_type"] == "SERIALIZATION_REFLECTION"
    assert out["pair_reports"][0]["independent_support_allowed"] is False
    assert out["pair_reports"][0]["reflection_equivalence_truth"] is False
    assert out["pair_reports"][0]["xlsx_support"]["dependency_type"] == "AGGREGATE_DERIVATION_UNRESOLVED"
    assert out["pair_reports"][0]["xlsx_support"]["independent_confirmation_allowed"] is False
    assert out["pair_reports"][1]["dependency_type"] == "UNRESOLVED"
    assert out["typed_dependency_independent_support_allowed"] is False
    assert out["typed_dependency_event_identity_truth"] is False
    assert out["typed_dependency_occurrence_identity_truth"] is False
