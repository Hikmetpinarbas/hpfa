from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.observed_actor_acquisition_release_interval_projection import (
    build_observed_actor_acquisition_release_interval_projection,
)

TRACE_JSON = "trackable_action_trace_candidates_lite_v1.json"
SOURCE_RUN_JSON = "active_match_exact_head_run_v1.json"
OUTPUT_JSON = "observed_actor_acquisition_release_interval_projection_v1.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_input_not_object:{path.name}")
    return payload


def _git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def runtime_write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    expected_product_commit: str,
) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).resolve().parent
    product_commit = _git_head(repo_root)
    expected = str(expected_product_commit or "").strip()

    source_run_path = source / SOURCE_RUN_JSON
    source_run = _load(source_run_path) if source_run_path.is_file() else {}
    source_commit = str(source_run.get("product_code_commit") or "").strip() or None
    if source_commit is None:
        canonical_run = source_run.get("canonical_full_spine_run")
        if isinstance(canonical_run, dict):
            source_commit = str(canonical_run.get("product_commit") or "").strip() or None

    audit = {
        "projection_code_commit": product_commit,
        "expected_projection_code_commit": expected or None,
        "projection_code_commit_verified": bool(expected and product_commit == expected),
        "source_physical_run_product_commit": source_commit,
        "source_artifact_commit_matches_projection_commit": (
            source_commit == product_commit if source_commit and product_commit else None
        ),
        "source_artifact_commit_known": source_commit is not None,
        "physical_validation_mode": (
            "SAME_HEAD_PHYSICAL_ARTIFACT"
            if source_commit and product_commit and source_commit == product_commit
            else "PROJECTION_REPLAY_ON_PRIOR_PHYSICAL_ARTIFACTS"
            if source_commit
            else "SOURCE_ARTIFACT_COMMIT_UNKNOWN"
        ),
        "full_active_match_rerun_performed_by_this_runner": False,
    }

    trace_path = source / TRACE_JSON
    if not expected or product_commit != expected:
        report = {
            "status": "FAIL_CLOSED",
            "observed_actor_acquisition_release_interval_candidates": [],
            "observed_actor_acquisition_release_interval_candidate_count": 0,
            "hard_block_hits": ["projection_code_commit_mismatch_or_unavailable"],
            "review_hits": [],
            "projection_creates_new_evidence": False,
            "projection_reconstructs_sequences": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    elif not trace_path.is_file():
        report = {
            "status": "FAIL_CLOSED",
            "observed_actor_acquisition_release_interval_candidates": [],
            "observed_actor_acquisition_release_interval_candidate_count": 0,
            "hard_block_hits": [f"required_input_missing:{TRACE_JSON}"],
            "review_hits": [],
            "projection_creates_new_evidence": False,
            "projection_reconstructs_sequences": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        report = build_observed_actor_acquisition_release_interval_projection(_load(trace_path))

    report.update(audit)
    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expected-product-commit", required=True)
    args = parser.parse_args()
    report = runtime_write_outputs(
        args.input_dir,
        args.out_dir,
        args.expected_product_commit,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
