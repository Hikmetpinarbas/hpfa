from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.partial_order_trace_variant_lite.src.partial_order_trace_variant import (
    build_partial_order_trace_variants,
)
from hpfa.modules.core.trace_similarity_primitive_lite.src.trace_similarity_primitive import (
    build_trace_similarity_primitive,
)
from hpfa.modules.core.trace_contrast_packet_lite.src.trace_contrast_packet import (
    build_trace_contrast_packets,
)
from hpfa.modules.core.process_robustness_lens_lite.src.recurrence_robustness_envelope import (
    build_recurrence_robustness_envelopes,
)
from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_pattern_admission import (
    build_sequence_pattern_admissions,
)
from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_safe_finding_binding import (
    build_sequence_safe_finding_blocks,
)
from hpfa.modules.core.professional_finding_candidate_lite.src.sequence_analyst_narrative import (
    compose_sequence_analyst_narrative,
)
from hpfa.modules.core.professional_finding_candidate_lite.src.match_story_synthesis import (
    synthesize_match_story,
)
from hpfa.modules.core.analyst_report_block_composer_lite.src.match_story_report_projection import (
    compose_match_story_report,
)
from hpfa.modules.core.report_output_contract_lite.src.report_output_contract import evaluate_report_block
from hpfa.modules.core.final_report_assembly_gate_lite.src.final_report_assembly_gate import evaluate_assembly_item

MODULE_ID = "active_match_process_story_sidecar_v1"
OUTPUT_JSON = "active_match_process_story_sidecar_v1.json"
OUTPUT_TXT = "active_match_process_story_sidecar_v1.txt"
SEQUENCE_JSON = "visible_action_sequence_candidates_lite_v1.json"
TRACE_JSON = "trackable_action_trace_candidates_lite_v1.json"
CONSEQUENCE_JSON = "trackable_action_consequence_candidates_lite_v1.json"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
MATCH_STORY_BLOCK_FAMILY = "match_story_analyst_reading_candidate"
READY_ASSEMBLY_DECISION = "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"

# Explicit exploratory parameters. They are required by the current similarity /
# contrast contracts and are never represented as calibrated football truth.
SIMILARITY_WEIGHTS = {"action": 1.0, "order": 1.0, "context": 1.0}
MINIMUM_SIMILARITY = 0.80
ROBUSTNESS_THRESHOLDS = (0.70, 0.80, 0.90)


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("module_status") or "UNKNOWN").strip().upper()


def _stage_record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "module_id": payload.get("module_id"),
        "status": payload.get("status") or payload.get("module_status"),
        "decision": payload.get("decision"),
        "hard_block_hits": list(payload.get("hard_block_hits") or []),
        "review_hits": list(payload.get("review_hits") or []),
        "canonical_event_count": payload.get("canonical_event_count", CANONICAL_EVENT_COUNT),
        "true_action_count": payload.get("true_action_count", TRUE_ACTION_COUNT),
        "production_release": bool(payload.get("production_release") is True),
    }


