from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.aggregate_definition_alignment_lite.src.aggregate_definition_alignment import build_alignment
from hpfa.modules.core.metric_definition_policy_lite.src.metric_definition_policy import load_policy_pack
from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import load_dictionary_pack
from hpfa.modules.core.active_match_spine_runner.src.zfgv_runtime_capability_admission import (
    build_runtime_capability_admission,
)

MODULE_ID = "active_match_metric_governance_bridge_v1"
OUTPUT_JSON = "active_match_metric_governance_bridge_v1.json"
OUTPUT_TXT = "active_match_metric_governance_bridge_v1.txt"
ZFGV_OBSERVATION_MODEL = "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
ALIGNMENT_CANDIDATE_DECISION = "DEFINITION_ALIGNMENT_CANDIDATE"


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _metric_capability_admission_rows(
    capability_requirements: list[dict[str, Any]],
    runtime_admission: dict[str, Any],
) -> list[dict[str, Any]]:
    evaluated = runtime_admission.get("runtime_capability_admission_evaluated") is True
    admitted = {
        str(value).strip().upper()
        for value in runtime_admission.get("admitted_observation_capabilities") or []
        if str(value).strip()
    }
    rows: list[dict[str, Any]] = []
    for requirement in capability_requirements:
        required = {
            str(value).strip().upper()
            for value in requirement.get("required_observation_capabilities") or []
            if str(value).strip()
        }
        requirement_declared = bool(required)
        missing = sorted(required - admitted) if evaluated else sorted(required)
        if not requirement_declared:
            state = "NOT_ELIGIBLE_REQUIRED_CAPABILITIES_UNDECLARED"
        elif not evaluated:
            state = "NOT_EVALUATED_RUNTIME_CAPABILITY_EVIDENCE_MISSING"
        elif missing:
            state = "NOT_ELIGIBLE_MISSING_REQUIRED_CAPABILITIES"
        else:
            state = "ELIGIBLE_REQUIRED_CAPABILITIES_PRESENT"
        rows.append({
            "metric_id": requirement.get("metric_id"),
            "required_observation_capabilities": sorted(required),
            "required_observation_capabilities_declared": requirement_declared,
            "admitted_observation_capabilities": sorted(admitted),
            "missing_required_observation_capabilities": missing,
            "runtime_capability_admission_evaluated": evaluated,
            "capability_eligibility_state": state,
            "metric_value_output_allowed_by_capability_match": False,
            "construct_truth_granted_by_capability_match": False,
        })
    return rows


def _alignment_candidate_rows(alignment: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    violations: list[str] = []
    for index, row in enumerate(alignment.get("alignment_rows", []) or []):
        if not isinstance(row, dict) or row.get("alignment_decision") != ALIGNMENT_CANDIDATE_DECISION:
            continue
        candidates.append(row)
        for field in (
            "metric_value_output_allowed",
            "claim_allowed",
            "aggregate_equivalence_truth",
            "independent_confirmation_allowed",
            "measurement_invariance_truth",
        ):
            if row.get(field) is not False:
                violations.append(f"alignment_candidate_claim_lock_invalid:{index}:{field}")
    return candidates, violations


def run_metric_governance_bridge(out_dir: str | Path, product_root: str | Path) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    root = Path(product_root).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)

    policy = load_policy_pack(root / "configs" / "metrics")
    dictionary = load_dictionary_pack(root)
    xlsx = _load(output / "xlsx_surface_audit_lite_v1.json")
    label_semantics = _load(output / "provider_label_value_semantics_lite_v1.json")
    reconciliation = _load(output / "cross_format_reconciliation_lite_v1.json")
    registry = _load(
        root
        / "hpfa"
        / "modules"
        / "core"
        / "aggregate_definition_alignment_lite"
        / "registry"
        / "sportsbase_aggregate_definition_candidates_v1.json"
    )

    runtime_admission = build_runtime_capability_admission(output)

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    prerequisites = {
        "xlsx_surface_audit": bool(xlsx),
        "provider_label_semantics": bool(label_semantics),
        "cross_format_reconciliation": bool(reconciliation),
        "aggregate_definition_registry": bool(registry),
    }
    for name, present in prerequisites.items():
        if not present:
            review_hits.append(f"metric_governance_prerequisite_missing:{name}")

    capability_requirements = [
        row
        for row in (dictionary.get("zfgv_metric_capability_requirements") or [])
        if isinstance(row, dict)
    ]
    zfgv_capability_contract_present = (
        dictionary.get("zfgv_observation_model") == ZFGV_OBSERVATION_MODEL
        and dictionary.get("event_only_compatibility_is_global_admission_gate") is False
        and dictionary.get("metric_admission_policy")
        == "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES"
        and bool(capability_requirements)
    )
    if not zfgv_capability_contract_present:
        hard_blocks.append("zfgv_metric_capability_contract_missing_or_invalid")

    invalid_capability_rows = [
        str(row.get("metric_id") or "UNKNOWN")
        for row in capability_requirements
        if not isinstance(row.get("required_observation_capabilities"), list)
        or row.get("metric_value_output_allowed_by_this_projection") is not False
        or row.get("construct_truth_granted_by_this_projection") is not False
    ]
    if invalid_capability_rows:
        hard_blocks.append(
            "zfgv_metric_capability_projection_invalid:"
            + ",".join(sorted(set(invalid_capability_rows)))
        )

    runtime_capability_admission_evaluated = (
        runtime_admission.get("runtime_capability_admission_evaluated") is True
    )
    if not runtime_capability_admission_evaluated:
        review_hits.append("zfgv_runtime_capability_admission_not_evaluated")

    metric_capability_admission = _metric_capability_admission_rows(
        capability_requirements, runtime_admission
    )
    undeclared_requirement_metric_ids = sorted({
        str(row.get("metric_id") or "UNKNOWN")
        for row in metric_capability_admission
        if row.get("required_observation_capabilities_declared") is not True
    })
    if undeclared_requirement_metric_ids:
        review_hits.append(
            "zfgv_metric_required_capabilities_undeclared:"
            + ",".join(undeclared_requirement_metric_ids)
        )

    alignment: dict[str, Any] = {
        "status": "NOT_EVALUATED_PREREQUISITE_MISSING",
        "alignment_rows": [],
        "definition_candidate_count": 0,
    }
    if all(prerequisites.values()):
        try:
            alignment = build_alignment(xlsx, label_semantics, reconciliation, policy, registry)
        except Exception as exc:
            hard_blocks.append(f"aggregate_definition_alignment_exception:{type(exc).__name__}")
            alignment = {
                "status": "FAIL_CLOSED",
                "hard_block_hits": [hard_blocks[-1]],
                "alignment_rows": [],
                "definition_candidate_count": 0,
            }

    policy_status = _status(policy.get("status"))
    dictionary_status = _status(dictionary.get("status"))
    alignment_status = _status(alignment.get("status"))

    if policy_status == "FAIL_CLOSED":
        hard_blocks.append("metric_definition_policy_fail_closed")
    elif policy_status == "REVIEW_REQUIRED":
        review_hits.append("metric_definition_policy_review_required")

    if dictionary_status == "FAIL_CLOSED":
        hard_blocks.append("provider_metric_dictionary_fail_closed")
    elif dictionary_status in {"REVIEW_REQUIRED", "SPEC_ONLY"}:
        review_hits.append(f"provider_metric_dictionary_{dictionary_status.casefold()}")

    if alignment_status == "FAIL_CLOSED":
        hard_blocks.append("aggregate_definition_alignment_fail_closed")
    elif alignment_status in {"REVIEW_REQUIRED", "NOT_EVALUATED_PREREQUISITE_MISSING"}:
        review_hits.append(f"aggregate_definition_alignment_{alignment_status.casefold()}")

    alignment_candidate_rows, alignment_candidate_claim_lock_violations = _alignment_candidate_rows(alignment)
    hard_blocks.extend(alignment_candidate_claim_lock_violations)

    payload = {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "SMOKE_PASS"),
        "observation_model": ZFGV_OBSERVATION_MODEL,
        "global_event_only_gate": False,
        "metric_admission_rule": "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES",
        "zfgv_capability_contract_present": zfgv_capability_contract_present,
        "runtime_capability_admission_evaluated": runtime_capability_admission_evaluated,
        "runtime_capability_admission": runtime_admission,
        "admitted_observation_capabilities": runtime_admission.get("admitted_observation_capabilities") or [],
        "zfgv_metric_capability_requirements": capability_requirements,
        "metric_capability_admission": metric_capability_admission,
        "undeclared_required_capability_metric_ids": undeclared_requirement_metric_ids,
        "metric_definition_policy_status": policy_status,
        "provider_metric_dictionary_status": dictionary_status,
        "aggregate_definition_alignment_status": alignment_status,
        "metric_definition_candidate_count": policy.get("metric_definition_candidate_count"),
        "provider_definition_ready_count": dictionary.get("provider_definition_ready_count"),
        "hpfa_domain_contract_ready_count": dictionary.get("hpfa_domain_contract_ready_count"),
        "aggregate_definition_candidate_count": alignment.get("definition_candidate_count"),
        "aggregate_definition_alignment_candidate_count": len(alignment_candidate_rows),
        "aggregate_definition_admitted_candidate_count": 0,
        "aggregate_definition_alignment_candidates_are_admitted": False,
        "aggregate_definition_alignment_candidates_allow_metric_value_output": False,
        "aggregate_definition_alignment_candidates_allow_claim_output": False,
        "aggregate_definition_alignment_candidate_claim_lock_violation_count": len(alignment_candidate_claim_lock_violations),
        "aggregate_alignment_decision_counts": alignment.get("alignment_decision_counts") or {},
        "prerequisites": prerequisites,
        "metric_policy": policy,
        "provider_metric_dictionary": dictionary,
        "aggregate_definition_alignment": alignment,
        "hard_block_hits": list(dict.fromkeys(hard_blocks)),
        "review_hits": list(dict.fromkeys(review_hits)),
        "metric_value_output_allowed": False,
        "construct_truth": False,
        "aggregate_equivalence_truth": False,
        "same_provider_multiformat_is_independent_support": False,
        "capability_eligibility_is_metric_truth": False,
        "capability_eligibility_is_construct_truth": False,
        "empty_required_capabilities_are_eligible": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA ACTIVE_MATCH METRIC GOVERNANCE BRIDGE V1",
        "==============================================",
        f"status={payload['status']}",
        f"observation_model={ZFGV_OBSERVATION_MODEL}",
        "global_event_only_gate=false",
        f"zfgv_capability_contract_present={str(zfgv_capability_contract_present).lower()}",
        f"runtime_capability_admission_evaluated={str(runtime_capability_admission_evaluated).lower()}",
        f"admitted_observation_capabilities={payload['admitted_observation_capabilities']}",
        f"metric_definition_policy_status={policy_status}",
        f"provider_metric_dictionary_status={dictionary_status}",
        f"aggregate_definition_alignment_status={alignment_status}",
        f"metric_definition_candidate_count={payload['metric_definition_candidate_count']}",
        f"provider_definition_ready_count={payload['provider_definition_ready_count']}",
        f"hpfa_domain_contract_ready_count={payload['hpfa_domain_contract_ready_count']}",
        f"aggregate_definition_candidate_count={payload['aggregate_definition_candidate_count']}",
        f"aggregate_definition_alignment_candidate_count={payload['aggregate_definition_alignment_candidate_count']}",
        "aggregate_definition_admitted_candidate_count=0",
        "aggregate_definition_alignment_candidates_are_admitted=false",
        f"undeclared_required_capability_metric_ids={payload['undeclared_required_capability_metric_ids']}",
        "empty_required_capabilities_are_eligible=false",
        f"aggregate_definition_alignment_candidate_claim_lock_violation_count={payload['aggregate_definition_alignment_candidate_claim_lock_violation_count']}",
        f"hard_block_hits={payload['hard_block_hits']}",
        f"review_hits={payload['review_hits']}",
        "metric_value_output_allowed=false",
        "construct_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    payload["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return payload
