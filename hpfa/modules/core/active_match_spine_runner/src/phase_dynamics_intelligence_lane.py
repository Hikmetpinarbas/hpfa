from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.analyst_episode_locator_lite.src.episode_consequence_projection import (
    build_episode_consequence_projection,
)
from hpfa.modules.core.analyst_episode_locator_lite.src.phase_conditioned_interaction_projection import (
    build_phase_conditioned_interactions,
)
from hpfa.modules.core.analyst_episode_locator_lite.src.phase_dynamics_interaction_bridge import (
    build_phase_dynamics_interaction_bridge,
)
from hpfa.modules.core.metric_definition_policy_lite.src.ball_security_construct import (
    build_ball_security_construct,
)
from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import load_guard
from hpfa.modules.core.metric_definition_policy_lite.src.progression_effectiveness_construct import (
    build_progression_effectiveness_construct,
)
from hpfa.modules.core.metric_definition_policy_lite.src.progression_safe_finding_projection import (
    build_progression_safe_finding_projection,
)
from hpfa.modules.core.metric_definition_policy_lite.src.recovery_yield_construct import (
    build_recovery_yield_construct,
)
from hpfa.modules.core.temporal_episode_signature_lite.src.observed_match_dynamics_projection import (
    build_observed_match_dynamics,
)

MODULE_ID = "phase_dynamics_intelligence_lane_v1"
CLAIM_CEILING = "PHASE_DYNAMICS_INTERACTION_CONSEQUENCE_CONSTRUCT_FINDING_CANDIDATE_ONLY"

INPUTS = {
    "process": "analyst_episode_process_participation_projection_v1.json",
    "episode": "analyst_episode_locator_lite_v1.json",
    "rich": "rich_multiformat_analysis_lattice_v1.json",
    "feature": "episode_feature_vector_lite_v1.json",
    "temporal": "temporal_episode_signature_lite_v1.json",
    "trace": "trackable_action_trace_candidates_lite_v1.json",
    "consequence": "trackable_action_consequence_candidates_lite_v1.json",
}
OUTPUTS = {
    "interaction": "phase_conditioned_interaction_projection_v1.json",
    "dynamics": "observed_match_dynamics_projection_v1.json",
    "episode_consequence": "episode_consequence_projection_v1.json",
    "bridge": "phase_dynamics_interaction_bridge_v1.json",
    "progression_effectiveness": "progression_effectiveness_construct_v1.json",
    "progression_safe_finding": "progression_safe_finding_projection_v1.json",
    "ball_security": "ball_security_construct_v1.json",
    "recovery_yield": "recovery_yield_construct_v1.json",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


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


def _construct_fail_closed(module_id: str, error_prefix: str, exc: Exception, **locks: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "module_id": module_id,
        "status": "FAIL_CLOSED",
        "construct_candidate": None,
        "construct_candidate_count": 0,
        "hard_block_hits": [f"{error_prefix}:{type(exc).__name__}"],
        "review_hits": [],
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    payload.update(locks)
    return payload


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
            "interaction_truth": False,
            "tempo_truth": False,
            "momentum_truth": False,
            "control_truth": False,
            "causal_truth": False,
            "consequence_candidate_is_causal_truth": False,
            "progression_effectiveness_truth": False,
            "ball_security_truth": False,
            "loss_exposure_truth": False,
            "recovery_yield_truth": False,
            "possession_gain_truth": False,
            "progression_safe_finding_engineering_envelope_complete": False,
            "physical_active_match_evidence_present": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    payloads = {key: _load(output / filename) for key, filename in INPUTS.items()}
    interaction = build_phase_conditioned_interactions(payloads["process"], payloads["episode"], payloads["rich"])
    dynamics = build_observed_match_dynamics(payloads["feature"], payloads["temporal"])
    episode_consequence = build_episode_consequence_projection(payloads["episode"], payloads["trace"], payloads["consequence"], interaction)
    bridge = build_phase_dynamics_interaction_bridge(interaction, dynamics, episode_consequence)

    repo_root = _repo_root()
    try:
        guard = load_guard(repo_root / "configs/metrics/construct_context_guard_v1.json")
        progression_effectiveness = build_progression_effectiveness_construct(payloads["trace"], payloads["consequence"], guard, repo_root=repo_root)
        ball_security = build_ball_security_construct(payloads["trace"], payloads["consequence"], guard)
        recovery_yield = build_recovery_yield_construct(payloads["trace"], payloads["consequence"], guard)
    except (OSError, ValueError) as exc:
        progression_effectiveness = _construct_fail_closed(
            "progression_effectiveness_construct_v1", "progression_construct_authority_unavailable", exc,
            progression_effectiveness_truth=False,
        )
        ball_security = _construct_fail_closed(
            "ball_security_construct_v1", "ball_security_construct_authority_unavailable", exc,
            ball_security_truth=False, loss_exposure_truth=False,
        )
        recovery_yield = _construct_fail_closed(
            "recovery_yield_construct_v1", "recovery_yield_construct_authority_unavailable", exc,
            recovery_yield_truth=False, possession_gain_truth=False,
        )

    progression_safe_finding = build_progression_safe_finding_projection(progression_effectiveness)

    output_payloads = {
        "interaction": interaction,
        "dynamics": dynamics,
        "episode_consequence": episode_consequence,
        "bridge": bridge,
        "progression_effectiveness": progression_effectiveness,
        "progression_safe_finding": progression_safe_finding,
        "ball_security": ball_security,
        "recovery_yield": recovery_yield,
    }
    for key, payload in output_payloads.items():
        _write(output / OUTPUTS[key], payload)

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    for name, payload in output_payloads.items():
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
        "episode_consequence_candidate_count": episode_consequence.get("episode_consequence_candidate_count"),
        "bound_episode_consequence_candidate_count": episode_consequence.get("bound_episode_consequence_candidate_count"),
        "phase_dynamics_interaction_candidate_count": bridge.get("phase_dynamics_interaction_candidate_count"),
        "progression_effectiveness_construct_candidate_count": progression_effectiveness.get("construct_candidate_count"),
        "progression_safe_finding_candidate_count": progression_safe_finding.get("finding_candidate_count"),
        "progression_safe_finding_engineering_envelope_complete": progression_safe_finding.get("engineering_envelope_complete") is True,
        "ball_security_construct_candidate_count": ball_security.get("construct_candidate_count"),
        "recovery_yield_construct_candidate_count": recovery_yield.get("construct_candidate_count"),
        "physical_active_match_evidence_present": False,
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
        "consequence_candidate_is_causal_truth": False,
        "progression_effectiveness_truth": False,
        "ball_security_truth": False,
        "loss_exposure_truth": False,
        "recovery_yield_truth": False,
        "possession_gain_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "tactical_plan_truth": False,
        "same_provider_support_is_independent_vote": False,
        "event_only_is_product_ceiling": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
