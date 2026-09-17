from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    build_analyst_output_claim_contract,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.claim_satisfiability_runtime_binding import (
    bind_claim_satisfiability,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_sentence_render_completeness import (
    build_source_bound_render_contract,
    validate_safe_sentence_render,
)

OUTPUT_NAME = "analyst_output_claim_contract_projection_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _counter_scenario_details(handoff: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in handoff.get("alternative_explanations") or []:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        meaning = str(row.get("meaning") or "").strip()
        if code or meaning:
            result.append({"code": code, "meaning": meaning})
    return result


def _visible_fact_text(handoff: dict[str, Any]) -> str | None:
    visible = handoff.get("what_visible")
    if not isinstance(visible, dict):
        return None
    success = visible.get("success_branch_count")
    failure = visible.get("failure_branch_count")
    denominator = visible.get("eligible_outcome_branch_count")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (success, failure, denominator)):
        return None
    return (
        "Bu maçta aynı görünür başlangıçtan çıkan "
        f"{denominator} uygun vakanın {success} tanesinde SUCCESS, "
        f"{failure} tanesinde FAILURE sonucu görünür olarak etiketlendi."
    )


def _propagate_render_source_terms(
    sequence_payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Carry existing Safe Finding terms into Analyst Output contracts for rendering.

    This is provenance propagation only. It creates no evidence, counterevidence,
    counter-scenario, withdrawal condition, interpretation, or EMIT permission.
    """
    handoff_by_ref = {
        str(row.get("safe_finding_handoff_candidate_id") or "").strip(): row
        for row in (sequence_payload.get("safe_finding_handoff_candidates") or [])
        if isinstance(row, dict) and str(row.get("safe_finding_handoff_candidate_id") or "").strip()
    }
    propagated = 0
    unresolved = 0
    for contract in result.get("analyst_output_contracts") or []:
        if not isinstance(contract, dict):
            continue
        source_ref = str(contract.get("source_safe_finding_handoff_ref") or "").strip()
        handoff = handoff_by_ref.get(source_ref)
        if not isinstance(handoff, dict):
            contract["render_source_terms_state"] = "SOURCE_SAFE_FINDING_HANDOFF_UNRESOLVED"
            unresolved += 1
            continue

        details = _counter_scenario_details(handoff)
        core_counter_scenarios = _strings([row.get("code") for row in details])
        core_withdrawal = _strings(handoff.get("withdrawal_conditions"))
        support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
        counterevidence = (
            handoff.get("counterevidence")
            if isinstance(handoff.get("counterevidence"), dict)
            else {}
        )
        evidence_refs = _strings(support.get("visible_success_sequence_refs"))
        counterevidence_refs = _strings(
            [
                *(counterevidence.get("visible_failure_sequence_refs") or []),
                *(counterevidence.get("comparable_counterexample_refs") or []),
            ]
        )

        contract["render_source_terms_state"] = "SOURCE_SAFE_FINDING_TERMS_PROPAGATED"
        contract["render_what_visible"] = handoff.get("what_visible")
        contract["render_what_visible_text_tr"] = _visible_fact_text(handoff)
        contract["render_safe_meaning"] = handoff.get("safe_meaning")
        contract["render_source_analyst_summary_tr"] = handoff.get("analyst_summary_tr")
        contract["render_analyst_action"] = handoff.get("analyst_action")
        contract["counter_scenario_candidates"] = core_counter_scenarios
        contract["counter_scenario_details"] = details
        contract["withdrawal_condition_candidates"] = core_withdrawal
        contract["render_evidence_refs"] = evidence_refs
        contract["render_counterevidence_refs"] = counterevidence_refs
        contract["render_source_terms_create_new_evidence"] = False
        contract["render_source_terms_create_new_counterevidence"] = False
        contract["render_source_terms_create_new_counter_scenario"] = False
        contract["render_source_terms_create_new_withdrawal_condition"] = False
        contract["render_source_terms_can_authorize_emit"] = False
        contract["render_source_terms_can_strengthen_claim_ceiling"] = False
        propagated += 1

    result["render_source_terms_propagated_count"] = propagated
    result["render_source_terms_unresolved_count"] = unresolved
    result["render_source_terms_create_new_evidence"] = False
    result["render_source_terms_can_authorize_emit"] = False
    result["render_source_terms_can_strengthen_claim_ceiling"] = False
    return result


def _materialize_source_bound_render_contracts(result: dict[str, Any]) -> dict[str, Any]:
    render_rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    rendered_allowed_count = 0
    fact_only_count = 0

    for source_contract in result.get("analyst_output_contracts") or []:
        if not isinstance(source_contract, dict):
            continue
        rendered = build_source_bound_render_contract(source_contract)
        validation = validate_safe_sentence_render(source_contract, rendered)
        state = str(validation.get("render_completeness_state") or "UNKNOWN")
        state_counts[state] += 1
        render_allowed = validation.get("render_allowed") is True
        fallback_allowed = validation.get("fallback_allowed") is True
        if render_allowed:
            rendered_allowed_count += 1
            final_sentence = str(rendered.get("rendered_sentence_tr") or "").strip() or None
        elif fallback_allowed:
            fact_only_count += 1
            final_sentence = str(validation.get("what_visible") or "").strip() or None
        else:
            final_sentence = None
        render_rows.append({
            "source_analyst_output_contract_ref": source_contract.get("analyst_output_contract_id"),
            "source_safe_finding_handoff_ref": source_contract.get("source_safe_finding_handoff_ref"),
            "source_safe_finding_admission_decision": source_contract.get("safe_finding_admission_decision"),
            "rendered_sentence_contract": rendered,
            "render_validation": validation,
            "final_human_sentence_tr": final_sentence,
            "render_creates_new_evidence": False,
            "render_can_authorize_emit": False,
            "render_can_strengthen_claim_ceiling": False,
            "analyst_or_llm_text_is_evidence": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        })

    result["source_bound_render_contracts"] = render_rows
    result["source_bound_render_contract_count"] = len(render_rows)
    result["source_bound_render_state_counts"] = dict(sorted(state_counts.items()))
    result["source_bound_render_allowed_count"] = rendered_allowed_count
    result["source_bound_fact_only_fallback_count"] = fact_only_count
    result["source_bound_render_creates_new_evidence"] = False
    result["source_bound_render_can_authorize_emit"] = False
    result["source_bound_render_can_strengthen_claim_ceiling"] = False
    result["analyst_or_llm_text_is_evidence"] = False
    return result


def runtime_write_outputs(
    sequence_json: str | Path,
    admission_json: str | Path,
    out_dir: str | Path,
) -> dict:
    sequence_path = Path(sequence_json).expanduser().resolve()
    admission_path = Path(admission_json).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    sequence_payload = _load(sequence_path)
    admission_payload = _load(admission_path)
    if not sequence_payload or not admission_payload:
        result = {
            "status": "FAIL_CLOSED",
            "analyst_output_contracts": [],
            "analyst_output_contract_count": 0,
            "professional_emit_allowed": False,
            "professional_emit_allowed_count": 0,
            "claim_satisfiability_gate_consumed": False,
            "render_source_terms_propagated_count": 0,
            "render_source_terms_unresolved_count": 0,
            "source_bound_render_contracts": [],
            "source_bound_render_contract_count": 0,
            "source_bound_render_state_counts": {},
            "source_bound_render_allowed_count": 0,
            "source_bound_fact_only_fallback_count": 0,
            "render_source_terms_create_new_evidence": False,
            "render_source_terms_can_authorize_emit": False,
            "render_source_terms_can_strengthen_claim_ceiling": False,
            "source_bound_render_creates_new_evidence": False,
            "source_bound_render_can_authorize_emit": False,
            "source_bound_render_can_strengthen_claim_ceiling": False,
            "hard_block_hits": ["required_sequence_or_admission_payload_missing_or_invalid"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        result = build_analyst_output_claim_contract(sequence_payload, admission_payload)
        if result.get("status") != "FAIL_CLOSED":
            result = bind_claim_satisfiability(
                sequence_payload,
                admission_payload,
                result,
            )
        if result.get("status") != "FAIL_CLOSED":
            result = _propagate_render_source_terms(sequence_payload, result)
            result = _materialize_source_bound_render_contracts(result)

    target = output / OUTPUT_NAME
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    result["output"] = str(target)
    result["source_sequence_json"] = str(sequence_path)
    result["source_admission_json"] = str(admission_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA compact Safe Finding admission to analyst-claim micro-gear")
    parser.add_argument("--sequence-json", required=True)
    parser.add_argument("--admission-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = runtime_write_outputs(args.sequence_json, args.admission_json, args.out_dir)
    print(json.dumps({
        "status": result.get("status"),
        "analyst_output_contract_count": result.get("analyst_output_contract_count"),
        "safe_finding_admission_decision_counts": result.get("safe_finding_admission_decision_counts") or {},
        "professional_emit_allowed": result.get("professional_emit_allowed"),
        "professional_emit_allowed_count": result.get("professional_emit_allowed_count"),
        "claim_satisfiability_gate_consumed": result.get("claim_satisfiability_gate_consumed") is True,
        "claim_satisfiability_gate_state_counts": result.get("claim_satisfiability_gate_state_counts") or {},
        "render_source_terms_propagated_count": result.get("render_source_terms_propagated_count"),
        "render_source_terms_unresolved_count": result.get("render_source_terms_unresolved_count"),
        "source_bound_render_contract_count": result.get("source_bound_render_contract_count"),
        "source_bound_render_state_counts": result.get("source_bound_render_state_counts") or {},
        "source_bound_render_allowed_count": result.get("source_bound_render_allowed_count"),
        "source_bound_fact_only_fallback_count": result.get("source_bound_fact_only_fallback_count"),
        "hard_block_hits": result.get("hard_block_hits") or [],
        "review_hits": result.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "output": result.get("output"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
