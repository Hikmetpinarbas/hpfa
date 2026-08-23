from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "final_report_assembly_gate_lite_v1"
OUTPUT_JSON = "final_report_assembly_gate_lite_v1.json"
OUTPUT_TXT = "final_report_assembly_gate_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "report_output_contract_candidate_only"
ASSEMBLY_CLAIM_CEILING = "final_report_assembly_candidate_only"
MISSING_CONTRACT_ITEM_ID = "MISSING_CONTRACT_ITEM_ID"

ALLOWED_DECISIONS = {"INCLUDE_BLOCK_CANDIDATE"}
REVIEW_DECISIONS = {"REVIEW_BLOCK"}
REJECT_DECISIONS = {"REJECT_BLOCK"}

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "final_report_text",
    "production_report",
    "production_report_output",
    "report_text",
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "coach_intention_truth",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
    "quality_truth",
    "sequence_truth",
    "organism_truth",
}

FORBIDDEN_TEXT_FRAGMENTS = [
    "domine etti",
    "saha kontrolünü aldı",
    "hoca planladı",
    "bilinçli olarak",
    "taktiksel gerçek",
    "kesin",
    "kanıtlıyor",
    "nedeni budur",
    "off-ball yapı",
    "pitch control",
    "oyun kontrolü",
]

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
    "quality_truth",
    "sequence_truth",
    "organism_truth",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _validate_output_root(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore

    return validate_output_root(out_dir)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _contract_item_id(item: dict[str, Any]) -> str:
    return str(item.get("contract_item_id") or "")


def _collect_forbidden_hits(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_UPSTREAM_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_collect_forbidden_hits(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(_collect_forbidden_hits(child, child_path))
    return hits


def _forbidden_upstream_hits(item: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(item)))


def _upstream_item_failed(item: dict[str, Any]) -> bool:
    if _as_list(item.get("hard_block_hits")):
        return True
    if str(item.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    if str(item.get("inclusion_decision") or "").upper() in REJECT_DECISIONS:
        return True
    return False


def _forbidden_text_hits(text: str) -> list[str]:
    lower = text.lower()
    return [fragment for fragment in FORBIDDEN_TEXT_FRAGMENTS if fragment in lower]


def evaluate_assembly_item(item: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(item)
    contract_item_id = _contract_item_id(normalized)
    missing_fields: list[str] = []
    if not contract_item_id:
        missing_fields.append("contract_item_id")
        contract_item_id = MISSING_CONTRACT_ITEM_ID
    if "report_block_id" not in normalized or normalized.get("report_block_id") in [None, ""]:
        missing_fields.append("report_block_id")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")
    if "inclusion_decision" not in normalized:
        missing_fields.append("inclusion_decision")

    inclusion_decision = str(normalized.get("inclusion_decision") or "")
    output_candidate = str(normalized.get("output_text_candidate_tr") or "")
    forbidden_upstream_hits = _forbidden_upstream_hits(normalized)
    forbidden_text_hits = _forbidden_text_hits(output_candidate)
    hard_block_hits: list[str] = []
    review_hits: list[str] = []

    if missing_fields:
        hard_block_hits.append("assembly_required_fields_missing")
    if _upstream_item_failed(normalized):
        hard_block_hits.append("upstream_contract_item_failed_closed")
    if inclusion_decision in REVIEW_DECISIONS:
        review_hits.append("upstream_contract_item_requires_review")
    if inclusion_decision not in ALLOWED_DECISIONS | REVIEW_DECISIONS | REJECT_DECISIONS:
        hard_block_hits.append("unknown_inclusion_decision_rejected")
    if inclusion_decision in ALLOWED_DECISIONS and not output_candidate:
        hard_block_hits.append("included_block_missing_output_candidate")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_contract_forbidden_output_attempted")
    if forbidden_text_hits:
        hard_block_hits.append("assembly_candidate_forbidden_language_detected")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_contract_claim_output_allowed")
    if normalized.get("final_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_contract_final_report_allowed")
    if normalized.get("production_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_contract_production_output_allowed")
    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")

    if hard_block_hits:
        assembly_decision = "BLOCK_ASSEMBLY_ITEM"
        status = "FAIL_CLOSED"
        assembly_item_candidate_tr = ""
    elif review_hits:
        assembly_decision = "ROUTE_ASSEMBLY_ITEM_TO_REVIEW"
        status = "REVIEW_REQUIRED"
        assembly_item_candidate_tr = ""
    else:
        assembly_decision = "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
        status = "SMOKE_PASS"
        assembly_item_candidate_tr = output_candidate

    return {
        "module_id": MODULE_ID,
        "assembly_item_id": f"assembly_item_{contract_item_id}",
        "contract_item_id": contract_item_id,
        "report_block_id": str(normalized.get("report_block_id") or ""),
        "source_inclusion_decision": inclusion_decision,
        "assembly_order": idx + 1,
        "assembly_decision": assembly_decision,
        "assembly_item_candidate_tr": assembly_item_candidate_tr,
        "claim_ceiling": ASSEMBLY_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "status": status,
        "hard_block_hits": hard_block_hits,
        "review_hits": review_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "forbidden_text_hits": forbidden_text_hits,
        "claim_output_allowed": False,
        "draft_report_candidate_allowed": True if status == "SMOKE_PASS" else False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "control_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "pitch_control_truth": False,
        "causal_truth": False,
        "quality_truth": False,
        "sequence_truth": False,
        "organism_truth": False,
        "blocked_language_families": list(BLOCKED_LANGUAGE_FAMILIES),
        "canonical_event_count": "UNKNOWN",
    }


def build_assembly_gate(contract_items: list[dict[str, Any]]) -> dict[str, Any]:
    assembly_items = [evaluate_assembly_item(item, idx) for idx, item in enumerate(contract_items)]
    blocked_count = sum(1 for item in assembly_items if item["assembly_decision"] == "BLOCK_ASSEMBLY_ITEM")
    review_count = sum(1 for item in assembly_items if item["assembly_decision"] == "ROUTE_ASSEMBLY_ITEM_TO_REVIEW")
    ready_count = sum(
        1 for item in assembly_items if item["assembly_decision"] == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
    )
    status = "FAIL_CLOSED" if blocked_count else "REVIEW_REQUIRED" if review_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "assembly_item_count": len(assembly_items),
        "ready_count": ready_count,
        "review_count": review_count,
        "blocked_count": blocked_count,
        "assembly_items": assembly_items,
        "claim_output_allowed": False,
        "draft_report_candidate_allowed": True if ready_count and not blocked_count and not review_count else False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "claim_ceiling": ASSEMBLY_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "final_report_assembly_candidate_only_not_final_report_not_production",
    }


def write_outputs(contract_items: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_assembly_gate(contract_items)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA FINAL REPORT ASSEMBLY GATE LITE V1",
        "========================================",
        f"status={report['status']}",
        f"assembly_item_count={report['assembly_item_count']}",
        f"ready_count={report['ready_count']}",
        f"review_count={report['review_count']}",
        f"blocked_count={report['blocked_count']}",
        f"draft_report_candidate_allowed={report['draft_report_candidate_allowed']}",
        f"final_report_allowed={report['final_report_allowed']}",
        f"production_report_allowed={report['production_report_allowed']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[assembly_items]",
    ]
    for item in report["assembly_items"][:50]:
        lines.append(
            f"- {item['assembly_item_id']} order={item['assembly_order']} "
            f"decision={item['assembly_decision']} status={item['status']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
