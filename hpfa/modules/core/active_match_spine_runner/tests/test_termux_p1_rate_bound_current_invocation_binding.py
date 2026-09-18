from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
HARNESS = ROOT / "tools" / "termux_p1_physical_acceptance_v1.sh"


def test_rate_bound_physical_harness_uses_single_authoritative_admission_pass() -> None:
    text = HARNESS.read_text(encoding="utf-8")

    context_call = text.index("active_match_exact_head_run_v1.py")

    assert "CHECKPOINT=PRE_CURRENT_INVOCATION_CONTEXT_SURFACES" in text
    assert "CURRENT_INVOCATION_CONTEXT_RETURN_CODE=$CONTEXT_RC" in text
    assert '--expected-product-commit "$EXPECTED_SHA"' in text
    assert '--match-dir "$RUNTIME"' in text
    assert '--out-dir "$WORK"' in text
    assert 'python -u "$SRC/safe_finding_admission_current_v1.py"' not in text
    assert 'python -u "$SRC/analyst_output_claim_admission_current_v1.py"' not in text
    assert text.index("CHECKPOINT=VERIFY_SAFE_FINDING_CURRENT_INVOCATION_ARTIFACT") > context_call
    assert text.index("CHECKPOINT=VERIFY_CLAIM_SATISFIABILITY_CURRENT_INVOCATION_ARTIFACT") > context_call


def test_rate_bound_physical_harness_fails_closed_on_stale_process_variant_reuse() -> None:
    text = HARNESS.read_text(encoding="utf-8")

    assert 'payload.get("process_context_stale_process_variant_surface_reused") is True' in text
    assert "SAFE_FINDING_RETURN_CODE=$SAFE_RC" in text
    assert "CLAIM_SATISFIABILITY_RETURN_CODE=$CLAIM_RC" in text


def test_rate_bound_physical_harness_does_not_validate_admission_after_context_failure() -> None:
    text = HARNESS.read_text(encoding="utf-8")

    assert '[ "$SEQUENCE_RC" -eq 0 ] && [ "$CONTEXT_RC" -eq 0 ]' in text
    assert "SAFE_FINDING_SKIPPED=UPSTREAM_SEQUENCE_OR_CONTEXT_NONZERO" in text
    assert "current_invocation_context_return_code=$CONTEXT_RC" in text


def test_physical_harness_archives_analyst_report_for_aday029_runtime_review() -> None:
    text = HARNESS.read_text(encoding="utf-8")
    assert '"HPFA_ANALYST_REPORT.txt"' in text
    assert '"analyst_output_claim_contract_projection_v1.json"' in text


def test_physical_harness_archives_multisurface_argument_artifacts() -> None:
    text = HARNESS.read_text(encoding="utf-8")
    assert '"rich_multiformat_analysis_lattice_v1.json"' in text
    assert '"active_match_full_spine_v1.json"' in text
    assert '"HPFA_ANALYST_REPORT.txt"' in text
