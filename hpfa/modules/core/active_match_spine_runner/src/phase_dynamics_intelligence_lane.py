from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.analyst_episode_locator_lite.src.phase_conditioned_interaction_projection import (
    build_phase_conditioned_interactions,
)
from hpfa.modules.core.analyst_episode_locator_lite.src.phase_dynamics_interaction_bridge import (
    build_phase_dynamics_interaction_bridge,
)
from hpfa.modules.core.temporal_episode_signature_lite.src.observed_match_dynamics_projection import (
    build_observed_match_dynamics,
)

MODULE_ID = "phase_dynamics_intelligence_lane_v1"
CLAIM_CEILING = "PHASE_DYNAMICS_INTERACTION_CANDIDATE_ONLY"

INPUTS = {
    "process": "analyst_episode_process_participation_projection_v1.json",
    "episode": "analyst_episode_locator_lite_v1.json",
    "rich": "rich_multiformat_analysis_lattice_v1.json",
    "feature": "episode_feature_vector_lite_v1.json",
    "temporal": "temporal_episode_signature_lite_v1.json",
}
OUTPUTS = {
    "interaction": "phase_conditioned_interaction_projection_v1.json",
    "dynamics": "observed_match_dynamics_projection_v1.json",
    "bridge": "phase_dynamics_interaction_bridge_v1.json",
}


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"phase_dynamics_input_unreadable:{path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"phase_dynamics_input_malformed:{path.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"phase_dynamics_input_not_object:{path.name}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def run_phase_dynamics_intelligence_lane(out_dir: str | Path) -> dict[str, Any]:
    output = validate_output_root(out_dir)
    missing = [name for name in INPUTS.values() if not (output / name).is_file()]
    if missing:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "PHASE_DYNAMICS_INPUTS_MISSING",
            "missing_inputs": sorted(missing),
            "hard_block_hits": [f"missing_input:{name}" for name in sorted(missing)],
            "review_hits": [],
            "phase_truth": False,
            "reciprocal_phase_truth": False,
            "tempo_truth": False,
            "momentum_truth": False,
            "control_truth": False,
            "causal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    payloads = {key: _load(output / filename) for key, filename in INPUTS.items()}
    interaction = build_phase_conditioned_interactions(
        payloads["process"], payloads["episode"], payloads["rich"]
    )
    dynamics = build_observed_match_dynamics(payloads["feature"], payloads["temporal"])
    bridge = build_phase_dynamics_interaction_bridge(interaction, dynamics)

    _write(output / OUTPUTS["interaction"], interaction)
    _write(output / OUTPUTS["dynamics"], dynamics)
    _write(output / OUTPUTS["bridge"], bridge)

    hard_blocks = []
    review_hits = []
    for name, payload in (("interaction", interaction), ("dynamics", dynamics), ("bridge", bridge)):
        if payload.get("status") == "FAIL_CLOSED":
            hard_blocks.append(f"{name}_fail_closed")
        if payload.get("status") == "REVIEW_REQUIRED":
            review_hits.append(f"{name}_review_required")

    if hard_blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_PHASE_DYNAMICS_INTELLIGENCE"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "PHASE_DYNAMICS_INTELLIGENCE_COMPLETED_REVIEW_REQUIRED"
    else:
        status = "SMOKE_PASS"
        decision = "PHASE_DYNAMICS_INTELLIGENCE_COMPLETED"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "interaction_episode_candidate_count": interaction.get("interaction_episode_candidate_count"),
        "observed_match_dynamics_candidate_count": dynamics.get("observed_match_dynamics_candidate_count"),
        "phase_dynamics_interaction_candidate_count": bridge.get("phase_dynamics_interaction_candidate_count"),
        "outputs": {key: str(output / filename) for key, filename in OUTPUTS.items()},
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "phase_truth": False,
        "reciprocal_phase_truth": False,
        "interaction_truth": False,
        "tempo_truth": False,
        "momentum_truth": False,
        "control_truth": False,
        "rhythm_truth": False,
        "phase_rupture_truth": False,
        "causal_truth": False,
        "tactical_plan_truth": False,
        "same_provider_support_is_independent_vote": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