def _not_evaluated(reason: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "PROCESS_STORY_NOT_EVALUATED_PREREQUISITE_MISSING",
        "story_path_blocked": True,
        "story_path_block_reason": reason,
        "entity_stories": [],
        "entity_story_count": 0,
        "report_blocks": [],
        "report_block_count": 0,
        "assembly_items": [],
        "assembly_item_count": 0,
        "stage_statuses": {},
        "hard_block_hits": [],
        "review_hits": [reason],
        "current_invocation_artifacts": [],
        "exploratory_similarity_parameters": {
            "minimum_similarity": MINIMUM_SIMILARITY,
            "weights": dict(SIMILARITY_WEIGHTS),
            "robustness_thresholds": list(ROBUSTNESS_THRESHOLDS),
            "calibrated": False,
            "universal_football_truth": False,
        },
        "nominal_support_is_independent_evidence_count": False,
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def build_process_story_from_current_reconstruction(output_root: str | Path) -> dict[str, Any]:
    """Build a match-local process story only from current reconstruction artifacts.

    This bridge deliberately does not rerun source ingestion or reconstruction. If the
    current invocation did not produce sequence/trace/consequence artifacts, the story
    lane is not evaluated instead of reading stale outputs or creating a parallel engine.
    """
    root = Path(output_root).expanduser().resolve(strict=False)
    sequence_payload = _load(root / SEQUENCE_JSON)
    trace_payload = _load(root / TRACE_JSON)
    consequence_payload = _load(root / CONSEQUENCE_JSON)
    missing = [
        name
        for name, payload in (
            (SEQUENCE_JSON, sequence_payload),
            (TRACE_JSON, trace_payload),
            (CONSEQUENCE_JSON, consequence_payload),
        )
        if not payload
    ]
    if missing:
        return _not_evaluated("current_reconstruction_story_prerequisite_missing:" + ",".join(sorted(missing)))

    variant = build_partial_order_trace_variants(sequence_payload, trace_payload, consequence_payload)
    similarity = build_trace_similarity_primitive(variant, weights=SIMILARITY_WEIGHTS)
    contrast = build_trace_contrast_packets(
        variant,
        similarity,
        minimum_similarity=MINIMUM_SIMILARITY,
        eligibility_weights=SIMILARITY_WEIGHTS,
    )
    robustness = build_recurrence_robustness_envelopes(
        variant,
        contrast,
        tested_similarity_thresholds=ROBUSTNESS_THRESHOLDS,
    )
    admission = build_sequence_pattern_admissions(variant, contrast, robustness)
    binding = build_sequence_safe_finding_blocks(admission)
    narrative = compose_sequence_analyst_narrative(binding)
    story = synthesize_match_story(narrative)
    report = compose_match_story_report(story)

    stages = {
        "partial_order_trace_variant": variant,
        "trace_similarity": similarity,
        "trace_contrast": contrast,
        "recurrence_robustness": robustness,
        "sequence_pattern_admission": admission,
        "sequence_safe_finding": binding,
        "sequence_analyst_narrative": narrative,
        "match_story_synthesis": story,
        "match_story_report_projection": report,
    }
    first_fail = next((name for name, payload in stages.items() if _status(payload) == "FAIL_CLOSED"), None)

    contract_items: list[dict[str, Any]] = []
    assembly_items: list[dict[str, Any]] = []
    if first_fail is None:
        for idx, block in enumerate(report.get("report_blocks") or []):
            if not isinstance(block, dict):
                continue
            contract = evaluate_report_block(block, idx)
            contract_items.append(contract)
            assembly_items.append(evaluate_assembly_item(contract, idx))

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    for name, payload in stages.items():
        if _status(payload) == "FAIL_CLOSED":
            hard_blocks.append(f"{name}_fail_closed")
        elif _status(payload) == "REVIEW_REQUIRED":
            review_hits.append(f"{name}_review_required")
    if any(_status(item) == "FAIL_CLOSED" for item in contract_items + assembly_items):
        hard_blocks.append("report_or_assembly_fail_closed")
    if any(_status(item) == "REVIEW_REQUIRED" for item in contract_items + assembly_items):
        review_hits.append("report_or_assembly_review_required")

    # The sidecar itself is non-blocking to unrelated full-spine lanes. Internal hard
    # blocks close only this story path and are exposed explicitly for diagnosis.
    story_path_blocked = bool(hard_blocks)
    ready_assembly_count = sum(
        1
        for item in assembly_items
        if item.get("assembly_decision") == READY_ASSEMBLY_DECISION
    )
    status = "REVIEW_REQUIRED" if hard_blocks or review_hits else "SMOKE_PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "PROCESS_STORY_PATH_BLOCKED" if story_path_blocked else "PROCESS_STORY_RUNTIME_CANDIDATES_BUILT",
        "story_path_blocked": story_path_blocked,
        "story_path_block_reason": hard_blocks[0] if hard_blocks else None,
        "entity_stories": list(story.get("entity_stories") or []) if not story_path_blocked else [],
        "entity_story_count": int(story.get("entity_story_count") or 0) if not story_path_blocked else 0,
        "report_blocks": list(report.get("report_blocks") or []) if not story_path_blocked else [],
        "report_block_count": int(report.get("report_block_count") or 0) if not story_path_blocked else 0,
        "contract_items": contract_items if not story_path_blocked else [],
        "contract_item_count": len(contract_items) if not story_path_blocked else 0,
        "assembly_items": assembly_items if not story_path_blocked else [],
        "assembly_item_count": len(assembly_items) if not story_path_blocked else 0,
        "ready_assembly_item_count": ready_assembly_count if not story_path_blocked else 0,
        "stage_statuses": {name: _stage_record(payload) for name, payload in stages.items()},
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "exploratory_similarity_parameters": {
            "minimum_similarity": MINIMUM_SIMILARITY,
            "weights": dict(SIMILARITY_WEIGHTS),
            "robustness_thresholds": list(ROBUSTNESS_THRESHOLDS),
            "calibrated": False,
            "universal_football_truth": False,
        },
        "reconstruction_artifacts_reused_without_reingest": True,
        "parallel_sequence_engine_created": False,
        "nominal_support_is_independent_evidence_count": False,
        "chronological_story_claimed": False,
        "tactical_plan_truth_claimed": False,
        "coach_intention_claimed": False,
        "causality_claimed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def _publishable_match_story_assembly(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if _status(item) != "SMOKE_PASS":
        return False
    if item.get("assembly_decision") != READY_ASSEMBLY_DECISION:
        return False
    if item.get("draft_report_candidate_allowed") is not True:
        return False
    if item.get("block_family") != MATCH_STORY_BLOCK_FAMILY:
        return False
    if not str(item.get("assembly_item_candidate_tr") or "").strip():
        return False

    lineage = item.get("match_story_evidence_lineage")
    if not isinstance(lineage, dict) or not lineage:
        return False
    source_ids = lineage.get("source_narrative_ids")
    process_count = lineage.get("process_narrative_count")
    subprocess_fields = (
        "recurrent_process_count",
        "robust_recurrent_process_count",
        "counterevidence_bearing_process_count",
        "context_sensitive_process_count",
        "null_evaluated_process_count",
    )
    if not isinstance(source_ids, list) or not source_ids:
        return False
    if any(not isinstance(source_id, str) or not source_id for source_id in source_ids):
        return False
    if len(set(source_ids)) != len(source_ids):
        return False
    if not isinstance(process_count, int) or isinstance(process_count, bool):
        return False
    if process_count < 1 or process_count != len(source_ids):
        return False
    for field in subprocess_fields:
        value = lineage.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            return False
        if value < 0 or value > process_count:
            return False
    if lineage["robust_recurrent_process_count"] > lineage["recurrent_process_count"]:
        return False
    if lineage.get("nominal_support_is_independent_evidence_count") is not False:
        return False
    if lineage.get("cross_process_support_independence_proven") is not False:
        return False
    return True


def write_process_story_sidecar(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    report = build_process_story_from_current_reconstruction(root)
    json_path = root / OUTPUT_JSON
    txt_path = root / OUTPUT_TXT
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    admitted = [
        item for item in report.get("assembly_items") or []
        if _publishable_match_story_assembly(item)
    ]
    lines = [
        "HPFA ACTIVE_MATCH PROCESS STORY SIDECAR V1",
        "==========================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"story_path_blocked={str(bool(report.get('story_path_blocked'))).lower()}",
        f"entity_story_count={report.get('entity_story_count')}",
        f"report_block_count={report.get('report_block_count')}",
        f"assembly_item_count={report.get('assembly_item_count')}",
        f"ready_assembly_item_count={report.get('ready_assembly_item_count')}",
        f"publication_admitted_match_story_count={len(admitted)}",
        f"review_hits={report.get('review_hits') or []}",
        f"hard_block_hits={report.get('hard_block_hits') or []}",
        "similarity_parameters_calibrated=false",
        "nominal_support_is_independent_evidence_count=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
        "[assembly_admitted_match_story]",
    ]
    for item in admitted:
        lineage = item["match_story_evidence_lineage"]
        lines.append(f"- text={item.get('assembly_item_candidate_tr')}")
        lines.append(f"  process_narrative_count={lineage.get('process_narrative_count')}")
        lines.append(f"  recurrent_process_count={lineage.get('recurrent_process_count')}")
        lines.append(f"  robust_recurrent_process_count={lineage.get('robust_recurrent_process_count')}")
        lines.append(f"  counterevidence_bearing_process_count={lineage.get('counterevidence_bearing_process_count')}")
        lines.append(f"  context_sensitive_process_count={lineage.get('context_sensitive_process_count')}")
        lines.append(f"  null_evaluated_process_count={lineage.get('null_evaluated_process_count')}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return report
