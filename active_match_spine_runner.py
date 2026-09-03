#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import full_spine_runner as full_spine_module
import rich_multiformat_analysis_lane as rich_lane_module
import reciprocal_process_chain_current_v1 as reciprocal_current
from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import bridge_reciprocal_packets
from shared_surface_snapshot_contract import surface_snapshot_id
from spine_runner import run_spine_check
from user_output_bundle import snapshot_output_state, write_standard_user_outputs

RICH_OWNED_OUTPUTS = {
    "rich_multiformat_analysis_lattice_v1.json",
    "rich_multiformat_analysis_lattice_v1.txt",
    "xlsx_surface_audit_lite_v1.json",
    "xlsx_surface_audit_lite_v1.txt",
    "xlsx_surface_analyst_audit_lite_v1.txt",
    "xlsx_entity_metric_row_projection_lite_v1.json",
    "xlsx_entity_metric_row_projection_lite_v1.txt",
}


def _bind_shared_snapshot_contract() -> None:
    rich_lane_module._snapshot = surface_snapshot_id


def _clear_rich_owned_outputs(out_dir: str | Path) -> list[str]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    cleared: list[str] = []
    for name in sorted(RICH_OWNED_OUTPUTS):
        path = output / name
        if not path.is_file():
            continue
        path.unlink()
        cleared.append(name)
    return cleared


def _apply_construct_admission_gate(report: dict) -> dict:
    """Keep review-only constructs visible without promoting them into C4."""
    if not isinstance(report, dict):
        return report
    constructs = report.get("constructs")
    c01 = constructs.get("C01") if isinstance(constructs, dict) else None
    if not isinstance(c01, dict):
        return report

    explicit_admission = str(c01.get("c4_admission_status") or "").upper()
    construct_status = str(c01.get("status") or "").upper()
    admitted = explicit_admission == "ADMITTED" and construct_status in {"PASS", "SMOKE_PASS"}
    if admitted:
        return report

    withheld = len(report.get("c4_packet_candidates") or [])
    report["c4_packet_candidates"] = []
    report["construct_c4_promotion_withheld_count"] = withheld
    report["construct_c4_promotion_state"] = "WITHHELD_PENDING_CONSTRUCT_ADMISSION"
    c01["c4_admission_status"] = "WITHHELD_PENDING_CONSTRUCT_ADMISSION"
    c01["c4_admission_reason"] = c01.get("review_reason") or "explicit_construct_admission_not_available"
    c01["construct_truth"] = False

    outputs = report.get("outputs") or {}
    lattice_json = Path(str(outputs.get("lattice_json") or ""))
    lattice_txt = Path(str(outputs.get("lattice_txt") or ""))
    if lattice_json.is_file():
        lattice_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if lattice_txt.is_file():
        text = lattice_txt.read_text(encoding="utf-8")
        marker = "C01_c4_admission_status=WITHHELD_PENDING_CONSTRUCT_ADMISSION"
        if marker not in text:
            lattice_txt.write_text(text.rstrip() + "\n" + marker + "\n", encoding="utf-8")
    return report


def _bind_construct_admission_gate() -> None:
    if getattr(full_spine_module, "_hpfa_construct_admission_gate_bound", False):
        return
    original = full_spine_module.run_rich_lane

    def gated_run_rich_lane(*args, **kwargs):
        out_dir = kwargs.get("out_dir")
        if out_dir is None and len(args) >= 2:
            out_dir = args[1]
        cleared = _clear_rich_owned_outputs(out_dir) if out_dir is not None else []
        report = _apply_construct_admission_gate(original(*args, **kwargs))
        report["cleared_stale_rich_owned_outputs"] = cleared
        return report

    full_spine_module.run_rich_lane = gated_run_rich_lane
    full_spine_module._hpfa_construct_admission_gate_bound = True


