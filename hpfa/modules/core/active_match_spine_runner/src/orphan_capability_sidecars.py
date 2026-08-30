from __future__ import annotations

from pathlib import Path
from typing import Any

from hpfa.modules.core.active_match_analyst_report_lite.src import report_lite
from hpfa.modules.core.triplex_source_alignment_adapter_lite.src import triplex_source_alignment_adapter as triplex

MODULE_ID = "active_match_orphan_capability_sidecars_v1"


def run_sidecars(active_match_dir: str | Path, out_dir: str | Path, product_root: str | Path) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    review_hits: list[str] = []

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

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if review_hits else "SMOKE_PASS",
        "active_match_analyst_report_lite_status": baseline_status,
        "triplex_source_alignment_status": triplex_status,
        "triplex_source_alignment_prerequisite_present": mapping_present,
        "active_match_analyst_report_lite": baseline,
        "triplex_source_alignment": triplex_report,
        "review_hits": review_hits,
        "current_invocation_artifacts": sorted(set(artifacts)),
        "sidecar_outputs_are_primary_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }
