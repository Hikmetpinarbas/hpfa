from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import active_match_full_run as current_episode
from hpfa.modules.core.temporal_episode_signature_lite.src.temporal_episode_signature import (
    write_outputs as write_temporal_episode_signature,
)

MODULE_ID = "active_match_episode_lane_adapter_v1"
CURRENT_EPISODE_RUNNER_OUTPUT = "active_match_full_run_lite_v1.json"
ROW_NUCLEUS_OUTPUT = "row_nucleus_inventory_lite_v1.json"
TEMPORAL_OUTPUT = "temporal_episode_signature_lite_v1.json"


def _product_root() -> Path:
    return Path(__file__).resolve().parents[5]


def run_current_episode_lane(
    active_match_dir: str | Path,
    out_dir: str | Path,
    execution_root: str | Path,
) -> dict[str, Any]:
    active_match = Path(active_match_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    selected_execution_root = Path(execution_root).expanduser().resolve(strict=False)
    product_root = _product_root()
    row_nucleus_path = output / ROW_NUCLEUS_OUTPUT

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    if not row_nucleus_path.is_file():
        hard_blocks.append("shared_row_nucleus_output_missing")

    surfaces = current_episode.readable_surface_files(active_match)
    input_status = {
        "match_dir": str(active_match),
        "surface_file_count": len(surfaces),
        "input_surface_ready": len(surfaces) > 0,
        "shared_foundation_reused": True,
    }
    if not input_status["input_surface_ready"]:
        hard_blocks.append("active_match_surface_missing")

    steps: list[dict[str, Any]] = []
    if not hard_blocks:
        steps = [
            current_episode.run_provider_time_context_step(product_root, active_match, output, row_nucleus_path),
            current_episode.run_step(product_root, [
                sys.executable,
                "context_action_semantics_rebind.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            current_episode.run_step(product_root, [
                sys.executable,
                "analyst_episode_locator.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            current_episode.run_step(product_root, [
                sys.executable,
                "episode_feature_vector.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            current_episode.run_step(product_root, [
                sys.executable,
                "event_window_builder.py",
                "--input-dir", str(output),
                "--raw-input-dir", str(active_match),
                "--out-dir", str(output),
            ]),
            current_episode.run_step(product_root, [
                sys.executable,
                "time_scale_router.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            current_episode.run_step(product_root, [
                sys.executable,
                "axis_integrity_tagger.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
        ]

    current_report: dict[str, Any] = {}
    if not hard_blocks:
        current_report = current_episode.write_summary(output, steps, input_status)
        if current_report.get("status") == "FAIL_CLOSED":
            hard_blocks.append("current_episode_lane_fail_closed")
        elif current_report.get("status") == "REVIEW_REQUIRED":
            review_hits.append("current_episode_lane_review_required")

    temporal_report: dict[str, Any] = {}
    if not hard_blocks:
        try:
            temporal_report = write_temporal_episode_signature(output, output)
        except (OSError, ValueError, TypeError) as exc:
            hard_blocks.append(f"temporal_episode_signature_execution_failed:{type(exc).__name__}")
        if temporal_report.get("status") == "FAIL_CLOSED":
            hard_blocks.append("temporal_episode_signature_fail_closed")
        elif temporal_report.get("status") == "REVIEW_REQUIRED":
            review_hits.append("temporal_episode_signature_review_required")

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    if hard_blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_EPISODE_LANE"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "EPISODE_LANE_COMPLETED_REVIEW_REQUIRED"
    else:
        status = "SMOKE_PASS"
        decision = "EPISODE_LANE_COMPLETED"

    episode_evidence = current_report.get("analyst_evidence") or {}
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "product_code_root": str(product_root),
        "selected_execution_root": str(selected_execution_root),
        "code_root_is_execution_root": product_root == selected_execution_root,
        "current_episode_runner_status": current_report.get("status"),
        "temporal_episode_signature_status": temporal_report.get("status"),
        "episode_candidate_count": episode_evidence.get("episode_candidate_count"),
        "episode_feature_vector_count": episode_evidence.get("episode_feature_vector_count"),
        "action_occurrence_eligible_count": episode_evidence.get("action_occurrence_eligible_count"),
        "temporal_episode_signature_count": temporal_report.get("temporal_episode_signature_count"),
        "comparison_available_count": temporal_report.get("comparison_available_count"),
        "same_start_order_indeterminate_count": temporal_report.get("same_start_order_indeterminate_count"),
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "step_statuses": [
            {
                "command": step.get("command"),
                "returncode": step.get("returncode"),
                "passed": step.get("passed"),
            }
            for step in steps
        ],
        "episode_output": str(output / CURRENT_EPISODE_RUNNER_OUTPUT),
        "temporal_output": str(output / TEMPORAL_OUTPUT),
        "shared_foundation_reused": True,
        "row_nucleus_recomputed_by_episode_lane": False,
        "episode_lane_adds_action_volume": False,
        "temporal_signature_is_rhythm_truth": False,
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }
