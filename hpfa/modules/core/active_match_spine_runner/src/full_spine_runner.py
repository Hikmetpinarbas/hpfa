from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import reconstruction_intelligence_packet_adapter_current_v1 as reconstruction_bridge
from episode_lane_runner import run_current_episode_lane
from hpfa.modules.core.analyst_report_block_composer_lite.src.analyst_report_block_composer import compose_report_block
from hpfa.modules.core.composite_argument_builder_lite.src.composite_argument_builder import build_argument_candidate
from hpfa.modules.core.defeasible_argument_router_lite.src.defeasible_argument_router import route_argument
from hpfa.modules.core.evidence_graph_engine_lite.src.evidence_graph_engine import build_evidence_graph
from hpfa.modules.core.evidence_lens_matrix_lite.src.evidence_lens_matrix import build_lens_matrix
from hpfa.modules.core.final_report_assembly_gate_lite.src.final_report_assembly_gate import evaluate_assembly_item
from hpfa.modules.core.multi_signal_evidence_fusion_lite.src.multi_signal_evidence_fusion import fuse_packet
from hpfa.modules.core.report_output_contract_lite.src.report_output_contract import evaluate_report_block
from hpfa.modules.core.safe_argument_router_tr_lite.src.safe_argument_router_tr import route_safe_sentence
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


def _stage_failure(stage: str, exc: Exception) -> dict[str, Any]:
    return {
        "module_id": f"full_spine_{stage}_failure_v1",
        "status": "FAIL_CLOSED",
        "decision": "BLOCK_FULL_SPINE",
        "hard_block_hits": [f"c4_stage_exception:{stage}:{type(exc).__name__}"],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }


