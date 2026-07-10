from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "report_output_contract_lite_v1"
OUTPUT_JSON = "report_output_contract_lite_v1.json"
OUTPUT_TXT = "report_output_contract_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "analyst_report_block_candidate_only"
OUTPUT_CONTRACT_CLAIM_CEILING = "report_output_contract_candidate_only"
MISSING_REPORT_BLOCK_ID = "MISSING_REPORT_BLOCK_ID"

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "report_text",
    "final_report_text",
    "production_report",
    "production_report_output",
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

FORBIDDEN_BLOCK_FRAGMENTS = [
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

ALLOWED_BLOCK_FAMILIES = {
    "analyst_reading_candidate",
    "technical_limit_candidate",
    "evidence_note_candidate",
    "review_required_candidate",
}


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


def _report_block_id(block: dict[str, Any]) -> str:
    return str(block.get("report_block_id") or "")


def _forbidden_upstream_hits(block: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for field in FORBIDDEN_UPSTREAM_FIELDS:
        if field in block and _is_forbidden_value(block.get(field)):
            hits.append(field)
    return sorted(hits)


def _upstream_block_failed(block: dict[str, Any]) -> bool:
    if _as_list(block.get("hard_block_hits")):
        return True
    if str(block.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(block.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _forbidden_text_hits(text: str) -> list[str]:
    lower = text.lower()
    return [fragment for fragment in FORBIDDEN_BLOCK_FRAGMENTS if fragment in lower]


def evaluate_report_block(block: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(block)
    block_id = _report_block_id(normalized)
    missing_fields: list[str] = []
    if not block_id:
        missing_fields.append("report_block_id")
        block_id = MISSING_REPORT_BLOCK_ID
    if "report_block_candidate_tr" not in normalized or normalized.get("report_block_candidate_tr") in [None, ""]:
        missing_fields.append("report_block_candidate_tr")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    block_family = str(normalized.get("block_family") or "")
    if block_family not in ALLOWED_BLOCK_FAMILIES:
        missing_fields.append("block_family")

    forbidden_upstream_hits = _forbidden_upstream_hits(normalized)
    hard_block_hits: list[str] = []
    review_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("report_block_required_fields_missing")
    if _upstream_block_failed(normalized):
        hard_block_hits.append("upstream_report_block_failed_closed")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_report_block_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_claim_output_allowed")
    if normalized.get("production_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_production_output_allowed")
    if normalized.get("final_report_allowed") not in [False, None]:
        hard_block_hits.append("upstream_report_block_final_output_allowed")

    text = str(normalized.get("report_block_candidate_tr") or "")
    forbidden_block_hits = _forbidden_text_hits(text)
    if forbidden_block_hits:
        hard_block_hits.append("report_block_forbidden_language_detected")

    if block_family == "review_required_candidate":
        review_hits.append("block_family_requires_review")
    if normalized.get("canonical_event_count") not in [None, "UNKNOWN"]:
        hard_block_hits.append("canonical_event_count_claim_rejected")

    if hard_block_hits:
        inclusion_decision = "REJECT_BLOCK"
        status = "FAIL_CLOSED"
        output_text = ""
    elif review_hits:
        inclusion_decision = "REVIEW_BLOCK"
        status = "REVIEW_REQUIRED"
        output_text = ""
    else:
        inclusion_decision = "INCLUDE_BLOCK_CANDIDATE"
        status = "SMOKE_PASS"
        output_text = text

    return {
        "module_id": MODULE_ID,
        "contract_item_id": f"contract_{block_id}",
        "report_block_id": block_id,
        "block_family": block_family,
        "block_language": str(normalized.get("block_language") or "UNKNOWN"),
        "inclusion_decision": inclusion_decision,
        "output_text_candidate_tr": output_text,
        "claim_ceiling": OUTPUT_CONTRACT_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "status": status,
        "hard_block_hits": hard_block_hits,
        "review_hits": review_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "forbidden_block_hits": forbidden_block_hits,
        "claim_output_allowed": False,
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


def build_output_contract(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    items = [evaluate_report_block(block, idx) for idx, block in enumerate(blocks)]
    rejected_count = sum(1 for item in items if item["inclusion_decision"] == "REJECT_BLOCK")
    review_count = sum(1 for item in items if item["inclusion_decision"] == "REVIEW_BLOCK")
    include_count = sum(1 for item in items if item["inclusion_decision"] == "INCLUDE_BLOCK_CANDIDATE")
    status = "FAIL_CLOSED" if rejected_count else "REVIEW_REQUIRED" if review_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "contract_item_count": len(items),
        "include_count": include_count,
        "review_count": review_count,
        "rejected_count": rejected_count,
        "contract_items": items,
        "claim_output_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "claim_ceiling": OUTPUT_CONTRACT_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "report_output_contract_candidate_only_not_final_report",
    }


def write_outputs(blocks: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_output_contract(blocks)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA REPORT OUTPUT CONTRACT LITE V1",
        "====================================",
        f"status={report['status']}",
        f"contract_item_count={report['contract_item_count']}",
        f"include_count={report['include_count']}",
        f"review_count={report['review_count']}",
        f"rejected_count={report['rejected_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[contract_items]",
    ]
    for item in report["contract_items"][:50]:
        lines.append(f"- {item['contract_item_id']} decision={item['inclusion_decision']} status={item['status']}")
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
