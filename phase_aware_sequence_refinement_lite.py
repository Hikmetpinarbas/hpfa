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
    / "phase_aware_sequence_refinement_lite"
    / "src"
    / "phase_aware_sequence_refinement.py"
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


module = _load("hpfa_phase_aware_refinement_impl", IMPL)
overlay = _load("hpfa_micro_action_phase_overlay", OVERLAY)
_base_build_phase_aware_sequence_refinement = module.build_phase_aware_sequence_refinement
write_outputs = module.write_outputs
load_json = module.load_json


def build_phase_aware_sequence_refinement(phase_payload: dict):
    payload = _base_build_phase_aware_sequence_refinement(phase_payload)
    return overlay.apply_micro_action_phase_overlay(phase_payload, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-derived-phase", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    phase_payload = load_json(
        args.event_derived_phase,
        "event_derived_phase_input_unreadable_or_malformed",
    )
    payload = build_phase_aware_sequence_refinement(phase_payload)
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "phase_refinement_decision_count",
                    "A_B_A_phase_oscillation_count",
                    "refinement_candidate_count",
                    "micro_action_overlay_candidate_count",
                    "separate_phase_display_suppressed_count",
                    "insufficient_anchor_review_count",
                    "automatic_merge_count",
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