def _bind_metric_governance_construct_gate() -> None:
    """A metric-governance FAIL_CLOSED may not be converted into C4 construct support."""
    if getattr(full_spine_module, "_hpfa_metric_governance_gate_bound", False):
        return
    original_sidecars = full_spine_module.run_sidecars
    original_packet_builder = full_spine_module.build_composite_packet
    state = {"construct_blocked": False, "reason": None}

    def gated_sidecars(*args, **kwargs):
        state["construct_blocked"] = False
        state["reason"] = None
        report = original_sidecars(*args, **kwargs)
        governance = report.get("metric_governance_bridge") if isinstance(report, dict) else None
        governance = governance if isinstance(governance, dict) else {}
        if str(governance.get("status") or "").upper() == "FAIL_CLOSED":
            state["construct_blocked"] = True
            reasons = governance.get("hard_block_hits") or []
            state["reason"] = str(reasons[0]) if reasons else "metric_governance_fail_closed"
            report["construct_path_blocked"] = True
            report["construct_path_block_reason"] = state["reason"]
        return report

    def gated_packet_builder(candidate):
        if state["construct_blocked"]:
            return {
                "status": "FAIL_CLOSED",
                "hard_block_hits": [f"metric_governance_blocks_construct_promotion:{state['reason']}"],
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        return original_packet_builder(candidate)

    full_spine_module.run_sidecars = gated_sidecars
    full_spine_module.build_composite_packet = gated_packet_builder
    full_spine_module._hpfa_metric_governance_gate_bound = True


def _bind_claim_safety_stage_passthrough() -> None:
    """Carry an existing claim-safety envelope into every current C4 producer input/output.

    This does not create or reinterpret evidence. It prevents downstream stages from
    forgetting upstream uncertainty, pending falsifiers, or withdrawal conditions.
    """
    if getattr(full_spine_module, "_hpfa_claim_safety_stage_passthrough_bound", False):
        return

    stage_producer_names = (
        "fuse_packet",
        "build_argument_candidate",
        "route_argument",
        "build_evidence_graph",
        "build_lens_matrix",
        "route_safe_sentence",
        "compose_report_block",
        "evaluate_report_block",
        "evaluate_assembly_item",
    )

    def wrap(producer):
        def preserving(payload):
            result = producer(payload)
            if not isinstance(result, dict) or not isinstance(payload, dict):
                return result
            metadata = payload.get("claim_safety_metadata")
            if isinstance(metadata, dict):
                result["claim_safety_metadata"] = json.loads(
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True)
                )
            return result

        return preserving

    for producer_name in stage_producer_names:
        producer = getattr(full_spine_module, producer_name, None)
        if callable(producer):
            setattr(full_spine_module, producer_name, wrap(producer))

    full_spine_module._hpfa_claim_safety_stage_passthrough_bound = True


def _normalize_current_surface_evidence(result: dict) -> None:
    engineering = result.get("engineering_evidence")
    if not isinstance(engineering, dict):
        return
    if "current_context_episode_feature_lane_completed" not in engineering:
        engineering["current_context_episode_feature_lane_completed"] = (
            engineering.get("current_context_episode_feature_lane_reused") is True
        )


def _merge_current_invocation_artifacts(
    result: dict,
    bridge: dict,
    out_dir: str | Path,
) -> None:
    """Lift producer-declared bridge artifacts into the canonical full-spine ledger.

    The standard bundle reads only the top-level current_invocation_artifacts ledger.
    A nested bridge ledger therefore must be explicitly projected upward or valid
    current-run outputs can be silently omitted from the official bundle.
    """
    output_root = Path(out_dir).expanduser().resolve(strict=False)
    existing = result.get("current_invocation_artifacts")
    bridge_values = bridge.get("current_invocation_artifacts") if isinstance(bridge, dict) else None
    values = [
        *(existing if isinstance(existing, list) else []),
        *(bridge_values if isinstance(bridge_values, list) else []),
    ]

    merged: list[str] = []
    seen: set[str] = set()
    for raw in values:
        path = Path(str(raw)).expanduser().resolve(strict=False)
        if path.parent != output_root or not path.is_file():
            continue
        text = str(path)
        if text in seen:
            continue
        seen.add(text)
        merged.append(text)

    result["current_invocation_artifacts"] = merged
    result["reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count"] = sum(
        1
        for raw in (bridge_values if isinstance(bridge_values, list) else [])
        if str(Path(str(raw)).expanduser().resolve(strict=False)) in seen
    )


