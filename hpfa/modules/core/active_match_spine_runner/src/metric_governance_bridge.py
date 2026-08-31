from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.aggregate_definition_alignment_lite.src.aggregate_definition_alignment import build_alignment
from hpfa.modules.core.metric_definition_policy_lite.src.metric_definition_policy import load_policy_pack
from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import load_dictionary_pack

MODULE_ID = "active_match_metric_governance_bridge_v1"
OUTPUT_JSON = "active_match_metric_governance_bridge_v1.json"
OUTPUT_TXT = "active_match_metric_governance_bridge_v1.txt"


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


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

    admitted_alignment_rows = [
        row
        for row in alignment.get("alignment_rows", []) or []
        if isinstance(row, dict) and row.get("alignment_decision") == "DEFINITION_ALIGNMENT_CANDIDATE"
    ]

    payload = {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "SMOKE_PASS"),
        "metric_definition_policy_status": policy_status,
        "provider_metric_dictionary_status": dictionary_status,
        "aggregate_definition_alignment_status": alignment_status,
        "metric_definition_candidate_count": policy.get("metric_definition_candidate_count"),
        "provider_definition_ready_count": dictionary.get("provider_definition_ready_count"),
        "hpfa_domain_contract_ready_count": dictionary.get("hpfa_domain_contract_ready_count"),
        "aggregate_definition_candidate_count": alignment.get("definition_candidate_count"),
        "aggregate_definition_admitted_candidate_count": len(admitted_alignment_rows),
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
        f"metric_definition_policy_status={policy_status}",
        f"provider_metric_dictionary_status={dictionary_status}",
        f"aggregate_definition_alignment_status={alignment_status}",
        f"metric_definition_candidate_count={payload['metric_definition_candidate_count']}",
        f"provider_definition_ready_count={payload['provider_definition_ready_count']}",
        f"hpfa_domain_contract_ready_count={payload['hpfa_domain_contract_ready_count']}",
        f"aggregate_definition_candidate_count={payload['aggregate_definition_candidate_count']}",
        f"aggregate_definition_admitted_candidate_count={payload['aggregate_definition_admitted_candidate_count']}",
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
