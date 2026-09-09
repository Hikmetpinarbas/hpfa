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


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run current ACTIVE_MATCH evidence spine through the existing process/story bridge"
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

    process = {
        "command": [],
        "returncode": 1,
        "passed": False,
        "stdout": "",
        "stderr": "base_active_match_full_run_failed",
    }
    story: dict[str, Any] = {
        "status": "REVIEW_REQUIRED",
        "decision": "PROCESS_STORY_NOT_EVALUATED_BASE_RUN_FAILED",
        "story_path_blocked": True,
        "entity_story_count": 0,
        "ready_assembly_item_count": 0,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }

    if base["passed"]:
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
        if process["passed"]:
            story = write_process_story_sidecar(out_dir)

    story_runtime_bound = (
        base["passed"]
        and process["passed"]
        and story.get("story_path_blocked") is False
    )

    payload = {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if base["passed"] else "FAIL_CLOSED",
        "decision": (
            "ACTIVE_MATCH_PROFESSIONAL_STORY_RUNTIME_EVALUATED"
            if base["passed"] and process["passed"]
            else "ACTIVE_MATCH_PROFESSIONAL_STORY_RUNTIME_INCOMPLETE"
        ),
        "base_active_match_run": base,
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

    if not base["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
