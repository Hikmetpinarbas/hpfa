from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import reconstruction_intelligence_packet_adapter_current_v1 as reconstruction_bridge
from episode_lane_runner import run_current_episode_lane
from hpfa.modules.core.analyst_report_block_composer_lite.src.analyst_report_block_composer import (
    compose_report_block,
)
from hpfa.modules.core.composite_argument_builder_lite.src.composite_argument_builder import (
    build_argument_candidate,
)
from hpfa.modules.core.defeasible_argument_router_lite.src.defeasible_argument_router import (
    route_argument,
)
from hpfa.modules.core.evidence_graph_engine_lite.src.evidence_graph_engine import (
    build_evidence_graph,
)
from hpfa.modules.core.evidence_lens_matrix_lite.src.evidence_lens_matrix import (
    build_lens_matrix,
)
from hpfa.modules.core.final_report_assembly_gate_lite.src.final_report_assembly_gate import (
    evaluate_assembly_item,
)
from hpfa.modules.core.multi_signal_evidence_fusion_lite.src.multi_signal_evidence_fusion import (
    fuse_packet,
)
from hpfa.modules.core.report_output_contract_lite.src.report_output_contract import (
    evaluate_report_block,
)
from hpfa.modules.core.safe_argument_router_tr_lite.src.safe_argument_router_tr import (
    route_safe_sentence,
)

from spine_runner import validate_active_match_authority, validate_output_root


MODULE_ID = "active_match_full_spine_runner_v1"
OUTPUT_JSON = "active_match_full_spine_v1.json"
OUTPUT_TXT = "active_match_full_spine_v1.txt"
PACKET_REPORT_JSON = "composite_evidence_packet_builder_lite_v1.json"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


class FullSpineContractError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullSpineContractError(f"json_input_unreadable:{path.name}") from exc
    if not isinstance(payload, dict):
        raise FullSpineContractError(f"json_input_not_object:{path.name}")
    return payload


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _chain_has_fail(chain: dict[str, dict[str, Any]]) -> bool:
    blocking_tokens = {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED", "BLOCK_FUSION", "BLOCK_ARGUMENT"}
    for record in chain.values():
        values = {_status(record.get("status")), _status(record.get("decision"))}
        if values & blocking_tokens:
            return True
        if any(value.startswith("BLOCK") for value in values):
            return True
    return False


def _chain_has_review(chain: dict[str, dict[str, Any]]) -> bool:
    for record in chain.values():
        values = {
            _status(record.get("status")),
            _status(record.get("decision")),
            _status(record.get("defeasible_state")),
        }
        if any("REVIEW" in value or value == "WEAKENED" for value in values):
            return True
    return False


def run_intelligence_chain(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fusion = fuse_packet(packet)
    argument = build_argument_candidate(fusion)
    routed = route_argument(argument)
    graph = build_evidence_graph(routed)
    lens = build_lens_matrix(graph)
    safe_sentence = route_safe_sentence(graph)
    report_block = compose_report_block(safe_sentence)
    output_contract = evaluate_report_block(report_block)
    assembly = evaluate_assembly_item(output_contract)
    return {
        "packet": packet,
        "fusion": fusion,
        "argument": argument,
        "route": routed,
        "graph": graph,
        "lens": lens,
        "safe_sentence": safe_sentence,
        "report_block": report_block,
        "output_contract": output_contract,
        "assembly": assembly,
    }


def _first_failure(chains: list[dict[str, dict[str, Any]]]) -> tuple[str | None, str | None]:
    ordered = (
        "packet",
        "fusion",
        "argument",
        "route",
        "graph",
        "safe_sentence",
        "report_block",
        "output_contract",
        "assembly",
    )
    for chain in chains:
        for stage in ordered:
            record = chain.get(stage) or {}
            status = _status(record.get("status"))
            decision = _status(record.get("decision"))
            if status in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"} or decision.startswith("BLOCK"):
                reasons = record.get("hard_block_hits") or record.get("blocked_reasons") or record.get("review_reasons") or []
                reason = str(reasons[0]) if isinstance(reasons, list) and reasons else (decision or status)
                return stage, reason
    return None, None


def run_full_spine(
    *,
    active_match_dir: str | Path,
    out_dir: str | Path,
    execution_root: str | Path,
    bridge_runner: Callable[[str | Path, str | Path], dict[str, Any]] | None = None,
    episode_runner: Callable[[str | Path, str | Path, str | Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    execution_root_path = Path(execution_root).expanduser().resolve(strict=False)
    active_match_path = validate_active_match_authority(active_match_dir, execution_root_path)
    output_root = validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    episode_lane = episode_runner or run_current_episode_lane
    episode_report = episode_lane(active_match_path, output_root, execution_root_path)
    episode_status = _status(episode_report.get("status"))

    bridge = bridge_runner or reconstruction_bridge.runtime_write_outputs
    bridge_report = bridge(active_match_path, output_root)
    bridge_status = _status(bridge_report.get("status"))

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    chains: list[dict[str, dict[str, Any]]] = []
    first_failed_node: str | None = None
    first_failed_reason_code: str | None = None

    if episode_status == "FAIL_CLOSED":
        hard_blocks.append("current_episode_lane_fail_closed")
        first_failed_node = "episode_lane"
        reasons = episode_report.get("hard_block_hits") or []
        first_failed_reason_code = str(reasons[0]) if isinstance(reasons, list) and reasons else "episode_lane_fail_closed"
    elif episode_status == "REVIEW_REQUIRED":
        review_hits.append("current_episode_lane_review_required")

    if bridge_status == "FAIL_CLOSED":
        hard_blocks.append("reconstruction_intelligence_bridge_fail_closed")
        if first_failed_node is None:
            first_failed_node = "reconstruction_intelligence_bridge"
            reasons = bridge_report.get("hard_block_hits") or []
            first_failed_reason_code = str(reasons[0]) if isinstance(reasons, list) and reasons else "reconstruction_intelligence_bridge_fail_closed"
    else:
        packet_report_path = output_root / PACKET_REPORT_JSON
        try:
            packet_report = _load_json(packet_report_path)
        except FullSpineContractError as exc:
            packet_report = {}
            hard_blocks.append(str(exc))
            if first_failed_node is None:
                first_failed_node = "composite_packet_inventory"
                first_failed_reason_code = str(exc)

        packets = packet_report.get("packets") if isinstance(packet_report, dict) else []
        if not isinstance(packets, list) or not packets:
            hard_blocks.append("composite_packet_inventory_empty_or_invalid")
            if first_failed_node is None:
                first_failed_node = "composite_packet_inventory"
                first_failed_reason_code = "composite_packet_inventory_empty_or_invalid"
            packets = []

        declared_packet_count = packet_report.get("packet_count") if isinstance(packet_report, dict) else None
        if isinstance(declared_packet_count, int) and declared_packet_count != len(packets):
            hard_blocks.append("composite_packet_count_mismatch")
            if first_failed_node is None:
                first_failed_node = "composite_packet_inventory"
                first_failed_reason_code = "composite_packet_count_mismatch"

        for packet in packets:
            if not isinstance(packet, dict):
                hard_blocks.append("composite_packet_record_invalid")
                if first_failed_node is None:
                    first_failed_node = "composite_packet_inventory"
                    first_failed_reason_code = "composite_packet_record_invalid"
                continue
            chains.append(run_intelligence_chain(packet))

    failed_chain_count = sum(_chain_has_fail(chain) for chain in chains)
    review_chain_count = sum(_chain_has_review(chain) for chain in chains)
    chain_failed_node, chain_failed_reason = _first_failure(chains)
    if first_failed_node is None and chain_failed_node is not None:
        first_failed_node = chain_failed_node
        first_failed_reason_code = chain_failed_reason

    if failed_chain_count:
        hard_blocks.append("intelligence_chain_fail_closed")
    if bridge_status == "REVIEW_REQUIRED":
        review_hits.append("reconstruction_intelligence_bridge_review_required")
    if review_chain_count:
        review_hits.append("intelligence_chain_review_required")

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    if hard_blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_FULL_SPINE"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "FULL_SPINE_COMPLETED_REVIEW_REQUIRED"
    else:
        status = "SMOKE_PASS"
        decision = "FULL_SPINE_EXECUTION_COMPLETED"

    report = {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "decision": decision,
        "runtime_evidence_status": "NOT_EVALUATED",
        "active_match_evidence_pass": False,
        "active_match_authority": str(active_match_path),
        "execution_root": str(execution_root_path),
        "episode_lane_status": episode_report.get("status"),
        "episode_candidate_count": episode_report.get("episode_candidate_count"),
        "episode_feature_vector_count": episode_report.get("episode_feature_vector_count"),
        "temporal_episode_signature_status": episode_report.get("temporal_episode_signature_status"),
        "temporal_episode_signature_count": episode_report.get("temporal_episode_signature_count"),
        "reconstruction_intelligence_bridge_status": bridge_report.get("status"),
        "match_surface_binding_id": bridge_report.get("match_surface_binding_id"),
        "composite_packet_count": len(chains),
        "intelligence_chain_count": len(chains),
        "failed_intelligence_chain_count": failed_chain_count,
        "review_required_intelligence_chain_count": review_chain_count,
        "first_failed_node": first_failed_node,
        "first_failed_reason_code": first_failed_reason_code,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "episode_lane": episode_report,
        "intelligence_chains": chains,
        "engineering_evidence": {
            "single_active_match_authority_validated": True,
            "current_context_episode_feature_lane_reused": True,
            "current_temporal_episode_signature_reused": True,
            "current_reconstruction_bridge_reused": True,
            "current_c4_producers_reused": True,
            "parallel_reasoning_engine_created": False,
            "first_failure_disclosure_enabled": True,
            "duplicate_foundation_execution_currently_possible": True,
        },
        "analyst_evidence": {
            "episode_candidate_count": episode_report.get("episode_candidate_count"),
            "episode_feature_vector_count": episode_report.get("episode_feature_vector_count"),
            "temporal_episode_signature_count": episode_report.get("temporal_episode_signature_count"),
            "packet_level_report_candidates_generated": len(chains),
            "counterevidence_preserved_by_current_c4_chain": True,
            "absence_is_counterevidence": False,
            "safe_report_language_only": True,
        },
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }

    (output_root / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "HPFA ACTIVE_MATCH FULL SPINE V1",
        "===============================",
        f"status={status}",
        f"decision={decision}",
        f"episode_lane_status={episode_report.get('status')}",
        f"episode_candidate_count={episode_report.get('episode_candidate_count')}",
        f"episode_feature_vector_count={episode_report.get('episode_feature_vector_count')}",
        f"temporal_episode_signature_count={episode_report.get('temporal_episode_signature_count')}",
        f"bridge_status={bridge_report.get('status')}",
        f"intelligence_chain_count={len(chains)}",
        f"failed_intelligence_chain_count={failed_chain_count}",
        f"review_required_intelligence_chain_count={review_chain_count}",
        f"first_failed_node={first_failed_node}",
        f"first_failed_reason_code={first_failed_reason_code}",
        f"hard_block_hits={hard_blocks}",
        f"review_hits={review_hits}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "possession_truth=false",
        "sequence_truth=false",
        "rhythm_truth=false",
        "tactical_truth=false",
        "production_release=false",
        "",
    ]
    (output_root / OUTPUT_TXT).write_text("\n".join(lines), encoding="utf-8")
    return report