def _attach_reciprocal_match_tomography_bridge(
    result: dict,
    *,
    active_match_dir: str | Path,
    out_dir: str | Path,
) -> dict:
    """Project reciprocal packet candidates through the existing C4 chain.

    The bridge is deliberately review-only. It does not alter the base full-spine
    status, does not create a parallel engine, and never converts CI/runtime
    execution into ACTIVE_MATCH evidence truth or production release.
    """
    try:
        bridge = bridge_reciprocal_packets(
            active_match_dir=active_match_dir,
            out_dir=out_dir,
            reciprocal_runner=reciprocal_current.runtime_write_outputs,
            packet_builder=full_spine_module.build_composite_packet,
            intelligence_runner=full_spine_module.run_intelligence_chain,
        )
    except Exception as exc:
        bridge = {
            "module_id": "reciprocal_full_spine_packet_bridge_v1",
            "status": "FAIL_CLOSED",
            "decision": "BLOCK_MATCH_TOMOGRAPHY_BRIDGE",
            "hard_block_hits": [f"reciprocal_full_spine_bridge_exception:{type(exc).__name__}"],
            "active_match_evidence_pass": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    result["reciprocal_match_tomography_bridge"] = bridge
    result["reciprocal_match_tomography_bridge_status"] = bridge.get("status")
    result["reciprocal_match_tomography_claim_output_allowed_count"] = bridge.get("claim_output_allowed_count", 0)
    _merge_current_invocation_artifacts(result, bridge, out_dir)
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["production_release"] = False
    return result


def _persist_augmented_full_spine_artifacts(result: dict, out_dir: str | Path) -> dict:
    """Persist post-run bridge augmentation into the canonical full-spine artifacts.

    `run_full_spine` writes its canonical JSON/TXT before this wrapper attaches the
    reciprocal Match Tomography bridge. Re-write those already-authoritative files
    after augmentation so bundle/report consumers cannot observe a stale pre-bridge
    snapshot. This is persistence only; it opens no claim or evidence state.
    """
    output_root = Path(out_dir).expanduser().resolve(strict=False)
    json_path = output_root / full_spine_module.OUTPUT_JSON
    txt_path = output_root / full_spine_module.OUTPUT_TXT
    if not json_path.is_file():
        result["reciprocal_match_tomography_artifact_persistence_status"] = "REVIEW_REQUIRED_CANONICAL_JSON_MISSING"
        result.setdefault("review_hits", []).append("canonical_full_spine_json_missing_after_bridge_augmentation")
        return result

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if txt_path.is_file():
        text = txt_path.read_text(encoding="utf-8").rstrip()
        markers = [
            f"reciprocal_match_tomography_bridge_status={result.get('reciprocal_match_tomography_bridge_status')}",
            f"reciprocal_match_tomography_claim_output_allowed_count={result.get('reciprocal_match_tomography_claim_output_allowed_count', 0)}",
            f"reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count={result.get('reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count', 0)}",
            "reciprocal_match_tomography_active_match_evidence_pass=false",
            "canonical_event_count=UNKNOWN",
            "true_action_count=UNKNOWN",
            "production_release=false",
        ]
        for marker in markers:
            if marker not in text:
                text += "\n" + marker
        txt_path.write_text(text + "\n", encoding="utf-8")

    result["reciprocal_match_tomography_artifact_persistence_status"] = "PERSISTED_IN_CANONICAL_FULL_SPINE_ARTIFACTS"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA ACTIVE_MATCH spine v1.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--composite-registry")
    parser.add_argument(
        "--full-spine",
        action="store_true",
        help=(
            "Run the current reconstruction-to-intelligence spine using existing product producers. "
            "This does not create a parallel runtime engine."
        ),
    )
    parser.add_argument(
        "--execution-root",
        help=(
            "Explicit selected runtime execution root. "
            "Defaults to the product checkout root when omitted; no runtime discovery is performed."
        ),
    )
    args = parser.parse_args()

    execution_root = Path(args.execution_root).expanduser().resolve(strict=False) if args.execution_root else ROOT
    user_outputs = None

    if args.full_spine:
        if args.composite_registry:
            parser.error("--composite-registry is not accepted with --full-spine")
        _bind_shared_snapshot_contract()
        _bind_construct_admission_gate()
        _bind_metric_governance_construct_gate()
        _bind_claim_safety_stage_passthrough()
        before_state = snapshot_output_state(args.out_dir)
        result = full_spine_module.run_full_spine(
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
            execution_root=execution_root,
        )
        _normalize_current_surface_evidence(result)
        result = _attach_reciprocal_match_tomography_bridge(
            result,
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
        )
        result = _persist_augmented_full_spine_artifacts(result, args.out_dir)
        user_outputs = write_standard_user_outputs(
            args.out_dir,
            result,
            before_state=before_state,
        )
        out_json = str(Path(args.out_dir) / "active_match_full_spine_v1.json")
        out_txt = str(Path(args.out_dir) / "active_match_full_spine_v1.txt")
        rc = 2 if result.get("status") == "FAIL_CLOSED" else 0
    else:
        result = run_spine_check(
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
            composite_registry=args.composite_registry,
            root=ROOT,
            execution_root=execution_root,
        )
        out_json = str(Path(args.out_dir) / "active_match_spine_check_v1.json")
        out_txt = str(Path(args.out_dir) / "active_match_spine_check_v1.txt")
        rc = 2 if result.get("status") == "FAIL_CLOSED" else 0

    print(json.dumps({
        "status": result.get("status"),
        "full_spine": bool(args.full_spine),
        "out_json": out_json,
        "out_txt": out_txt,
        "analyst_report": user_outputs.get("analyst_report") if user_outputs else None,
        "bundle_zip": user_outputs.get("bundle_zip") if user_outputs else None,
        "bundle_manifest": user_outputs.get("bundle_manifest") if user_outputs else None,
        "reciprocal_match_tomography_bridge_status": result.get("reciprocal_match_tomography_bridge_status"),
        "reciprocal_match_tomography_claim_output_allowed_count": result.get("reciprocal_match_tomography_claim_output_allowed_count"),
        "reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count": result.get("reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count"),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
