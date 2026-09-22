from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import reconstruction_intelligence_packet_adapter_current_v1 as reconstruction_bridge
from episode_lane_runner import run_current_episode_lane
from orphan_capability_sidecars import run_sidecars
from rich_multiformat_analysis_lane import run_rich_lane
from hpfa.modules.core.analyst_report_block_composer_lite.src.analyst_report_block_composer import compose_report_block
from hpfa.modules.core.composite_argument_builder_lite.src.composite_argument_builder import build_argument_candidate
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet
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
FUSED_PACKET_JSON = "active_match_fused_packet_inventory_v1.json"
FUSED_PACKET_TXT = "active_match_fused_packet_inventory_v1.txt"
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


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _collect_current_artifacts(*payloads: dict[str, Any], extra: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for payload in payloads:
        values = payload.get("current_invocation_artifacts")
        if not isinstance(values, list):
            continue
        for value in values:
            text = str(value or "").strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
    for value in extra or []:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


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


def _chain_completed(chain: dict[str, dict[str, Any]]) -> bool:
    required = ("fusion", "argument", "route", "graph", "safe_sentence", "report_block", "output_contract", "assembly")
    return all(isinstance(chain.get(stage), dict) for stage in required) and not _chain_has_fail(chain)


def run_intelligence_chain(packet: dict[str, Any], stage_overrides: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None) -> dict[str, dict[str, Any]]:
    overrides = stage_overrides or {}
    chain: dict[str, dict[str, Any]] = {"packet": packet}
    stages = (
        ("fusion", "packet", overrides.get("fusion", fuse_packet)),
        ("argument", "fusion", overrides.get("argument", build_argument_candidate)),
        ("route", "argument", overrides.get("route", route_argument)),
        ("graph", "route", overrides.get("graph", build_evidence_graph)),
        ("lens", "graph", overrides.get("lens", build_lens_matrix)),
        ("safe_sentence", "graph", overrides.get("safe_sentence", route_safe_sentence)),
        ("report_block", "safe_sentence", overrides.get("report_block", compose_report_block)),
        ("output_contract", "report_block", overrides.get("output_contract", evaluate_report_block)),
        ("assembly", "output_contract", overrides.get("assembly", evaluate_assembly_item)),
    )
    for stage_name, input_stage, producer in stages:
        try:
            output = producer(chain[input_stage])
            if not isinstance(output, dict):
                raise TypeError("stage_output_must_be_dict")
        except Exception as exc:
            chain[stage_name] = _stage_failure(stage_name, exc)
            if stage_name != "lens":
                break
            continue
        chain[stage_name] = output
    return chain


def _first_failure(chains: list[dict[str, dict[str, Any]]]) -> tuple[str | None, str | None]:
    for chain in chains:
        for stage in ("packet", "fusion", "argument", "route", "graph", "lens", "safe_sentence", "report_block", "output_contract", "assembly"):
            record = chain.get(stage) or {}
            status, decision = _status(record.get("status")), _status(record.get("decision"))
            if status in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"} or decision.startswith("BLOCK"):
                reasons = record.get("hard_block_hits") or record.get("blocked_reasons") or record.get("review_reasons") or []
                reason = str(reasons[0]) if isinstance(reasons, list) and reasons else (decision or status)
                return stage, reason
    return None, None


def _safe_external_call(runner: Callable[..., dict[str, Any]], args: tuple[Any, ...], stage: str) -> dict[str, Any]:
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


def _p02_finding_safe_sentence_candidate(finding: dict[str, Any]) -> dict[str, Any] | None:
    if str(finding.get("finding_admission_decision") or "") != "EMIT_CANDIDATE":
        return None
    finding_id = str(finding.get("finding_target_candidate_id") or "").strip()
    if not finding_id:
        return None
    resolved = int(finding.get("resolved_target_state_denominator") or 0)
    observed = int(finding.get("target_observed_visible_count") or 0)
    not_observed = int(finding.get("target_not_observed_complete_path_count") or 0)
    unresolved = int(finding.get("target_state_unresolved_count") or 0)
    focus = str(finding.get("finding_focus") or "")
    if focus == "TARGET_VARIATION_VISIBLE":
        sentence = (
            f"Aynı exact takım, periyot, skor-durumu ve başlangıç-bölgesi bağlamındaki çözümlenmiş "
            f"{resolved} süreç biriminin {observed} tanesinde ilan edilen advanced-access hedefi görünürken "
            f"{not_observed} complete admitted path içinde hedef görünmedi; unresolved={unresolved}. "
            "Bu yalnız match-local hedef-varyasyonu bulgusudur; genel hücum başarısı, taktik kalite veya nedensellik değildir."
        )
    elif focus == "TARGET_OBSERVED_ONLY_IN_RESOLVED_POPULATION":
        sentence = (
            f"Aynı exact takım, periyot, skor-durumu ve başlangıç-bölgesi bağlamındaki çözümlenmiş "
            f"{resolved} süreç biriminin tamamında ilan edilen advanced-access hedefi görünür; unresolved={unresolved}. "
            "Bu yalnız bu match-local resolved population için görünürlük bulgusudur; genel hücum başarısı, "
            "taktik kalite, bağlam dışı istikrar veya nedensellik değildir."
        )
    elif focus == "TARGET_NOT_OBSERVED_ONLY_IN_RESOLVED_POPULATION":
        sentence = (
            f"Aynı exact takım, periyot, skor-durumu ve başlangıç-bölgesi bağlamındaki çözümlenmiş "
            f"{resolved} süreç biriminin hiçbir complete admitted semantic-zone path örneğinde ilan edilen "
            f"advanced-access hedefi görünmedi; unresolved={unresolved}. Bu yalnız bu match-local resolved population "
            "için görünürlük bulgusudur; genel hücum başarısızlığı, taktik zayıflık veya nedensellik değildir."
        )
    else:
        return None
    return {
        "module_id": "p02_professional_finding_safe_sentence_adapter_v1",
        "safe_sentence_id": f"safe_sentence_{finding_id}",
        "finding_target_candidate_id": finding_id,
        "safe_sentence_candidate_tr": sentence,
        "sentence_candidate_tr": sentence,
        "sentence_language": "tr",
        "claim_ceiling": "safe_sentence_candidate_only",
        "status": "SMOKE_PASS",
        "decision": "READY_FOR_REPORT_COMPOSER_CANDIDATE",
        "review_required": False,
        "review_reasons": [],
        "hard_block_hits": [],
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "safe_sentence_allowed": True,
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
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _run_p02_professional_finding_report_contracts(rich_report: dict[str, Any]) -> dict[str, Any]:
    p02 = rich_report.get("progression_pool_p02") or {}
    findings = p02.get("professional_finding_target_candidates") or []
    items: list[dict[str, Any]] = []
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict):
            continue
        safe = _p02_finding_safe_sentence_candidate(finding)
        if safe is None:
            continue
        block = compose_report_block(safe)
        contract = evaluate_report_block(block)
        assembly = evaluate_assembly_item(contract)
        items.append({
            "finding_target_candidate_id": finding.get("finding_target_candidate_id"),
            "safe_sentence": safe,
            "report_block": block,
            "output_contract": contract,
            "assembly": assembly,
        })
    blocked = sum(
        1 for row in items
        if str((row.get("assembly") or {}).get("status") or "") == "FAIL_CLOSED"
    )
    review = sum(
        1 for row in items
        if str((row.get("assembly") or {}).get("status") or "") == "REVIEW_REQUIRED"
    )
    ready = sum(
        1 for row in items
        if str((row.get("assembly") or {}).get("status") or "") == "SMOKE_PASS"
        and str((row.get("assembly") or {}).get("assembly_decision") or "") == "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE"
    )
    status = "FAIL_CLOSED" if blocked else "REVIEW_REQUIRED" if review else "SMOKE_PASS"
    return {
        "module_id": "p02_professional_finding_report_contract_adapter_v1",
        "status": status,
        "finding_contract_item_count": len(items),
        "ready_draft_report_candidate_count": ready,
        "review_count": review,
        "blocked_count": blocked,
        "items": items,
        "claim_output_allowed": False,
        "draft_report_candidate_allowed": bool(ready and not blocked and not review),
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _write_fused_packet_inventory(
    output_root: Path,
    packets: list[dict[str, Any]],
    base_count: int,
    rich_count: int,
    *,
    auxiliary_counterevidence_packets: list[dict[str, Any]] | None = None,
    auxiliary_counterevidence_fusions: list[dict[str, Any]] | None = None,
) -> list[str]:
    json_path = output_root / FUSED_PACKET_JSON
    txt_path = output_root / FUSED_PACKET_TXT
    auxiliary_counterevidence_packets = auxiliary_counterevidence_packets or []
    auxiliary_counterevidence_fusions = auxiliary_counterevidence_fusions or []
    payload = {
        "module_id": "active_match_fused_packet_inventory_v1",
        "status": "SMOKE_PASS",
        "base_reconstruction_packet_count": base_count,
        "rich_construct_packet_count": rich_count,
        "auxiliary_counterevidence_packet_count": len(auxiliary_counterevidence_packets),
        "auxiliary_counterevidence_fusion_count": len(auxiliary_counterevidence_fusions),
        "fused_packet_count": len(packets),
        "packets": packets,
        "auxiliary_counterevidence_packets": auxiliary_counterevidence_packets,
        "auxiliary_counterevidence_fusions": auxiliary_counterevidence_fusions,
        "format_fusion_is_independent_evidence_vote": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA ACTIVE_MATCH FUSED PACKET INVENTORY V1",
        f"base_reconstruction_packet_count={base_count}",
        f"rich_construct_packet_count={rich_count}",
        f"auxiliary_counterevidence_packet_count={len(auxiliary_counterevidence_packets)}",
        f"auxiliary_counterevidence_fusion_count={len(auxiliary_counterevidence_fusions)}",
        f"fused_packet_count={len(packets)}",
        "format_fusion_is_independent_evidence_vote=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    return [str(json_path), str(txt_path)]


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
    first_failed_node = None
    first_failed_reason_code = None

    bridge = bridge_runner or reconstruction_bridge.runtime_write_outputs
    bridge_report = _safe_external_call(bridge, (active_match_path, output_root), "reconstruction_bridge")
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

    rich_report: dict[str, Any] = {
        "status": "NOT_EVALUATED_PREREQUISITE_MISSING",
        "reason": "bridge_snapshot_id_missing",
        "current_invocation_artifacts": [],
    }
    sidecar_report: dict[str, Any] = {
        "status": "NOT_EVALUATED_PREREQUISITE_MISSING",
        "current_invocation_artifacts": [],
    }
    p02_professional_finding_report_contracts: dict[str, Any] = {
        "module_id": "p02_professional_finding_report_contract_adapter_v1",
        "status": "NOT_EVALUATED",
        "finding_contract_item_count": 0,
        "ready_draft_report_candidate_count": 0,
        "review_count": 0,
        "blocked_count": 0,
        "items": [],
        "claim_output_allowed": False,
        "draft_report_candidate_allowed": False,
        "final_report_allowed": False,
        "production_report_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    expected_snapshot_id = str(bridge_report.get("input_surface_snapshot_id") or "")
    if not hard_blocks and expected_snapshot_id:
        try:
            rich_report = run_rich_lane(
                active_match_path,
                output_root,
                expected_snapshot_id=expected_snapshot_id,
                match_surface_binding_id=bridge_report.get("match_surface_binding_id"),
            )
        except Exception as exc:
            rich_report = {
                "status": "FAIL_CLOSED",
                "hard_block_hits": [f"rich_multiformat_lane_exception:{type(exc).__name__}"],
                "current_invocation_artifacts": [],
            }
        rich_status = _status(rich_report.get("status"))
        if rich_status == "FAIL_CLOSED":
            hard_blocks.append("rich_multiformat_analysis_lane_fail_closed")
            first_failed_node = first_failed_node or "rich_multiformat_analysis_lane"
            reasons = rich_report.get("hard_block_hits") or []
            first_failed_reason_code = first_failed_reason_code or (
                str(reasons[0]) if isinstance(reasons, list) and reasons else "rich_multiformat_analysis_lane_fail_closed"
            )
        elif rich_status == "REVIEW_REQUIRED":
            review_hits.append("rich_multiformat_analysis_lane_review_required")

        sidecar_report = run_sidecars(active_match_path, output_root, Path(__file__).resolve().parents[5])
        if _status(sidecar_report.get("status")) == "REVIEW_REQUIRED":
            review_hits.append("orphan_capability_sidecars_review_required")

        p02_professional_finding_report_contracts = _run_p02_professional_finding_report_contracts(rich_report)
        if _status(p02_professional_finding_report_contracts.get("status")) == "REVIEW_REQUIRED":
            review_hits.append("p02_professional_finding_report_contract_review_required")
        elif _status(p02_professional_finding_report_contracts.get("status")) == "FAIL_CLOSED":
            review_hits.append("p02_professional_finding_report_contract_blocked")

    packets: list[dict[str, Any]] = []
    base_packet_count = 0
    rich_packet_count = 0
    auxiliary_counterevidence_packets: list[dict[str, Any]] = []
    auxiliary_counterevidence_fusions: list[dict[str, Any]] = []
    fused_packet_artifacts: list[str] = []
    if not hard_blocks:
        try:
            packet_report = _load_json(output_root / PACKET_REPORT_JSON)
        except FullSpineContractError as exc:
            packet_report = {}
            hard_blocks.append(str(exc))
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or str(exc)
        base_packets = packet_report.get("packets") if isinstance(packet_report, dict) else []
        if not isinstance(base_packets, list) or not base_packets:
            hard_blocks.append("composite_packet_inventory_empty_or_invalid")
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or "composite_packet_inventory_empty_or_invalid"
            base_packets = []
        declared_packet_count = packet_report.get("packet_count") if isinstance(packet_report, dict) else None
        if isinstance(declared_packet_count, int) and declared_packet_count != len(base_packets):
            hard_blocks.append("composite_packet_count_mismatch")
            first_failed_node = first_failed_node or "composite_packet_inventory"
            first_failed_reason_code = first_failed_reason_code or "composite_packet_count_mismatch"
        packets = [packet for packet in base_packets if isinstance(packet, dict)]
        base_packet_count = len(packets)

        for candidate in rich_report.get("c4_packet_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            packet = build_composite_packet(candidate)
            if packet.get("hard_block_hits"):
                review_hits.append("rich_construct_packet_not_admitted")
                continue

            p02_role = str(candidate.get("p02_packet_role") or "")
            if p02_role == "POPULATION_COLLAPSED_COUNTEREVIDENCE_COMPARISON_PACKET_ONLY":
                auxiliary_counterevidence_packets.append(packet)
                fusion = fuse_packet(packet)
                auxiliary_counterevidence_fusions.append(fusion)
                if _status(fusion.get("status")) in {"REVIEW_REQUIRED", "FAIL_CLOSED"}:
                    review_hits.append("p02_auxiliary_counterevidence_review_required")
                continue

            packets.append(packet)
            rich_packet_count += 1

        if not hard_blocks:
            fused_packet_artifacts = _write_fused_packet_inventory(
                output_root,
                packets,
                base_packet_count,
                rich_packet_count,
                auxiliary_counterevidence_packets=auxiliary_counterevidence_packets,
                auxiliary_counterevidence_fusions=auxiliary_counterevidence_fusions,
            )
            for packet in packets:
                chains.append(run_intelligence_chain(packet))

    failed_chain_count = sum(_chain_has_fail(chain) for chain in chains)
    review_chain_count = sum(_chain_has_review(chain) for chain in chains)
    completed_chain_count = sum(_chain_completed(chain) for chain in chains)
    chain_node, chain_reason = _first_failure(chains)
    if first_failed_node is None and chain_node is not None:
        first_failed_node, first_failed_reason_code = chain_node, chain_reason
    if failed_chain_count:
        hard_blocks.append("intelligence_chain_fail_closed")
    if review_chain_count:
        review_hits.append("intelligence_chain_review_required")
    hard_blocks = _dedupe_preserve_order(hard_blocks)
    review_hits = _dedupe_preserve_order(review_hits)
    if hard_blocks:
        status, decision = "FAIL_CLOSED", "BLOCK_FULL_SPINE"
    elif review_hits:
        status, decision = "REVIEW_REQUIRED", "FULL_SPINE_COMPLETED_REVIEW_REQUIRED"
    else:
        status, decision = "SMOKE_PASS", "FULL_SPINE_EXECUTION_COMPLETED"

    episode_lane_invoked = _status(episode_report.get("status")) != "NOT_EVALUATED"
    feature_lane_executed = episode_report.get("context_episode_feature_lane_executed") is True
    feature_lane_completed = episode_report.get("context_episode_feature_lane_completed") is True
    shared_foundation_reused = episode_report.get("shared_foundation_reused") is True
    row_nucleus_recomputed = episode_report.get("row_nucleus_recomputed_by_episode_lane")
    temporal_lane_executed = episode_report.get("temporal_episode_signature_executed") is True
    c4_chain_executed = bool(chains)
    c4_surface_current = bool(chains) and failed_chain_count == 0 and completed_chain_count == len(chains)
    current_invocation_artifacts = _collect_current_artifacts(
        bridge_report,
        episode_report,
        rich_report,
        sidecar_report,
        extra=[
            *fused_packet_artifacts,
            str(output_root / OUTPUT_JSON),
            str(output_root / OUTPUT_TXT),
        ],
    )

    entity_views = rich_report.get("entity_views") or {}
    constructs = rich_report.get("constructs") or {}
    c01_construct = constructs.get("C01") or {}
    c01_bound_to_c4 = (
        str(c01_construct.get("c4_admission_status") or "").upper() == "ADMITTED"
        and str(c01_construct.get("status") or "").upper() in {"PASS", "SMOKE_PASS"}
    )
    p02_report = rich_report.get("progression_pool_p02") or {}
    p02_rich_packet_count = len(auxiliary_counterevidence_packets)
    p02_aux_counterevidence_count = sum(
        int(fusion.get("admitted_counterevidence_count") or 0)
        for fusion in auxiliary_counterevidence_fusions
    )
    p02_aux_dependency_challenge_count = sum(
        int(fusion.get("dependency_challenge_count") or 0)
        for fusion in auxiliary_counterevidence_fusions
    )
    p02_aux_non_support_count = sum(
        int(fusion.get("non_support_count") or 0)
        for fusion in auxiliary_counterevidence_fusions
    )
    p02_aux_unresolved_count = sum(
        int(fusion.get("unresolved_counterevidence_count") or 0)
        for fusion in auxiliary_counterevidence_fusions
    )
    _unused_p02_rich_packet_count = sum(
        1
        for candidate in (rich_report.get("c4_packet_candidates") or [])
        if isinstance(candidate, dict)
        and str(candidate.get("p02_packet_role") or "") == "POPULATION_COLLAPSED_COUNTEREVIDENCE_COMPARISON_PACKET_ONLY"
    )
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
        "rich_multiformat_analysis_lane_status": rich_report.get("status"),
        "xlsx_projected_row_count": rich_report.get("xlsx_projected_row_count"),
        "primitive_metric_count": len(rich_report.get("primitive_metrics") or []),
        "phase_state_candidate_count": len(rich_report.get("phase_state_candidates") or []),
        "player_view_candidate_count": len(entity_views.get("player_view_candidates") or []),
        "team_view_candidate_count": len(entity_views.get("team_view_candidates") or []),
        "goalkeeper_view_candidate_count": len(entity_views.get("goalkeeper_view_candidates") or []),
        "C01_status": c01_construct.get("status"),
        "C01_c4_admission_status": c01_construct.get("c4_admission_status"),
        "P02_c4_packet_candidate_count": p02_rich_packet_count,
        "P02_counterevidence_population_count": p02_report.get("p02_counterevidence_population_count"),
        "P02_auxiliary_counterevidence_packet_count": len(auxiliary_counterevidence_packets),
        "P02_auxiliary_counterevidence_fusion_count": len(auxiliary_counterevidence_fusions),
        "P02_admitted_counterevidence_count": p02_aux_counterevidence_count,
        "P02_dependency_challenge_count": p02_aux_dependency_challenge_count,
        "P02_non_support_count": p02_aux_non_support_count,
        "P02_unresolved_counterevidence_count": p02_aux_unresolved_count,
        "base_composite_packet_count": base_packet_count,
        "rich_construct_packet_count": rich_packet_count,
        "composite_packet_count": len(chains),
        "intelligence_chain_count": len(chains),
        "failed_intelligence_chain_count": failed_chain_count,
        "completed_intelligence_chain_count": completed_chain_count,
        "review_required_intelligence_chain_count": review_chain_count,
        "first_failed_node": first_failed_node,
        "first_failed_reason_code": first_failed_reason_code,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "episode_lane": episode_report,
        "rich_multiformat_analysis_lattice": rich_report,
        "orphan_capability_sidecars": sidecar_report,
        "p02_professional_finding_report_contracts": p02_professional_finding_report_contracts,
        "P02_professional_finding_report_contract_item_count": p02_professional_finding_report_contracts.get("finding_contract_item_count", 0),
        "P02_professional_finding_ready_draft_report_candidate_count": p02_professional_finding_report_contracts.get("ready_draft_report_candidate_count", 0),
        "intelligence_chains": chains,
        "current_invocation_artifacts": current_invocation_artifacts,
        "engineering_evidence": {
            "single_active_match_authority_validated": True,
            "reconstruction_bridge_executed": True,
            "episode_lane_executed": episode_lane_invoked,
            "shared_foundation_reused": shared_foundation_reused,
            "row_nucleus_recomputed_by_episode_lane": row_nucleus_recomputed,
            "current_context_episode_feature_lane_reused": feature_lane_completed,
            "current_context_episode_feature_lane_executed": feature_lane_executed,
            "current_temporal_episode_signature_reused": temporal_lane_executed,
            "current_reconstruction_bridge_reused": True,
            "rich_multiformat_lane_executed": expected_snapshot_id != "" and _status(rich_report.get("status")) != "NOT_EVALUATED_PREREQUISITE_MISSING",
            "xlsx_row_projection_bound": rich_report.get("xlsx_projected_row_count") is not None,
            "micro_mezzo_macro_lattice_bound": bool(rich_report.get("analysis_lattice")),
            "phase_state_candidate_lane_bound": bool(rich_report.get("phase_state_candidates")),
            "entity_views_bound": bool(entity_views),
            "construct_C01_bound_to_c4": c01_bound_to_c4,
            "P02_counterevidence_packets_bound_to_c4": p02_rich_packet_count > 0,
            "P02_counterevidence_packets_are_auxiliary_fusion_only": True,
            "P02_counterevidence_packets_enter_argument_route": False,
            "current_c4_producers_executed": c4_chain_executed,
            "current_c4_producers_reused": c4_surface_current,
            "c4_stage_exception_containment_enabled": True,
            "c4_sidecar_dependency_preserved": True,
            "parallel_reasoning_engine_created": False,
            "p02_professional_finding_report_contract_reuses_existing_composer_output_assembly": True,
            "first_failure_disclosure_enabled": True,
            "duplicate_foundation_execution_currently_possible": False,
        },
        "analyst_evidence": {
            "episode_candidate_count": episode_report.get("episode_candidate_count"),
            "episode_feature_vector_count": episode_report.get("episode_feature_vector_count"),
            "temporal_episode_signature_count": episode_report.get("temporal_episode_signature_count"),
            "xlsx_projected_row_count": rich_report.get("xlsx_projected_row_count"),
            "primitive_metric_count": len(rich_report.get("primitive_metrics") or []),
            "phase_state_candidate_count": len(rich_report.get("phase_state_candidates") or []),
            "packet_level_report_candidates_generated": len(chains),
            "counterevidence_preserved_by_current_c4_chain": c4_surface_current,
            "P02_auxiliary_counterevidence_preserved": p02_aux_counterevidence_count > 0,
            "P02_auxiliary_counterevidence_safe_finding_emitted": False,
            "absence_is_counterevidence": False,
            "safe_report_language_only": c4_surface_current,
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
    (output_root / OUTPUT_TXT).write_text("\n".join([
        "HPFA ACTIVE_MATCH FULL SPINE V1",
        "===============================",
        f"status={status}",
        f"decision={decision}",
        f"episode_lane_status={episode_report.get('status')}",
        f"episode_candidate_count={episode_report.get('episode_candidate_count')}",
        f"episode_feature_vector_count={episode_report.get('episode_feature_vector_count')}",
        f"temporal_episode_signature_count={episode_report.get('temporal_episode_signature_count')}",
        f"rich_multiformat_analysis_lane_status={rich_report.get('status')}",
        f"xlsx_projected_row_count={rich_report.get('xlsx_projected_row_count')}",
        f"primitive_metric_count={len(rich_report.get('primitive_metrics') or [])}",
        f"phase_state_candidate_count={len(rich_report.get('phase_state_candidates') or [])}",
        f"player_view_candidate_count={len(entity_views.get('player_view_candidates') or [])}",
        f"team_view_candidate_count={len(entity_views.get('team_view_candidates') or [])}",
        f"goalkeeper_view_candidate_count={len(entity_views.get('goalkeeper_view_candidates') or [])}",
        f"C01_status={c01_construct.get('status')}",
        f"C01_c4_admission_status={c01_construct.get('c4_admission_status')}",
        f"P02_c4_packet_candidate_count={p02_rich_packet_count}",
        f"P02_auxiliary_counterevidence_packet_count={len(auxiliary_counterevidence_packets)}",
        f"P02_admitted_counterevidence_count={p02_aux_counterevidence_count}",
        f"base_composite_packet_count={base_packet_count}",
        f"rich_construct_packet_count={rich_packet_count}",
        f"intelligence_chain_count={len(chains)}",
        f"completed_intelligence_chain_count={completed_chain_count}",
        f"first_failed_node={first_failed_node}",
        f"first_failed_reason_code={first_failed_reason_code}",
        f"hard_block_hits={hard_blocks}",
        f"review_hits={review_hits}",
        f"shared_foundation_reused={str(shared_foundation_reused).lower()}",
        f"row_nucleus_recomputed_by_episode_lane={row_nucleus_recomputed}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "possession_truth=false",
        "sequence_truth=false",
        "rhythm_truth=false",
        "tactical_truth=false",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    return report
