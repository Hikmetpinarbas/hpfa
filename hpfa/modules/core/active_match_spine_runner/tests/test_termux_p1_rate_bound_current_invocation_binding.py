from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
HARNESS = ROOT / "tools" / "termux_p1_physical_acceptance_v1.sh"


def test_rate_bound_physical_harness_materializes_current_invocation_surfaces_before_admission() -> None:
    text = HARNESS.read_text(encoding="utf-8")

    context_call = text.index("active_match_exact_head_run_v1.py")
    safe_call = text.index("safe_finding_admission_current_v1.py")
    claim_call = text.index("analyst_output_claim_admission_current_v1.py")

    assert context_call < safe_call < claim_call
    assert "CHECKPOINT=PRE_CURRENT_INVOCATION_CONTEXT_SURFACES" in text
    assert "CURRENT_INVOCATION_CONTEXT_RETURN_CODE=$CONTEXT_RC" in text
    assert '--expected-product-commit "$EXPECTED_SHA"' in text
    assert '--match-dir "$RUNTIME"' in text
    assert '--out-dir "$WORK"' in text


def test_rate_bound_physical_harness_does_not_continue_admission_after_context_failure() -> None:
    text = HARNESS.read_text(encoding="utf-8")

    assert '[ "$SEQUENCE_RC" -eq 0 ] && [ "$CONTEXT_RC" -eq 0 ]' in text
    assert "SAFE_FINDING_SKIPPED=UPSTREAM_SEQUENCE_OR_CONTEXT_NONZERO" in text
    assert "current_invocation_context_return_code=$CONTEXT_RC" in text
