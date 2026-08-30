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

import rich_multiformat_analysis_lane as rich_lane_module
from shared_surface_snapshot_contract import surface_snapshot_id
from spine_runner import run_spine_check
from full_spine_runner import run_full_spine
from user_output_bundle import snapshot_output_state, write_standard_user_outputs


def _bind_shared_snapshot_contract() -> None:
    # Reconstruction/Episode already use the canonical recursive path+size+SHA256
    # contract. The rich lane historically used a different serialization for the
    # same files, creating false mismatch failures. Bind it to the same contract
    # at the product entrypoint until all producers import the shared helper.
    rich_lane_module._snapshot = surface_snapshot_id


def _normalize_current_surface_evidence(result: dict) -> None:
    # Preserve one explicit semantic for the user report: completed current
    # Episode Feature production. Older full-spine records expose the same fact
    # as `..._reused`; do not make the report hide a successfully completed lane.
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
        before_state = snapshot_output_state(args.out_dir)
        result = run_full_spine(
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
