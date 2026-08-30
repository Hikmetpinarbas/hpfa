from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import active_match_full_run as current_episode
from hpfa.modules.core.temporal_episode_signature_lite.src.temporal_episode_signature import (
    write_outputs as write_temporal_episode_signature,
)

MODULE_ID = "active_match_episode_lane_adapter_v1"
CURRENT_EPISODE_RUNNER_OUTPUT = "active_match_full_run_lite_v1.json"
ROW_NUCLEUS_OUTPUT = "row_nucleus_inventory_lite_v1.json"
BRIDGE_OUTPUT = "reconstruction_intelligence_packet_bridge_current_v1.json"
TEMPORAL_OUTPUT = "temporal_episode_signature_lite_v1.json"
EPISODE_OWNED_OUTPUTS = {
    "minimum_viable_context_lite_v1.json",
    "minimum_viable_context_lite_v1.txt",
    "context_action_semantics_rebind_lite_v1.json",
    "context_action_semantics_rebind_lite_v1.txt",
    "context_action_semantics_rebind_analyst_audit_v1.txt",
    "analyst_episode_locator_lite_v1.json",
    "analyst_episode_locator_lite_v1.txt",
    "analyst_episode_locator_analyst_audit_v1.txt",
    "episode_feature_vector_lite_v1.json",
    "episode_feature_vector_lite_v1.txt",
    "episode_feature_vector_analyst_audit_v1.txt",
    "event_window_builder_lite_v1.json",
    "event_window_builder_lite_v1.txt",
    "time_scale_router_lite_v1.json",
    "time_scale_router_lite_v1.txt",
    "axis_integrity_tagger_lite_v1.json",
    "axis_integrity_tagger_lite_v1.txt",
    "temporal_episode_signature_lite_v1.json",
    "temporal_episode_signature_lite_v1.txt",
    "temporal_episode_signature_analyst_audit_v1.txt",
    "active_match_full_run_lite_v1.json",
    "active_match_full_run_lite_v1.txt",
}


def _product_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _surface_snapshot(match_dir: str | Path) -> dict[str, Any]:
    root = Path(match_dir).expanduser().resolve(strict=False)
    records: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if not path.is_file():
                continue
            records.append({
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            })
    stable_payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "snapshot_id": hashlib.sha256(stable_payload.encode("utf-8")).hexdigest(),
        "surface_file_count": len(records),
    }


def _clear_episode_owned_outputs(output: Path) -> list[str]:
    cleared: list[str] = []
    for name in sorted(EPISODE_OWNED_OUTPUTS):
        path = output / name
        if not path.is_file():
            continue
        path.unlink()
        cleared.append(name)
    return cleared


def _first_failed_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if step.get("passed") is not False:
            continue
        command = step.get("command") or []
        if isinstance(command, list) and command:
            if len(command) > 1 and str(command[0]).endswith(("python", "python3", "python.exe")):
                stage = Path(str(command[1])).name
            else:
                stage = Path(str(command[0])).name
        else:
            stage = "unknown_episode_step"
        return {
            "stage": stage,
            "returncode": step.get("returncode"),
            "stderr": str(step.get("stderr") or "")[-2000:],
        }
    return None


def _run_until_failure(
    steps: list[dict[str, Any]],
    producers: list[Callable[[], dict[str, Any]]],
) -> None:
    for producer in producers:
        step = producer()
        steps.append(step)
        if step.get("passed") is False:
            break


def _stage_executed(steps: list[dict[str, Any]], script_name: str) -> bool:
    for step in steps:
        command = step.get("command") or []
        if not isinstance(command, list):
            continue
        if any(Path(str(token)).name == script_name for token in command):
            return True
    return False


