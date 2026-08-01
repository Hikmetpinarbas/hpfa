from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPL = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "match_context_slicer_lite"
    / "src"
    / "match_context_slicer.py"
)
OVERLAY = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "phase_aware_sequence_refinement_lite"
    / "src"
    / "micro_action_phase_overlay.py"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{name}_unloadable")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


module = _load("hpfa_match_context_slicer_impl", IMPL)
overlay = _load("hpfa_micro_action_phase_overlay", OVERLAY)
_base_build_match_context_slicer = module.build_match_context_slicer
write_outputs = module.write_outputs
load_json = module.load_json


def build_match_context_slicer(
    action_payload: dict,
    phase_payload: dict,
    refinement_payload: dict,
):
    payload = _base_build_match_context_slicer(
        action_payload,
        phase_payload,
        refinement_payload,
    )
    return overlay.apply_effective_phase_to_context_slices(
        refinement_payload,
        payload,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--event-derived-phase", required=True)
    parser.add_argument("--phase-refinement", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_match_context_slicer(
        load_json(
            args.selected_action_consequence,
            "selected_action_input_unreadable_or_malformed",
        ),
        load_json(
            args.event_derived_phase,
            "event_derived_phase_input_unreadable_or_malformed",
        ),
        load_json(
            args.phase_refinement,
            "phase_refinement_input_unreadable_or_malformed",
        ),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "time_axis_candidate",
                    "goal_context_candidate_count",
                    "match_context_slice_count",
                    "micro_action_overlay_context_slice_count",
                    "separate_phase_display_suppressed_count",
                    "team_relative_score_state_candidate_counts",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
