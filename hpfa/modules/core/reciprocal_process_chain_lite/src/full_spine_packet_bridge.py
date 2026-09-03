from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

MODULE_ID = "reciprocal_full_spine_packet_bridge_v1"
OUTPUT_JSON = "reciprocal_full_spine_packet_bridge_v1.json"
OUTPUT_TXT = "reciprocal_full_spine_packet_bridge_v1.txt"


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def bridge_reciprocal_packets(
    *,
    active_match_dir: str | Path,
    out_dir: str | Path,
    reciprocal_runner: Callable[[str | Path, str | Path], dict[str, Any]],
    packet_builder: Callable[[dict[str, Any]], dict[str, Any]],
    intelligence_runner: Callable[[dict[str, Any]], dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Project current reciprocal C4 candidates through the existing intelligence chain.

    This bridge creates no occurrences, episodes, evidence votes or reasoning engine.
    It only invokes already-existing producers and records whether their candidate
    packets can traverse the current C4 chain without opening claim ceilings.
    """
    output_root = Path(out_dir).expanduser().resolve(strict=False)
    output_root.mkdir(parents=True, exist_ok=True)

    reciprocal = reciprocal_runner(active_match_dir, output_root)
    reciprocal_status = _status(reciprocal.get("status"))
    candidates = reciprocal.get("reciprocal_c4_packet_candidates") or []
    if not isinstance(candidates, list):
        candidates = []

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    chains: list[dict[str, Any]] = []
    packet_count = 0

    if reciprocal_status == "FAIL_CLOSED":
        hard_blocks.append("reciprocal_process_chain_fail_closed")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                review_hits.append("non_object_reciprocal_c4_candidate_ignored")
                continue
            packet = packet_builder(candidate)
            if not isinstance(packet, dict):
                hard_blocks.append("existing_packet_builder_returned_non_object")
                break
            if packet.get("hard_block_hits"):
                review_hits.append("reciprocal_packet_not_admitted_by_existing_packet_builder")
                continue
            chain = intelligence_runner(packet)
            chains.append({
                "candidate_id": candidate.get("candidate_id") or candidate.get("finding_input_id"),
                "packet": packet,
                "chain": chain,
            })
            packet_count += 1

    claim_output_allowed_count = 0
    completed_chain_count = 0
    for row in chains:
        chain = row.get("chain") or {}
        assembly = chain.get("assembly") if isinstance(chain, dict) else None
        output_contract = chain.get("output_contract") if isinstance(chain, dict) else None
        if isinstance(output_contract, dict) and output_contract.get("claim_output_allowed") is True:
            claim_output_allowed_count += 1
        if isinstance(assembly, dict) and _status(assembly.get("status")) not in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"}:
            completed_chain_count += 1

    status = "FAIL_CLOSED" if hard_blocks else "REVIEW_REQUIRED"
    report = {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BLOCK_MATCH_TOMOGRAPHY_BRIDGE" if hard_blocks else "RECIPROCAL_MATCH_TOMOGRAPHY_CANDIDATES_PROJECTED",
        "reciprocal_process_status": reciprocal.get("status"),
        "reciprocal_process_chain_candidate_count": reciprocal.get("reciprocal_process_chain_candidate_count"),
        "outcome_contrast_candidate_count": reciprocal.get("outcome_contrast_candidate_count"),
        "different_outcome_analogue_link_count": reciprocal.get("different_outcome_analogue_link_count"),
        "defeasible_process_finding_input_count": reciprocal.get("defeasible_process_finding_input_count"),
        "reciprocal_c4_packet_candidate_count": len(candidates),
        "existing_packet_builder_admitted_count": packet_count,
        "existing_intelligence_chain_completed_candidate_count": completed_chain_count,
        "claim_output_allowed_count": claim_output_allowed_count,
        "chains": chains,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "creates_parallel_engine": False,
        "creates_occurrence": False,
        "creates_episode": False,
        "creates_independent_evidence": False,
        "creates_final_finding": False,
        "active_match_evidence_pass": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    json_path = output_root / OUTPUT_JSON
    txt_path = output_root / OUTPUT_TXT
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA RECIPROCAL FULL-SPINE PACKET BRIDGE V1",
        f"status={status}",
        f"reciprocal_c4_packet_candidate_count={len(candidates)}",
        f"existing_packet_builder_admitted_count={packet_count}",
        f"existing_intelligence_chain_completed_candidate_count={completed_chain_count}",
        f"claim_output_allowed_count={claim_output_allowed_count}",
        "creates_parallel_engine=false",
        "active_match_evidence_pass=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    report["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return report
