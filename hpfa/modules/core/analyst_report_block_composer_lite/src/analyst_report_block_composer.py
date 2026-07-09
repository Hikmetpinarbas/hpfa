from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "analyst_report_block_composer_lite_v1"
OUTPUT_JSON = "analyst_report_block_composer_lite_v1.json"
OUTPUT_TXT = "analyst_report_block_composer_lite_v1.txt"

UPSTREAM_CLAIM_CEILING = "safe_sentence_candidate_only"
REPORT_BLOCK_CLAIM_CEILING = "analyst_report_block_candidate_only"
MISSING_SAFE_SENTENCE_ID = "MISSING_SAFE_SENTENCE_ID"

FORBIDDEN_UPSTREAM_FIELDS = {
    "claim_text",
    "report_text",
    "report_language",
    "final_report_text",
    "production_report",
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

FORBIDDEN_OUTPUT_FRAGMENTS = [
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


def _safe_sentence_id(item: dict[str, Any]) -> str:
    return str(item.get("safe_sentence_id") or "")


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _forbidden_upstream_hits(item: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for field in FORBIDDEN_UPSTREAM_FIELDS:
        if field in item and _is_forbidden_value(item.get(field)):
            hits.append(field)
    return sorted(hits)


def _upstream_safe_sentence_failed(item: dict[str, Any]) -> bool:
    if _as_list(item.get("hard_block_hits")):
        return True
    if str(item.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(item.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _forbidden_text_hits(text: str) -> list[str]:
    lower = text.lower()
    return [fragment for fragment in FORBIDDEN_OUTPUT_FRAGMENTS if fragment in lower]


def _sentence_text(item: dict[str, Any]) -> str:
    return str(item.get("safe_sentence_candidate_tr") or "")


def compose_report_block(item: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized = dict(item)
    safe_sentence_id = _safe_sentence_id(normalized)
    missing_fields: list[str] = []
    if not safe_sentence_id:
        missing_fields.append("safe_sentence_id")
        safe_sentence_id = MISSING_SAFE_SENTENCE_ID
    if "safe_sentence_candidate_tr" not in normalized or normalized.get("safe_sentence_candidate_tr") in [None, ""]:
        missing_fields.append("safe_sentence_candidate_tr")
    if normalized.get("claim_ceiling") != UPSTREAM_CLAIM_CEILING:
        missing_fields.append("claim_ceiling")

    sentence = _sentence_text(normalized)
    forbidden_upstream_hits = _forbidden_upstream_hits(normalized)
    hard_block_hits: list[str] = []
    if missing_fields:
        hard_block_hits.append("safe_sentence_required_fields_missing")
    if _upstream_safe_sentence_failed(normalized):
        hard_block_hits.append("upstream_safe_sentence_failed_closed")
    if forbidden_upstream_hits:
        hard_block_hits.append("upstream_safe_sentence_forbidden_output_attempted")
    if normalized.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_safe_sentence_claim_output_allowed")
    if normalized.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_safe_sentence_report_language_allowed")
    if normalized.get("safe_sentence_allowed") not in [True, None]:
        hard_block_hits.append("upstream_safe_sentence_not_allowed")
    if not sentence:
        hard_block_hits.append("safe_sentence_candidate_required")

    report_block_candidate_tr = "" if hard_block_hits else "Analist okuması: " + sentence
    forbidden_block_hits = _forbidden_text_hits(report_block_candidate_tr)
    if forbidden_block_hits:
        hard_block_hits.append("report_block_forbidden_language_detected")
        report_block_candidate_tr = ""

    status = "FAIL_CLOSED" if hard_block_hits else "SMOKE_PASS"
    decision = "BLOCK_REPORT_BLOCK" if hard_block_hits else "READY_FOR_REPORT_OUTPUT_CONTRACT_CANDIDATE"

    return {
        "module_id": MODULE_ID,
        "report_block_id": f"report_block_{safe_sentence_id}",
        "safe_sentence_id": safe_sentence_id,
        "report_block_candidate_tr": report_block_candidate_tr,
        "block_language": "tr",
        "block_family": "analyst_reading_candidate",
        "claim_ceiling": REPORT_BLOCK_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized.get("claim_ceiling"),
        "status": status,
        "decision": decision,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_upstream_hits": forbidden_upstream_hits,
        "forbidden_block_hits": forbidden_block_hits,
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
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


def build_report_block_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    blocks = [compose_report_block(item, idx) for idx, item in enumerate(items)]
    blocked_count = sum(1 for block in blocks if block["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "report_block_count": len(blocks),
        "blocked_report_block_count": blocked_count,
        "report_blocks": blocks,
        "claim_output_allowed": False,
        "production_report_allowed": False,
        "final_report_allowed": False,
        "claim_ceiling": REPORT_BLOCK_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "analyst_report_block_candidate_only_not_final_report",
    }


def write_outputs(items: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report_block_report(items)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA ANALYST REPORT BLOCK COMPOSER LITE V1",
        "============================================",
        f"status={report['status']}",
        f"report_block_count={report['report_block_count']}",
        f"blocked_report_block_count={report['blocked_report_block_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[report_block_candidates]",
    ]
    for block in report["report_blocks"][:50]:
        lines.append(f"- {block['report_block_id']} status={block['status']} decision={block['decision']}")
        if block["report_block_candidate_tr"]:
            lines.append(f"  {block['report_block_candidate_tr']}")
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
