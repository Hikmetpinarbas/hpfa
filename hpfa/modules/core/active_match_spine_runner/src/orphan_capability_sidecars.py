from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.active_match_analyst_report_lite.src import report_lite
from hpfa.modules.core.triplex_source_alignment_adapter_lite.src import triplex_source_alignment_adapter as triplex
from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import run_metric_governance_bridge
from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
    write_outputs as write_occurrence_consequence_outputs,
)
from hpfa.modules.core.active_match_spine_runner.src.occurrence_state_transition_projection import (
    build_occurrence_state_transition_projection,
    write_outputs as write_occurrence_state_transition_outputs,
)
from hpfa.modules.core.spatial_transition_candidate_lite.src import spatial_transition_candidate as spatial_transition
from hpfa.modules.core.state_transition_dynamics_lite.src import state_transition_dynamics as state_transition
from hpfa.modules.core.analyst_episode_locator_lite.src import process_participation_projection as process_participation
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    build_analyst_output_claim_contract,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.supported_sequence_grammar_alignment_projection import (
    build_supported_sequence_grammar_alignment,
)

MODULE_ID = "active_match_orphan_capability_sidecars_v1"
TRACE_OUTPUT = "trackable_action_trace_candidates_lite_v1.json"
EVIDENCE_OUTPUT = "evidence_atom_inventory_lite_v1.json"
IDENTITY_OUTPUT = "match_local_identity_candidates_lite_v1.json"
EPISODE_OUTPUT = "analyst_episode_locator_lite_v1.json"
CONSEQUENCE_OUTPUT = "trackable_action_consequence_candidates_lite_v1.json"
SEQUENCE_OUTPUT = "visible_action_sequence_candidates_lite_v1.json"
GRAMMAR_ALIGNMENT_OUTPUT = "supported_sequence_grammar_alignment_projection_v1.json"
ANALYST_OUTPUT_CLAIM_CONTRACT_OUTPUT = "analyst_output_claim_contract_projection_v1.json"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json_input_not_object")
    return payload


def _write_projection(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def run_sidecars(active_match_dir: str | Path, out_dir: str | Path, product_root: str | Path) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    review_hits: list[str] = []
    hard_blocks: list[str] = []
    construct_path_blocked = False
    construct_path_block_reason: str | None = None

    try:
        baseline = report_lite.write_report(active_match_dir, output, root=product_root)
        baseline_status = baseline.get("status")
        engineering = baseline.get("engineering_evidence") or {}
        for key in ("out_json", "out_txt"):
            value = engineering.get(key)
            if value and Path(str(value)).is_file():
                artifacts.append(str(value))
    except Exception as exc:
        baseline = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
        baseline_status = "REVIEW_REQUIRED"
        review_hits.append(f"active_match_analyst_report_lite_sidecar_failed:{type(exc).__name__}")

    mapping_present = any((output / name).is_file() for name in triplex.MAPPING_FILES)
    if mapping_present:
        try:
            triplex_report = triplex.write_outputs(output, output, root=product_root)
            triplex_status = triplex_report.get("status")
            for value in (triplex_report.get("outputs") or {}).values():
                if value and Path(str(value)).is_file():
                    artifacts.append(str(value))
            if triplex_status != "PASS":
                review_hits.append("triplex_source_alignment_not_pass")
        except Exception as exc:
            triplex_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            triplex_status = "REVIEW_REQUIRED"
            review_hits.append(f"triplex_source_alignment_sidecar_failed:{type(exc).__name__}")
    else:
        triplex_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "source_mapping_contract_or_audit_not_currently_produced",
            "fusion_admissible": False,
        }
        triplex_status = triplex_report["status"]

    trace_path = output / TRACE_OUTPUT
    evidence_path = output / EVIDENCE_OUTPUT
    identity_path = output / IDENTITY_OUTPUT
    episode_path = output / EPISODE_OUTPUT
    consequence_path = output / CONSEQUENCE_OUTPUT
    sequence_path = output / SEQUENCE_OUTPUT

    occurrence_projection_prerequisite_present = trace_path.is_file() and consequence_path.is_file()
    if occurrence_projection_prerequisite_present:
        try:
            occurrence_projection_report = build_occurrence_consequence_projection(
                _load_json(trace_path),
                _load_json(consequence_path),
            )
            occurrence_projection_paths = write_occurrence_consequence_outputs(
                occurrence_projection_report,
                output,
            )
            for value in occurrence_projection_paths.values():
                if value.is_file():
                    artifacts.append(str(value))
            occurrence_projection_status = occurrence_projection_report.get("status")
            if occurrence_projection_status == "FAIL_CLOSED":
                reasons = occurrence_projection_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "occurrence_consequence_projection_fail_closed"
                hard_blocks.append(f"occurrence_consequence_construct_path_blocked:{reason}")
            elif occurrence_projection_status != "PASS":
                review_hits.append("occurrence_consequence_projection_review_required")
        except Exception as exc:
            occurrence_projection_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            occurrence_projection_status = "REVIEW_REQUIRED"
            review_hits.append(f"occurrence_consequence_projection_sidecar_failed:{type(exc).__name__}")
    else:
        occurrence_projection_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "trackable_action_trace_or_consequence_output_missing",
            "production_release": False,
        }
        occurrence_projection_status = occurrence_projection_report["status"]

    spatial_prerequisite_present = trace_path.is_file() and evidence_path.is_file()
    if spatial_prerequisite_present:
        try:
            spatial_report = spatial_transition.build_spatial_transition_candidates(
                _load_json(trace_path),
                _load_json(evidence_path),
                None,
            )
            spatial_paths = spatial_transition.write_outputs(spatial_report, output)
            for value in spatial_paths.values():
                if value.is_file():
                    artifacts.append(str(value))
            spatial_status = spatial_report.get("status")
            if spatial_status == "FAIL_CLOSED":
                reasons = spatial_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "spatial_transition_fail_closed"
                hard_blocks.append(f"spatial_transition_construct_path_blocked:{reason}")
            elif spatial_status != "PASS":
                review_hits.append("spatial_transition_candidate_review_required")
        except Exception as exc:
            spatial_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            spatial_status = "REVIEW_REQUIRED"
            review_hits.append(f"spatial_transition_sidecar_failed:{type(exc).__name__}")
    else:
        spatial_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "trackable_action_trace_or_evidence_atom_output_missing",
            "production_release": False,
        }
        spatial_status = spatial_report["status"]

    state_transition_prerequisite_present = spatial_prerequisite_present and consequence_path.is_file()
    if state_transition_prerequisite_present:
        try:
            state_transition_report = state_transition.build_state_transition_dynamics(
                spatial_report,
                _load_json(consequence_path),
            )
            state_transition_paths = state_transition.write_outputs(state_transition_report, output)
            for value in state_transition_paths.values():
                if value.is_file():
                    artifacts.append(str(value))
            state_transition_status = state_transition_report.get("status")
            if state_transition_status == "FAIL_CLOSED":
                reasons = state_transition_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "state_transition_dynamics_fail_closed"
                hard_blocks.append(f"state_transition_dynamics_construct_path_blocked:{reason}")
            elif state_transition_status != "PASS":
                review_hits.append("state_transition_dynamics_review_required")
        except Exception as exc:
            state_transition_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            state_transition_status = "REVIEW_REQUIRED"
            review_hits.append(f"state_transition_dynamics_sidecar_failed:{type(exc).__name__}")
    else:
        state_transition_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "spatial_or_consequence_output_missing",
            "production_release": False,
        }
        state_transition_status = state_transition_report["status"]

    occurrence_state_transition_prerequisite_present = (
        spatial_prerequisite_present
        and occurrence_projection_prerequisite_present
        and occurrence_projection_status != "FAIL_CLOSED"
    )
    if occurrence_state_transition_prerequisite_present:
        try:
            occurrence_state_transition_report = build_occurrence_state_transition_projection(
                spatial_report,
                occurrence_projection_report,
            )
            occurrence_state_transition_paths = write_occurrence_state_transition_outputs(
                occurrence_state_transition_report,
                output,
            )
            for value in occurrence_state_transition_paths.values():
                if value.is_file():
                    artifacts.append(str(value))
            occurrence_state_transition_status = occurrence_state_transition_report.get("status")
            if occurrence_state_transition_status == "FAIL_CLOSED":
                reasons = occurrence_state_transition_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "occurrence_state_transition_projection_fail_closed"
                hard_blocks.append(f"occurrence_state_transition_construct_path_blocked:{reason}")
            elif occurrence_state_transition_status != "PASS":
                review_hits.append("occurrence_state_transition_projection_review_required")
        except Exception as exc:
            occurrence_state_transition_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            occurrence_state_transition_status = "REVIEW_REQUIRED"
            review_hits.append(f"occurrence_state_transition_projection_sidecar_failed:{type(exc).__name__}")
    else:
        occurrence_state_transition_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "spatial_or_occurrence_consequence_projection_missing",
            "production_release": False,
        }
        occurrence_state_transition_status = occurrence_state_transition_report["status"]

    process_participation_prerequisite_present = (
        evidence_path.is_file() and identity_path.is_file() and episode_path.is_file()
    )
    if process_participation_prerequisite_present:
        try:
            process_participation_report = process_participation.build_process_participation_projection(
                _load_json(evidence_path),
                _load_json(identity_path),
                _load_json(episode_path),
                repo_root=product_root,
            )
            process_paths = process_participation.write_outputs(process_participation_report, output)
            for value in process_paths.values():
                if value.is_file():
                    artifacts.append(str(value))
            process_participation_status = process_participation_report.get("status")
            if process_participation_status == "FAIL_CLOSED":
                reasons = process_participation_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "process_participation_projection_fail_closed"
                hard_blocks.append(f"process_participation_construct_path_blocked:{reason}")
            elif process_participation_status != "PASS":
                review_hits.append("process_participation_projection_review_required")
        except Exception as exc:
            process_participation_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            process_participation_status = "REVIEW_REQUIRED"
            review_hits.append(f"process_participation_projection_sidecar_failed:{type(exc).__name__}")
    else:
        process_participation_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "evidence_identity_or_episode_output_missing",
            "production_release": False,
        }
        process_participation_status = process_participation_report["status"]

    sequence_intelligence_prerequisite_present = sequence_path.is_file()
    if sequence_intelligence_prerequisite_present:
        try:
            sequence_payload = _load_json(sequence_path)
            grammar_alignment_report = build_supported_sequence_grammar_alignment(sequence_payload)
            grammar_alignment_path = _write_projection(
                output / GRAMMAR_ALIGNMENT_OUTPUT,
                grammar_alignment_report,
            )
            artifacts.append(str(grammar_alignment_path))
            grammar_alignment_status = grammar_alignment_report.get("status")
            if grammar_alignment_status == "FAIL_CLOSED":
                reasons = grammar_alignment_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "grammar_alignment_fail_closed"
                hard_blocks.append(f"sequence_grammar_alignment_construct_path_blocked:{reason}")
            elif grammar_alignment_status != "PASS":
                review_hits.append("sequence_grammar_alignment_review_required")

            analyst_output_claim_contract_report = build_analyst_output_claim_contract(sequence_payload)
            analyst_output_claim_contract_path = _write_projection(
                output / ANALYST_OUTPUT_CLAIM_CONTRACT_OUTPUT,
                analyst_output_claim_contract_report,
            )
            artifacts.append(str(analyst_output_claim_contract_path))
            analyst_output_claim_contract_status = analyst_output_claim_contract_report.get("status")
            if analyst_output_claim_contract_status == "FAIL_CLOSED":
                reasons = analyst_output_claim_contract_report.get("hard_block_hits") or []
                reason = str(reasons[0]) if reasons else "analyst_output_claim_contract_fail_closed"
                hard_blocks.append(f"analyst_output_claim_contract_construct_path_blocked:{reason}")
            elif analyst_output_claim_contract_status != "PASS":
                review_hits.append("analyst_output_claim_contract_review_required")
        except Exception as exc:
            grammar_alignment_report = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
            grammar_alignment_status = "REVIEW_REQUIRED"
            analyst_output_claim_contract_report = {
                "status": "REVIEW_REQUIRED",
                "error_type": type(exc).__name__,
            }
            analyst_output_claim_contract_status = "REVIEW_REQUIRED"
            review_hits.append(f"sequence_intelligence_sidecar_failed:{type(exc).__name__}")
    else:
        grammar_alignment_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "visible_action_sequence_output_missing",
            "production_release": False,
        }
        grammar_alignment_status = grammar_alignment_report["status"]
        analyst_output_claim_contract_report = {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "reason": "visible_action_sequence_output_missing",
            "production_release": False,
        }
        analyst_output_claim_contract_status = analyst_output_claim_contract_report["status"]

    try:
        metric_governance = run_metric_governance_bridge(output, product_root)
        metric_governance_status = metric_governance.get("status")
        for value in metric_governance.get("current_invocation_artifacts") or []:
            if value and Path(str(value)).is_file():
                artifacts.append(str(value))
        normalized_governance_status = str(metric_governance_status or "").upper()
        if normalized_governance_status == "FAIL_CLOSED":
            reasons = metric_governance.get("hard_block_hits") or []
            construct_path_block_reason = str(reasons[0]) if reasons else "metric_governance_fail_closed"
            hard_blocks.append(f"metric_governance_construct_path_blocked:{construct_path_block_reason}")
            construct_path_blocked = True
        elif normalized_governance_status != "SMOKE_PASS":
            review_hits.append(f"metric_governance_bridge_{str(metric_governance_status).casefold()}")
    except Exception as exc:
        metric_governance = {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
        metric_governance_status = "REVIEW_REQUIRED"
        review_hits.append(f"metric_governance_bridge_sidecar_failed:{type(exc).__name__}")

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if hard_blocks or review_hits else "SMOKE_PASS",
        "active_match_analyst_report_lite_status": baseline_status,
        "triplex_source_alignment_status": triplex_status,
        "triplex_source_alignment_prerequisite_present": mapping_present,
        "occurrence_consequence_projection_status": occurrence_projection_status,
        "occurrence_consequence_projection_prerequisite_present": occurrence_projection_prerequisite_present,
        "spatial_transition_candidate_status": spatial_status,
        "spatial_transition_candidate_prerequisite_present": spatial_prerequisite_present,
        "state_transition_dynamics_status": state_transition_status,
        "state_transition_dynamics_prerequisite_present": state_transition_prerequisite_present,
        "occurrence_state_transition_projection_status": occurrence_state_transition_status,
        "occurrence_state_transition_projection_prerequisite_present": occurrence_state_transition_prerequisite_present,
        "process_participation_projection_status": process_participation_status,
        "process_participation_projection_prerequisite_present": process_participation_prerequisite_present,
        "sequence_grammar_alignment_status": grammar_alignment_status,
        "sequence_grammar_alignment_prerequisite_present": sequence_intelligence_prerequisite_present,
        "analyst_output_claim_contract_status": analyst_output_claim_contract_status,
        "analyst_output_claim_contract_prerequisite_present": sequence_intelligence_prerequisite_present,
        "metric_governance_bridge_status": metric_governance_status,
        "active_match_analyst_report_lite": baseline,
        "triplex_source_alignment": triplex_report,
        "occurrence_consequence_projection": occurrence_projection_report,
        "spatial_transition_candidate": spatial_report,
        "state_transition_dynamics": state_transition_report,
        "occurrence_state_transition_projection": occurrence_state_transition_report,
        "process_participation_projection": process_participation_report,
        "sequence_grammar_alignment": grammar_alignment_report,
        "analyst_output_claim_contract": analyst_output_claim_contract_report,
        "metric_governance_bridge": metric_governance,
        "construct_path_blocked": construct_path_blocked,
        "construct_path_block_reason": construct_path_block_reason,
        "hard_block_hits": _dedupe(hard_blocks),
        "review_hits": _dedupe(review_hits),
        "current_invocation_artifacts": sorted(set(artifacts)),
        "sidecar_outputs_are_primary_truth": False,
        "metric_value_output_allowed": False,
        "construct_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }
