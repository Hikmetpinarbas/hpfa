from __future__ import annotations

from pathlib import Path
from typing import Any

from hpfa.modules.core.active_match_analyst_report_lite.src import report_lite
from hpfa.modules.core.triplex_source_alignment_adapter_lite.src import triplex_source_alignment_adapter as triplex
from hpfa.modules.core.active_match_spine_runner.src.metric_governance_bridge import run_metric_governance_bridge

MODULE_ID = "active_match_orphan_capability_sidecars_v1"


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
        # A governance hard block is scoped to the metric/construct path. The
        # unrelated baseline/triplex sidecars remain reviewable, so the sidecar
        # container itself stays REVIEW_REQUIRED rather than promoting that
        # scoped block to the whole ACTIVE_MATCH spine.
        "status": "REVIEW_REQUIRED" if hard_blocks or review_hits else "SMOKE_PASS",
        "active_match_analyst_report_lite_status": baseline_status,
        "triplex_source_alignment_status": triplex_status,
        "triplex_source_alignment_prerequisite_present": mapping_present,
        "metric_governance_bridge_status": metric_governance_status,
        "active_match_analyst_report_lite": baseline,
        "triplex_source_alignment": triplex_report,
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
