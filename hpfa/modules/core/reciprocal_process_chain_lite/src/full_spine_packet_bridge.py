from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

MODULE_ID = "reciprocal_full_spine_packet_bridge_v1"
OUTPUT_JSON = "reciprocal_full_spine_packet_bridge_v1.json"
OUTPUT_TXT = "reciprocal_full_spine_packet_bridge_v1.txt"


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _build_tomography_coverage(reciprocal: dict[str, Any], chains: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize defeasible reciprocal coverage without producing a finding.

    This is an accounting surface over already-produced finding inputs. It does not
    interpret absence as support, does not count dependent analogues as independent
    votes and does not promote any C4/report claim.
    """
    rows = reciprocal.get("defeasible_process_finding_inputs") or []
    rows = rows if isinstance(rows, list) else []
    states: Counter[str] = Counter()
    with_counterevidence = 0
    with_dependent_support = 0
    isolated = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("evidence_balance_state_candidate") or "UNKNOWN")
        states[state] += 1
        counter_ids = row.get("counterevidence_chain_ids") or []
        support_ids = row.get("dependent_support_chain_ids") or []
        if isinstance(counter_ids, list) and counter_ids:
            with_counterevidence += 1
        if isinstance(support_ids, list) and support_ids:
            with_dependent_support += 1
        if not counter_ids and not support_ids:
            isolated += 1

    return {
        "surface_id": "reciprocal_match_tomography_coverage_v1",
        "status": "REVIEW_REQUIRED",
        "finding_input_count": len(rows),
        "finding_inputs_with_counterevidence_count": with_counterevidence,
        "finding_inputs_with_dependent_support_count": with_dependent_support,
        "isolated_finding_input_count": isolated,
        "evidence_balance_state_candidate_counts": dict(sorted(states.items())),
        "existing_intelligence_chain_projection_count": len(chains),
        "absence_of_counterevidence_is_confirmation": False,
        "dependent_support_is_independent_vote": False,
        "coverage_is_team_tendency_truth": False,
        "coverage_is_tactical_truth": False,
        "coverage_is_causal_truth": False,
        "finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


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

    tomography_coverage = _build_tomography_coverage(reciprocal, chains)
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
        "match_tomography_coverage": tomography_coverage,
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
        f"tomography_finding_input_count={tomography_coverage.get('finding_input_count', 0)}",
        f"tomography_with_counterevidence_count={tomography_coverage.get('finding_inputs_with_counterevidence_count', 0)}",
        f"tomography_with_dependent_support_count={tomography_coverage.get('finding_inputs_with_dependent_support_count', 0)}",
        f"tomography_isolated_count={tomography_coverage.get('isolated_finding_input_count', 0)}",
        "tomography_claim_output_allowed=false",
        "creates_parallel_engine=false",
        "active_match_evidence_pass=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    report["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return report
