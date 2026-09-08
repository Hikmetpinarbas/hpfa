from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "analyst_episode_process_participation_projection_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
EPISODE_MODULE_ID = "analyst_episode_locator_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "PROVIDER_ANNOTATED_PROCESS_PARTICIPATION_CANDIDATE_ONLY"
OUTPUTS = {
    "json": "analyst_episode_process_participation_projection_v1.json",
    "summary": "analyst_episode_process_participation_projection_v1.txt",
    "analyst": "analyst_episode_process_participation_analyst_audit_v1.txt",
}

PROCESS_ROLES = {"PARTICIPATION_INTERVAL", "CONTEXT_INTERVAL"}
BOUND_IDENTITY_STATES = {"ACTOR_IDENTITY_CANDIDATE_BOUND", "TEAM_IDENTITY_CANDIDATE_BOUND"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _provider_semantics(repo_root: Path):
    from hpfa.modules.core.provider_label_value_semantics_lite.src import provider_label_value_semantics as provider

    registry_path = (
        repo_root
        / "hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json"
    )
    return provider, provider.load_registry(registry_path)


def _binding_index(identity_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blocks: list[str] = []
    index: dict[str, dict[str, Any]] = {}
    rows = identity_payload.get("identity_bindings") or []
    if not isinstance(rows, list):
        return {}, ["identity_bindings_invalid"]
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"identity_binding_record_invalid:{position}")
            continue
        atom_id = _clean(row.get("evidence_atom_id"))
        if not atom_id or atom_id in index:
            blocks.append(f"identity_binding_atom_id_invalid_or_duplicate:{position}")
            continue
        index[atom_id] = row
    return index, blocks


def _episode_index(episode_payload: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    blocks: list[str] = []
    index: dict[str, str] = {}
    episodes = episode_payload.get("episode_candidates") or []
    if not isinstance(episodes, list):
        return {}, ["episode_candidates_invalid"]
    for position, episode in enumerate(episodes):
        if not isinstance(episode, dict):
            blocks.append(f"episode_record_invalid:{position}")
            continue
        episode_id = _clean(episode.get("episode_candidate_id"))
        if not episode_id:
            blocks.append(f"episode_id_missing:{position}")
            continue
        for nucleus_id in episode.get("row_nucleus_refs") or []:
            key = _clean(nucleus_id)
            if not key:
                continue
            if key in index and index[key] != episode_id:
                blocks.append(f"row_nucleus_multi_episode_assignment:{key}")
                continue
            index[key] = episode_id
    return index, blocks


def build_process_participation_projection(
    evidence_payload: dict[str, Any],
    identity_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    expected = {
        "evidence": (evidence_payload, EVIDENCE_MODULE_ID),
        "identity": (identity_payload, IDENTITY_MODULE_ID),
        "episode": (episode_payload, EPISODE_MODULE_ID),
    }
    for name, (payload, module_id) in expected.items():
        if payload.get("module_id") != module_id:
            blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")

    evidence_binding = _clean(evidence_payload.get("match_surface_binding_id"))
    identity_binding = _clean(identity_payload.get("match_surface_binding_id"))
    if not evidence_binding or evidence_binding != identity_binding:
        blocks.append("evidence_identity_match_surface_binding_mismatch")

    identity_by_atom, identity_blocks = _binding_index(identity_payload)
    episode_by_nucleus, episode_blocks = _episode_index(episode_payload)
    blocks.extend(identity_blocks)
    blocks.extend(episode_blocks)

    atoms = evidence_payload.get("evidence_atoms") or []
    if not isinstance(atoms, list):
        blocks.append("evidence_atoms_invalid")
        atoms = []
    if evidence_payload.get("evidence_atom_count") != len(atoms):
        blocks.append("evidence_atom_count_mismatch")

    root = Path(repo_root).resolve() if repo_root is not None else _repo_root()
    try:
        provider, registry = _provider_semantics(root)
    except (OSError, ValueError, ImportError) as exc:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "process_participation_candidates": [],
            "process_participation_candidate_count": 0,
            "hard_block_hits": sorted(set(blocks + [f"provider_semantic_authority_unavailable:{type(exc).__name__}"])),
            "review_hits": sorted(set(reviews)),
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    records: list[dict[str, Any]] = []
    if not blocks:
        for position, atom in enumerate(atoms):
            if not isinstance(atom, dict):
                blocks.append(f"evidence_atom_invalid:{position}")
                continue
            role = _clean(atom.get("semantic_role_candidate"))
            if role not in PROCESS_ROLES:
                continue
            if atom.get("atom_status") != "PASS":
                reviews.append(f"process_atom_review_required:{_clean(atom.get('evidence_atom_id')) or position}")
                continue
            atom_id = _clean(atom.get("evidence_atom_id"))
            identity = identity_by_atom.get(atom_id)
            if not identity:
                blocks.append(f"process_atom_identity_binding_missing:{atom_id}")
                continue
            decision_state = _clean(identity.get("decision_state"))
            source_role = _clean(atom.get("source_role"))
            if role == "PARTICIPATION_INTERVAL":
                if source_role != "PLAYER_SURFACE_CANDIDATE" or decision_state != "ACTOR_IDENTITY_CANDIDATE_BOUND":
                    reviews.append(f"participation_identity_not_actor_bound:{atom_id}")
                    continue
            elif decision_state not in BOUND_IDENTITY_STATES:
                reviews.append(f"process_context_identity_not_bound:{atom_id}")
                continue

            classified = provider.classify_label(
                _clean(atom.get("raw_label")),
                source_format="evidence_atom",
                source_role=source_role,
                registry=registry,
            )
            if classified.get("review_status") != "REVIEWED_CANDIDATE":
                reviews.append(f"process_semantics_not_reviewed:{atom_id}")
                continue
            if _clean(classified.get("rule_id")) != _clean(atom.get("semantic_rule_id")):
                blocks.append(f"process_semantic_rule_lineage_mismatch:{atom_id}")
                continue
            if _clean(classified.get("semantic_role_candidate")) != role:
                blocks.append(f"process_semantic_role_reclassification_mismatch:{atom_id}")
                continue
            process_family = _clean(classified.get("context_candidate"))
            if not process_family:
                reviews.append(f"process_family_missing:{atom_id}")
                continue

            nucleus_id = _clean(atom.get("row_nucleus_candidate_id"))
            episode_id = episode_by_nucleus.get(nucleus_id)
            if not episode_id:
                reviews.append(f"process_atom_episode_binding_missing:{atom_id}")

            reflection_state = _clean(atom.get("reflection_dependency_state"))
            records.append({
                "process_participation_candidate_id": "ppc_" + atom_id.removeprefix("ea_")[:24],
                "evidence_atom_id": atom_id,
                "row_nucleus_candidate_id": nucleus_id,
                "episode_candidate_id": episode_id,
                "match_surface_binding_id": evidence_binding,
                "source_role": source_role,
                "semantic_role": role,
                "process_family_candidate": process_family,
                "shot_present_annotation_candidate": _clean(classified.get("terminal_outcome_candidate")) == "SHOT_PRESENT_CANDIDATE",
                "team_identity_candidate_id": identity.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": identity.get("actor_identity_candidate_id") if role == "PARTICIPATION_INTERVAL" else None,
                "period_candidate": atom.get("period_candidate"),
                "start_candidate": atom.get("start_candidate"),
                "end_candidate": atom.get("end_candidate"),
                "provider_semantic_rule_id": classified.get("rule_id"),
                "reflection_dependency_state": reflection_state,
                "provenance_root": atom_id,
                "derivation_parents": [atom_id],
                "dependency_group": atom_id,
                "independence_group": None,
                "independent_support_vote_count": 0,
                "process_participation_is_action_truth": False,
                "process_annotation_is_tactical_plan_truth": False,
                "process_annotation_is_coach_intention_truth": False,
                "process_annotation_is_off_ball_role_truth": False,
                "episode_binding_is_possession_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    participation = [row for row in records if row["semantic_role"] == "PARTICIPATION_INTERVAL"]
    process_context = [row for row in records if row["semantic_role"] == "CONTEXT_INTERVAL"]
    family_counts = Counter(row["process_family_candidate"] for row in participation)
    shot_family_counts = Counter(
        row["process_family_candidate"] for row in participation if row["shot_present_annotation_candidate"]
    )
    actor_family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in participation:
        actor_id = _clean(row.get("actor_identity_candidate_id"))
        if actor_id:
            actor_family_counts[actor_id][row["process_family_candidate"]] += 1

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "match_surface_binding_id": evidence_binding or None,
        "process_participation_candidates": records,
        "process_participation_candidate_count": len(records),
        "player_participation_annotation_count": len(participation),
        "team_process_annotation_count": len(process_context),
        "player_participation_family_annotation_counts": dict(sorted(family_counts.items())),
        "player_shot_present_process_family_annotation_counts": dict(sorted(shot_family_counts.items())),
        "actor_process_family_annotation_counts": {
            actor: dict(sorted(counts.items())) for actor, counts in sorted(actor_family_counts.items())
        },
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "annotation_count_is_action_count": False,
        "annotation_count_is_independent_support_count": False,
        "reflection_adds_independent_vote": False,
        "process_participation_is_off_ball_role_truth": False,
        "process_family_is_tactical_plan_truth": False,
        "process_family_is_coach_intention_truth": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST EPISODE PROCESS PARTICIPATION PROJECTION V1",
        f"status={payload.get('status')}",
        f"player_participation_annotation_count={payload.get('player_participation_annotation_count', 0)}",
        f"team_process_annotation_count={payload.get('team_process_annotation_count', 0)}",
        f"player_participation_family_annotation_counts={json.dumps(payload.get('player_participation_family_annotation_counts') or {}, sort_keys=True)}",
        f"player_shot_present_process_family_annotation_counts={json.dumps(payload.get('player_shot_present_process_family_annotation_counts') or {}, sort_keys=True)}",
        f"review_hits={payload.get('review_hits')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA ANALYST AUDIT — PROCESS PARTICIPATION",
        "WHAT_VISIBLE: provider-reviewed process participation/context annotations are bound to match-local identity candidates and episode navigation candidates where available.",
        "SUPPORT: evidence atom + reviewed provider semantic rule + match-local identity binding + episode row-nucleus membership.",
        "COUNTEREVIDENCE: not generated from missing annotations; absence is not counterevidence.",
        "SAFE_MEANING: a player is visibly annotated as participating in a provider-defined process family; shot-present annotations may distinguish shot-producing process annotations.",
        "FORBIDDEN_INFERENCE: participation is not an action, off-ball role, spacing, team shape, tactical plan, coach intention, possession truth or causality.",
        "ANALYST_ACTION: compare recurring participant/process annotations with admitted episode consequences before writing a finding.",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]) + "\n"


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst(payload), encoding="utf-8")
    return paths
