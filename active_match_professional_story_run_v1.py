from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from hpfa.modules.core.active_match_spine_runner.src.process_story_sidecar import (
    write_process_story_sidecar,
)

MODULE_ID = "active_match_professional_story_run_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
PIPELINE_STAGE_ORDER = (
    "base_active_match_run",
    "reconstruction_intelligence_packet_run",
    "reciprocal_process_run",
    "process_story_projection",
)


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _not_run(reason: str) -> dict[str, Any]:
    return {
        "command": [],
        "returncode": 1,
        "passed": False,
        "stdout": "",
        "stderr": reason,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run current ACTIVE_MATCH evidence spine through the existing reconstruction, process and story bridges"
    )
    parser.add_argument("--match-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    match_dir = Path(args.match_dir).expanduser().resolve(strict=False)
    out_dir = Path(args.out_dir).expanduser().resolve(strict=False)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = _run(
        [
            sys.executable,
            "active_match_full_run.py",
            "--match-dir",
            str(match_dir),
            "--out-dir",
            str(out_dir),
        ],
        repo_root,
    )

    reconstruction = _not_run("base_active_match_full_run_failed")
    process = _not_run("reconstruction_intelligence_packet_run_failed_or_not_evaluated")
    story: dict[str, Any] = {
        "status": "REVIEW_REQUIRED",
        "decision": "PROCESS_STORY_NOT_EVALUATED_UPSTREAM_INCOMPLETE",
        "story_path_blocked": True,
        "entity_story_count": 0,
        "ready_assembly_item_count": 0,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
    story_projection_evaluated = False

    if base["passed"]:
        reconstruction = _run(
            [
                sys.executable,
                "reconstruction_intelligence_packet_adapter_current_v1.py",
                "--input-dir",
                str(match_dir),
                "--out-dir",
                str(out_dir),
            ],
            repo_root,
        )

    if base["passed"] and reconstruction["passed"]:
        process = _run(
            [
                sys.executable,
                "reciprocal_process_chain_current_v1.py",
                "--input-dir",
                str(match_dir),
                "--out-dir",
                str(out_dir),
            ],
            repo_root,
        )

    if base["passed"] and reconstruction["passed"] and process["passed"]:
        story_projection_evaluated = True
        story = write_process_story_sidecar(out_dir)

    required_analysis_layers_activated = (
        base["passed"]
        and reconstruction["passed"]
        and process["passed"]
        and story_projection_evaluated
    )
    story_runtime_bound = (
        required_analysis_layers_activated
        and story.get("story_path_blocked") is False
    )

    payload = {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if required_analysis_layers_activated else "FAIL_CLOSED",
        "decision": (
            "ACTIVE_MATCH_FULL_POSTMATCH_PIPELINE_EVALUATED"
            if required_analysis_layers_activated
            else "ACTIVE_MATCH_FULL_POSTMATCH_PIPELINE_INCOMPLETE"
        ),
        "pipeline_stage_order": list(PIPELINE_STAGE_ORDER),
        "required_analysis_layers_activated": required_analysis_layers_activated,
        "story_projection_evaluated": story_projection_evaluated,
        "base_active_match_run": base,
        "reconstruction_intelligence_packet_run": reconstruction,
        "reciprocal_process_run": process,
        "process_story_status": story.get("status"),
        "process_story_decision": story.get("decision"),
        "process_story_runtime_bound": story_runtime_bound,
        "story_path_blocked": bool(story.get("story_path_blocked", True)),
        "story_path_block_reason": story.get("story_path_block_reason"),
        "entity_story_count": int(story.get("entity_story_count") or 0),
        "report_block_count": int(story.get("report_block_count") or 0),
        "ready_assembly_item_count": int(story.get("ready_assembly_item_count") or 0),
        "review_hits": list(story.get("review_hits") or []),
        "hard_block_hits": list(story.get("hard_block_hits") or []),
        "pipeline_is_possession_truth": False,
        "pipeline_is_tactical_plan_truth": False,
        "professional_story_is_tactical_plan_truth": False,
        "professional_story_is_coach_intention_truth": False,
        "professional_story_is_causality_truth": False,
        "professional_story_is_dominance_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }

    output_path = out_dir / "active_match_professional_story_run_v1.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))

    return 0 if required_analysis_layers_activated else 2


if __name__ == "__main__":
    raise SystemExit(main())
