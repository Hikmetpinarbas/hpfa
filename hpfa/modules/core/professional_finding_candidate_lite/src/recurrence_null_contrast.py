from __future__ import annotations

from statistics import mean
from typing import Any

MODULE_ID = "sequence_pattern_admission_lite_v1"
CONTRAST_ID = "recurrence_null_contrast_v1"
CLAIM_CEILING = "UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _fail(*hits: str) -> dict[str, Any]:
    return {
        "contrast_id": CONTRAST_ID,
        "status": "FAIL_CLOSED",
        "decision": "RECURRENCE_NULL_CONTRAST_REJECTED",
        "rows": [],
        "row_count": 0,
        "hard_block_hits": sorted(set(hits)),
        "claim_ceiling": CLAIM_CEILING,
        "multiple_testing_corrected": False,
        "significance_claim_allowed": False,
        "tactical_pattern_truth_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _quantile(values: list[int], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty values")
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def evaluate_recurrence_null_contrast(
    admission_payload: dict[str, Any],
    null_payload: dict[str, Any],
) -> dict[str, Any]:
    """Compare admitted independent recurrence with an explicit caller-supplied null distribution.

    This evaluator does not generate a null model. It audits a supplied match-local null
    distribution, binds it to the exact admitted trace cohort, and exposes descriptive
    empirical-tail evidence only. It never emits significance, tactical or causal truth.
    """
    hard: list[str] = []
    reviews: list[str] = []

    if admission_payload.get("module_id") != MODULE_ID:
        hard.append("admission_module_id_mismatch")
    if admission_payload.get("canonical_event_count") != "UNKNOWN":
        hard.append("canonical_event_count_claimed")
    if admission_payload.get("true_action_count") != "UNKNOWN":
        hard.append("true_action_count_claimed")
    if admission_payload.get("production_release") is True:
        hard.append("production_release_claimed")
    if admission_payload.get("hard_block_hits"):
        hard.append("admission_hard_blocks_present")
    if _clean(admission_payload.get("status")).upper() == "FAIL_CLOSED":
        hard.append("admission_fail_closed")

    if null_payload.get("module_id") != CONTRAST_ID:
        hard.append("null_payload_module_id_mismatch")
    if null_payload.get("canonical_event_count") != "UNKNOWN":
        hard.append("null_canonical_event_count_claimed")
    if null_payload.get("true_action_count") != "UNKNOWN":
        hard.append("null_true_action_count_claimed")
    if null_payload.get("production_release") is True:
        hard.append("null_production_release_claimed")
    if null_payload.get("hard_block_hits"):
        hard.append("null_hard_blocks_present")

    method = null_payload.get("method") if isinstance(null_payload.get("method"), dict) else {}
    for field in ("null_model_id", "null_model_version", "null_mechanism", "exchangeability_assumption"):
        if not _clean(method.get(field)):
            hard.append(f"null_method_missing:{field}")
    preserved = sorted({_clean(x) for x in (method.get("preserved_constraints") or []) if _clean(x)})
    if not preserved:
        hard.append("null_method_preserved_constraints_missing")
    if method.get("observed_labels_reused_as_null_truth") is not False:
        hard.append("null_observed_labels_reuse_lock_missing")

    null_rows = [row for row in (null_payload.get("null_rows") or []) if isinstance(row, dict)]
    if not null_rows:
        hard.append("null_rows_empty")
    if hard:
        return _fail(*hard)

    admissions = {
        _clean(row.get("trace_family_ref")): row
        for row in (admission_payload.get("sequence_pattern_admissions") or [])
        if isinstance(row, dict) and _clean(row.get("trace_family_ref"))
    }

    out: list[dict[str, Any]] = []
    for row in null_rows:
        family_ref = _clean(row.get("trace_family_ref"))
        if not family_ref or family_ref not in admissions:
            return _fail(f"null_family_not_in_admission:{family_ref or 'UNKNOWN'}")
        admitted = admissions[family_ref]
        admitted_refs = sorted({_clean(x) for x in (admitted.get("eligible_trace_refs") or []) if _clean(x)})
        null_refs = sorted({_clean(x) for x in (row.get("eligible_trace_refs") or []) if _clean(x)})
        if not admitted_refs or null_refs != admitted_refs:
            return _fail(f"null_trace_cohort_mismatch:{family_ref}")

        observed = admitted.get("independent_support_count")
        if not isinstance(observed, int) or observed < 1:
            reviews.append(f"independent_support_not_admitted:{family_ref}")
            out.append({
                "trace_family_ref": family_ref,
                "eligible_trace_refs": admitted_refs,
                "state": "NOT_EVALUATED_INDEPENDENT_SUPPORT_UNKNOWN",
                "observed_independent_recurrence": "UNKNOWN",
                "claim_ceiling": CLAIM_CEILING,
            })
            continue

        draws = row.get("null_independent_recurrence_counts")
        if not isinstance(draws, list) or not draws:
            return _fail(f"null_draws_missing:{family_ref}")
        if any(not isinstance(x, int) or x < 0 for x in draws):
            return _fail(f"null_draw_invalid:{family_ref}")
        declared_n = row.get("simulation_count")
        if not isinstance(declared_n, int) or declared_n != len(draws):
            return _fail(f"null_simulation_count_mismatch:{family_ref}")
        if any(x > len(admitted_refs) for x in draws):
            return _fail(f"null_draw_exceeds_eligible_cohort:{family_ref}")

        exceed_or_equal = sum(1 for x in draws if x >= observed)
        tail = (exceed_or_equal + 1) / (len(draws) + 1)
        below = sum(1 for x in draws if x < observed)
        percentile = below / len(draws)
        state = "OBSERVED_ABOVE_NULL_MEDIAN" if observed > _quantile(draws, 0.5) else "OBSERVED_NOT_ABOVE_NULL_MEDIAN"

        out.append({
            "trace_family_ref": family_ref,
            "eligible_trace_refs": admitted_refs,
            "state": state,
            "observed_independent_recurrence": observed,
            "simulation_count": len(draws),
            "null_mean": mean(draws),
            "null_median": _quantile(draws, 0.5),
            "null_q95": _quantile(draws, 0.95),
            "empirical_upper_tail_probability_uncorrected": tail,
            "observed_percentile_in_null_draws": percentile,
            "null_model_id": _clean(method.get("null_model_id")),
            "null_model_version": _clean(method.get("null_model_version")),
            "null_mechanism": _clean(method.get("null_mechanism")),
            "preserved_constraints": preserved,
            "exchangeability_assumption": _clean(method.get("exchangeability_assumption")),
            "multiple_testing_corrected": False,
            "significance_claim_allowed": False,
            "tactical_pattern_truth_allowed": False,
            "causality_allowed": False,
            "safe_meaning": "Observed independent recurrence is described relative to the supplied audited null distribution only; this is not a tactical-pattern, intention, causal or significance claim.",
            "withdrawal_condition": "Withdraw or recompute if the admitted trace cohort, independence mapping, null mechanism, preserved constraints, exchangeability assumption or null draws change.",
            "claim_ceiling": CLAIM_CEILING,
        })

    return {
        "contrast_id": CONTRAST_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "RECURRENCE_NULL_CONTRAST_EVALUATED",
        "rows": out,
        "row_count": len(out),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "method": {
            "null_model_id": _clean(method.get("null_model_id")),
            "null_model_version": _clean(method.get("null_model_version")),
            "null_mechanism": _clean(method.get("null_mechanism")),
            "preserved_constraints": preserved,
            "exchangeability_assumption": _clean(method.get("exchangeability_assumption")),
        },
        "multiple_testing_corrected": False,
        "significance_claim_allowed": False,
        "tactical_pattern_truth_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
