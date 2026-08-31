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
        # Per-invocation state: one failed run may not poison a later healthy run
        # in the same Python process.
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


def _normalize_current_surface_evidence(result: dict) -> None:
    engineering = result.get("engineering_evidence")
    if not isinstance(engineering, dict):
        return
    if "current_context_episode_feature_lane_completed" not in engineering:
        engineering["current_context_episode_feature_lane_completed"] = (
            engineering.get("current_context_episode_feature_lane_reused") is True
        )


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
        before_state = snapshot_output_state(args.out_dir)
        result = full_spine_module.run_full_spine(
            active_match_dir=args.active_match_dir,
            out_dir=args.out_dir,
            execution_root=execution_root,
        )
        _normalize_current_surface_evidence(result)
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
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
