from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from hpfa.modules.core.temporal_episode_signature_lite.src.temporal_episode_signature import (
    write_outputs as write_temporal_episode_signature,
)


MODULE_ID = "active_match_episode_lane_adapter_v1"
CURRENT_EPISODE_RUNNER_OUTPUT = "active_match_full_run_lite_v1.json"
TEMPORAL_OUTPUT = "temporal_episode_signature_lite_v1.json"


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def run_current_episode_lane(
    active_match_dir: str | Path,
    out_dir: str | Path,
    execution_root: str | Path,
) -> dict[str, Any]:
    active_match = Path(active_match_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    root = Path(execution_root).expanduser().resolve(strict=False)
    current_runner = root / "active_match_full_run.py"

    if not current_runner.is_file():
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "BLOCK_EPISODE_LANE",
            "hard_block_hits": ["current_episode_runner_missing"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    completed = subprocess.run(
        [
            sys.executable,
            str(current_runner),
            "--match-dir",
            str(active_match),
            "--out-dir",
            str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    current_report = _load(output / CURRENT_EPISODE_RUNNER_OUTPUT)
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if completed.returncode != 0:
        hard_blocks.append("current_episode_runner_failed")
    if not current_report:
        hard_blocks.append("current_episode_runner_output_missing_or_invalid")
    elif current_report.get("status") == "FAIL_CLOSED":
        hard_blocks.append("current_episode_runner_fail_closed")

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

    if current_report.get("status") == "REVIEW_REQUIRED":
        review_hits.append("current_episode_lane_review_required")

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
        "current_episode_runner_status": current_report.get("status"),
        "current_episode_runner_returncode": completed.returncode,
        "temporal_episode_signature_status": temporal_report.get("status"),
        "episode_candidate_count": episode_evidence.get("episode_candidate_count"),
        "episode_feature_vector_count": episode_evidence.get("episode_feature_vector_count"),
        "action_occurrence_eligible_count": episode_evidence.get("action_occurrence_eligible_count"),
        "temporal_episode_signature_count": temporal_report.get("temporal_episode_signature_count"),
        "comparison_available_count": temporal_report.get("comparison_available_count"),
        "same_start_order_indeterminate_count": temporal_report.get("same_start_order_indeterminate_count"),
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "current_episode_runner_stdout": completed.stdout[-4000:],
        "current_episode_runner_stderr": completed.stderr[-4000:],
        "episode_output": str(output / CURRENT_EPISODE_RUNNER_OUTPUT),
        "temporal_output": str(output / TEMPORAL_OUTPUT),
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