def _snapshot_bound_raw_step(
    active_match: Path,
    expected_snapshot_id: str,
    command_hint: list[str],
    producer: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    before = _surface_snapshot(active_match)
    if before.get("snapshot_id") != expected_snapshot_id:
        return {
            "command": command_hint,
            "returncode": 18,
            "stdout": "",
            "stderr": "active_match_surface_snapshot_mismatch_before_raw_read",
            "passed": False,
        }

    step = producer()
    after = _surface_snapshot(active_match)
    if after.get("snapshot_id") != expected_snapshot_id:
        return {
            **dict(step),
            "command": step.get("command") or command_hint,
            "returncode": 19,
            "stderr": "active_match_surface_snapshot_changed_during_raw_read",
            "passed": False,
        }
    return step


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
    bridge_path = output / BRIDGE_OUTPUT

    hard_blocks: list[str] = []
    review_hits: list[str] = []

    row_nucleus_available = row_nucleus_path.is_file()
    if not row_nucleus_available:
        hard_blocks.append("shared_row_nucleus_output_missing")

    bridge_report = current_episode.read_json(bridge_path)
    expected_snapshot_id = str(bridge_report.get("input_surface_snapshot_id") or "")
    if not expected_snapshot_id:
        hard_blocks.append("shared_input_surface_snapshot_id_missing")

    observed_snapshot = _surface_snapshot(active_match)
    surface_snapshot_bound = bool(expected_snapshot_id) and observed_snapshot.get("snapshot_id") == expected_snapshot_id
    if expected_snapshot_id and not surface_snapshot_bound:
        hard_blocks.append("active_match_surface_snapshot_mismatch_before_episode")

    surfaces = current_episode.readable_surface_files(active_match)
    input_status = {
        "match_dir": str(active_match),
        "surface_file_count": len(surfaces),
        "input_surface_ready": len(surfaces) > 0,
        "expected_surface_snapshot_id": expected_snapshot_id or None,
        "observed_surface_snapshot_id": observed_snapshot.get("snapshot_id"),
        "surface_snapshot_bound": surface_snapshot_bound,
        "shared_foundation_reused": row_nucleus_available and surface_snapshot_bound,
    }
    if not input_status["input_surface_ready"]:
        hard_blocks.append("active_match_surface_missing")

    shared_foundation_reused = row_nucleus_available and surface_snapshot_bound
    cleared_episode_outputs = _clear_episode_owned_outputs(output)

    steps: list[dict[str, Any]] = []
    if not hard_blocks:
        provider_command = ["internal:provider_time_semantic_admission_lite_v1"]
        event_window_command = [
            sys.executable,
            "event_window_builder.py",
            "--input-dir", str(output),
            "--raw-input-dir", str(active_match),
            "--out-dir", str(output),
        ]
        producers: list[Callable[[], dict[str, Any]]] = [
            lambda: _snapshot_bound_raw_step(
                active_match,
                expected_snapshot_id,
                provider_command,
                lambda: current_episode.run_provider_time_context_step(
                    product_root, active_match, output, row_nucleus_path
                ),
            ),
            lambda: current_episode.run_step(product_root, [
                sys.executable,
                "context_action_semantics_rebind.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            lambda: current_episode.run_step(product_root, [
                sys.executable,
                "analyst_episode_locator.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            lambda: current_episode.run_step(product_root, [
                sys.executable,
                "episode_feature_vector.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            lambda: _snapshot_bound_raw_step(
                active_match,
                expected_snapshot_id,
                event_window_command,
                lambda: current_episode.run_step(product_root, event_window_command),
            ),
            lambda: current_episode.run_step(product_root, [
                sys.executable,
                "time_scale_router.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
            lambda: current_episode.run_step(product_root, [
                sys.executable,
                "axis_integrity_tagger.py",
                "--input-dir", str(output),
                "--out-dir", str(output),
            ]),
        ]
        _run_until_failure(steps, producers)

    current_report: dict[str, Any] = {}
    first_failed_episode_step: dict[str, Any] | None = None
    if steps:
        current_report = current_episode.write_summary(output, steps, input_status)
        first_failed_episode_step = _first_failed_step(steps)
        if first_failed_episode_step:
            hard_blocks.append(
                "episode_step_failed:"
                f"{first_failed_episode_step['stage']}:"
                f"returncode_{first_failed_episode_step['returncode']}"
            )
        elif current_report.get("status") == "FAIL_CLOSED":
            hard_blocks.append("current_episode_lane_fail_closed")
        elif current_report.get("status") == "REVIEW_REQUIRED":
            review_hits.append("current_episode_lane_review_required")

    feature_lane_executed = all(
        _stage_executed(steps, script)
        for script in (
            "context_action_semantics_rebind.py",
            "analyst_episode_locator.py",
            "episode_feature_vector.py",
        )
    )
    feature_lane_completed = feature_lane_executed and not any(
        step.get("passed") is False
        for step in steps
        if any(
            Path(str(token)).name in {
                "context_action_semantics_rebind.py",
                "analyst_episode_locator.py",
                "episode_feature_vector.py",
            }
            for token in (step.get("command") or [])
        )
    )

    temporal_report: dict[str, Any] = {}
    first_failed_temporal_reason: str | None = None
    temporal_executed = False
    if not hard_blocks:
        final_snapshot = _surface_snapshot(active_match)
        if final_snapshot.get("snapshot_id") != expected_snapshot_id:
            hard_blocks.append("active_match_surface_snapshot_mismatch_before_temporal")
        else:
            temporal_executed = True
            try:
                temporal_report = write_temporal_episode_signature(output, output)
            except (OSError, ValueError, TypeError) as exc:
                first_failed_temporal_reason = f"temporal_episode_signature_execution_failed:{type(exc).__name__}"
                hard_blocks.append(first_failed_temporal_reason)
            if temporal_report.get("status") == "FAIL_CLOSED":
                temporal_blocks = temporal_report.get("hard_block_hits") or []
                if isinstance(temporal_blocks, list) and temporal_blocks:
                    first_failed_temporal_reason = str(temporal_blocks[0])
                    hard_blocks.append(first_failed_temporal_reason)
                else:
                    first_failed_temporal_reason = "temporal_episode_signature_fail_closed"
                    hard_blocks.append(first_failed_temporal_reason)
            elif temporal_report.get("status") == "REVIEW_REQUIRED":
                review_hits.append("temporal_episode_signature_review_required")

    final_observed_snapshot = _surface_snapshot(active_match)
    final_snapshot_bound = bool(expected_snapshot_id) and final_observed_snapshot.get("snapshot_id") == expected_snapshot_id
    if expected_snapshot_id and not final_snapshot_bound:
        hard_blocks.append("active_match_surface_snapshot_mismatch_after_temporal")

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
        "expected_surface_snapshot_id": expected_snapshot_id or None,
        "observed_surface_snapshot_id": final_observed_snapshot.get("snapshot_id"),
        "surface_snapshot_bound": final_snapshot_bound,
        "current_episode_runner_status": current_report.get("status"),
        "temporal_episode_signature_status": temporal_report.get("status"),
        "episode_candidate_count": episode_evidence.get("episode_candidate_count"),
        "episode_feature_vector_count": episode_evidence.get("episode_feature_vector_count"),
        "action_occurrence_eligible_count": episode_evidence.get("action_occurrence_eligible_count"),
        "temporal_episode_signature_count": temporal_report.get("temporal_episode_signature_count"),
        "comparison_available_count": temporal_report.get("comparison_available_count"),
        "same_start_order_indeterminate_count": temporal_report.get("same_start_order_indeterminate_count"),
        "first_failed_episode_step": first_failed_episode_step,
        "first_failed_temporal_reason": first_failed_temporal_reason,
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
        "shared_foundation_reused": shared_foundation_reused,
        "cleared_stale_episode_output_count": len(cleared_episode_outputs),
        "cleared_stale_episode_outputs": cleared_episode_outputs,
        "context_episode_feature_lane_executed": feature_lane_executed,
        "context_episode_feature_lane_completed": feature_lane_completed,
        "temporal_episode_signature_executed": temporal_executed,
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