def _chain_has_fail(chain: dict[str, dict[str, Any]]) -> bool:
    blocking = {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED", "BLOCK_FUSION", "BLOCK_ARGUMENT"}
    for record in chain.values():
        values = {_status(record.get("status")), _status(record.get("decision"))}
        if values & blocking or any(value.startswith("BLOCK") for value in values):
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


def run_intelligence_chain(
    packet: dict[str, Any],
    stage_overrides: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Reuse the current C4 producer chain with exception containment only.

    Explicit producer FAIL/REVIEW artifacts are still passed downstream because
    current C4 consumers are responsible for preserving and contracting those
    states. Only an actual Python exception stops execution at the boundary.
    """
    overrides = stage_overrides or {}
    stages: tuple[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]], ...] = (
        ("fusion", overrides.get("fusion", fuse_packet)),
        ("argument", overrides.get("argument", build_argument_candidate)),
        ("route", overrides.get("route", route_argument)),
        ("graph", overrides.get("graph", build_evidence_graph)),
        ("lens", overrides.get("lens", build_lens_matrix)),
        ("safe_sentence", overrides.get("safe_sentence", route_safe_sentence)),
        ("report_block", overrides.get("report_block", compose_report_block)),
        ("output_contract", overrides.get("output_contract", evaluate_report_block)),
        ("assembly", overrides.get("assembly", evaluate_assembly_item)),
    )
    chain: dict[str, dict[str, Any]] = {"packet": packet}
    current = packet
    for stage_name, producer in stages:
        try:
            output = producer(current)
            if not isinstance(output, dict):
                raise TypeError("stage_output_must_be_dict")
        except Exception as exc:
            chain[stage_name] = _stage_failure(stage_name, exc)
            break
        chain[stage_name] = output
        current = output
    return chain


def _first_failure(chains: list[dict[str, dict[str, Any]]]) -> tuple[str | None, str | None]:
    order = (
        "packet",
        "fusion",
        "argument",
        "route",
        "graph",
        "lens",
        "safe_sentence",
        "report_block",
        "output_contract",
        "assembly",
    )
    for chain in chains:
        for stage in order:
            record = chain.get(stage) or {}
            status = _status(record.get("status"))
            decision = _status(record.get("decision"))
            if status in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"} or decision.startswith("BLOCK"):
                reasons = record.get("hard_block_hits") or record.get("blocked_reasons") or record.get("review_reasons") or []
                reason = str(reasons[0]) if isinstance(reasons, list) and reasons else (decision or status)
                return stage, reason
    return None, None


def _safe_external_call(
    runner: Callable[..., dict[str, Any]],
    args: tuple[Any, ...],
    stage: str,
) -> dict[str, Any]:
    try:
        result = runner(*args)
        if not isinstance(result, dict):
            raise TypeError("stage_output_must_be_dict")
        return result
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "hard_block_hits": [f"{stage}_exception:{type(exc).__name__}"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }


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

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    chains: list[dict[str, dict[str, Any]]] = []
    first_failed_node: str | None = None
    first_failed_reason_code: str | None = None

    bridge = bridge_runner or reconstruction_bridge.runtime_write_outputs
    bridge_report = _safe_external_call(
        bridge,
        (active_match_path, output_root),
        "reconstruction_bridge",
    )
    bridge_status = _status(bridge_report.get("status"))
    if bridge_status == "FAIL_CLOSED":
        hard_blocks.append("reconstruction_intelligence_bridge_fail_closed")
        first_failed_node = "reconstruction_intelligence_bridge"
        reasons = bridge_report.get("hard_block_hits") or []
        first_failed_reason_code = str(reasons[0]) if isinstance(reasons, list) and reasons else "reconstruction_intelligence_bridge_fail_closed"
    elif bridge_status == "REVIEW_REQUIRED":
        review_hits.append("reconstruction_intelligence_bridge_review_required")

    episode_report: dict[str, Any] = {
        "status": "NOT_EVALUATED",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    if not hard_blocks:
        episode_lane = episode_runner or run_current_episode_lane
        episode_report = _safe_external_call(
            episode_lane,
            (active_match_path, output_root, execution_root_path),
            "episode_lane",
        )
        episode_status = _status(episode_report.get("status"))
        if episode_status == "FAIL_CLOSED":
            hard_blocks.append("current_episode_lane_fail_closed")
            first_failed_node = first_failed_node or "episode_lane"
            reasons = episode_report.get("hard_block_hits") or []
            first_failed_reason_code = first_failed_reason_code or (
                str(reasons[0]) if isinstance(reasons, list) and reasons else "episode_lane_fail_closed"
            )
        elif episode_status == "REVIEW_REQUIRED":
            review_hits.append("current_episode_lane_review_required")

    if not hard_blocks:
        try:
            packet_report = _load_json(output_root / PACKET_REPORT_JSON)
        except FullSpineContractError as exc:
            packet_report = {}
            hard_blocks.append(str(exc))
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or str(exc)

        packets = packet_report.get("packets") if isinstance(packet_report, dict) else []
        if not isinstance(packets, list) or not packets:
            hard_blocks.append("composite_packet_inventory_empty_or_invalid")
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or "composite_packet_inventory_empty_or_invalid"
            packets = []

        declared_packet_count = packet_report.get("packet_count") if isinstance(packet_report, dict) else None
        if isinstance(declared_packet_count, int) and declared_packet_count != len(packets):
            hard_blocks.append("composite_packet_count_mismatch")
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or "composite_packet_count_mismatch"

        if not hard_blocks:
            for packet in packets:
                if not isinstance(packet, dict):
                    hard_blocks.append("composite_packet_record_invalid")
                    first_failed_node = first_failed_node or "composite_packet_inventory"
                    first_failed_reason_code = first_failed_reason_code or "composite_packet_record_invalid"
                    continue
                chains.append(run_intelligence_chain(packet))

    failed_chain_count = sum(_chain_has_fail(chain) for chain in chains)
    review_chain_count = sum(_chain_has_review(chain) for chain in chains)
    chain_node, chain_reason = _first_failure(chains)
    if first_failed_node is None and chain_node is not None:
        first_failed_node, first_failed_reason_code = chain_node, chain_reason
    if failed_chain_count:
        hard_blocks.append("intelligence_chain_fail_closed")
    if review_chain_count:
        review_hits.append("intelligence_chain_review_required")

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    if hard_blocks:
        status, decision = "FAIL_CLOSED", "BLOCK_FULL_SPINE"
    elif review_hits:
        status, decision = "REVIEW_REQUIRED", "FULL_SPINE_COMPLETED_REVIEW_REQUIRED"
    else:
        status, decision = "SMOKE_PASS", "FULL_SPINE_EXECUTION_COMPLETED"

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
            "shared_foundation_reused": True,
            "row_nucleus_recomputed_by_episode_lane": False,
            "current_context_episode_feature_lane_reused": True,
            "current_temporal_episode_signature_reused": True,
            "current_reconstruction_bridge_reused": True,
            "current_c4_producers_reused": True,
            "c4_stage_exception_containment_enabled": True,
            "parallel_reasoning_engine_created": False,
            "first_failure_disclosure_enabled": True,
            "duplicate_foundation_execution_currently_possible": False,
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
    (output_root / OUTPUT_TXT).write_text(
        "\n".join(
            [
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
                f"first_failed_node={first_failed_node}",
                f"first_failed_reason_code={first_failed_reason_code}",
                f"hard_block_hits={hard_blocks}",
                f"review_hits={review_hits}",
                "shared_foundation_reused=true",
                "row_nucleus_recomputed_by_episode_lane=false",
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
        ),
        encoding="utf-8",
    )
    return report
