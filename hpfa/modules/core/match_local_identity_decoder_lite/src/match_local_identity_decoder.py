from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_local_identity_decoder_lite_v1"
OUTPUT_JSON = "match_local_identity_decoder_lite_v1.json"
OUTPUT_TXT = "match_local_identity_decoder_lite_v1.txt"


def _raw(value: Any) -> str:
    return "" if value is None else str(value)


def _clean(value: Any) -> str:
    return " ".join(_raw(value).split()).strip()


def _norm(value: Any) -> str:
    text = _clean(value).casefold()
    tokenized = "".join(char if char.isalnum() else "_" for char in text)
    return "_".join(part for part in tokenized.split("_") if part)


def _stable_id(prefix: str, *parts: Any) -> str:
    seed = "|".join(_clean(part) for part in parts)
    return f"{prefix}_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _provider_actor_id(atom: dict[str, Any]) -> str:
    extra = atom.get("source_extra_fields")
    if not isinstance(extra, dict):
        return ""
    for key in ("player_id", "playerId", "actor_id", "actorId", "person_id", "personId"):
        value = _clean(extra.get(key))
        if value:
            return value
    return ""


def _provider_team_id(atom: dict[str, Any]) -> str:
    extra = atom.get("source_extra_fields")
    if not isinstance(extra, dict):
        return ""
    for key in ("team_id", "teamId", "squad_id", "squadId"):
        value = _clean(extra.get(key))
        if value:
            return value
    return ""


def build_match_local_identity_decoder(evidence_payload: dict[str, Any]) -> dict[str, Any]:
    atoms = evidence_payload.get("evidence_atoms") or []
    match_binding_id = _clean(
        evidence_payload.get("match_binding_id")
        or next((atom.get("match_binding_id") for atom in atoms if isinstance(atom, dict)), "")
    )

    team_aliases: dict[str, set[str]] = defaultdict(set)
    actor_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    team_provider_ids: dict[str, set[str]] = defaultdict(set)
    actor_provider_ids: dict[tuple[str, str], set[str]] = defaultdict(set)

    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        team_raw = _clean(atom.get("team_raw"))
        player_raw = _clean(atom.get("player_raw"))
        team_key = _norm(team_raw)
        player_key = _norm(player_raw)
        if team_key:
            team_aliases[team_key].add(team_raw)
            provider_team_id = _provider_team_id(atom)
            if provider_team_id:
                team_provider_ids[team_key].add(provider_team_id)
        if team_key and player_key:
            actor_aliases[(team_key, player_key)].add(player_raw)
            provider_actor_id = _provider_actor_id(atom)
            if provider_actor_id:
                actor_provider_ids[(team_key, player_key)].add(provider_actor_id)

    team_candidates = []
    team_decisions: dict[str, dict[str, Any]] = {}
    for team_key in sorted(team_aliases):
        aliases = sorted(team_aliases[team_key])
        provider_ids = sorted(team_provider_ids.get(team_key, set()))
        conflict = len(provider_ids) > 1
        state = "CROSS_TEAM_CONFLICT_REVIEW_REQUIRED" if conflict else "TEAM_IDENTITY_BOUND"
        candidate = {
            "team_identity_id": _stable_id("team", match_binding_id, team_key),
            "match_binding_id": match_binding_id,
            "normalized_team_key": team_key,
            "team_aliases_raw": aliases,
            "provider_team_ids": provider_ids,
            "decision_state": state,
        }
        team_candidates.append(candidate)
        team_decisions[team_key] = candidate

    actor_candidates = []
    actor_decisions: dict[tuple[str, str], dict[str, Any]] = {}
    player_to_teams: dict[str, set[str]] = defaultdict(set)
    for team_key, player_key in actor_aliases:
        player_to_teams[player_key].add(team_key)

    for key in sorted(actor_aliases):
        team_key, player_key = key
        aliases = sorted(actor_aliases[key])
        provider_ids = sorted(actor_provider_ids.get(key, set()))
        cross_team = len(player_to_teams[player_key]) > 1
        provider_conflict = len(provider_ids) > 1
        if provider_conflict:
            state = "AMBIGUOUS_ALIAS_REVIEW_REQUIRED"
        elif cross_team and not provider_ids:
            state = "CROSS_TEAM_CONFLICT_REVIEW_REQUIRED"
        else:
            state = "ACTOR_IDENTITY_BOUND"
        candidate = {
            "actor_identity_id": _stable_id("actor", match_binding_id, team_key, player_key),
            "match_binding_id": match_binding_id,
            "team_identity_id": team_decisions[team_key]["team_identity_id"],
            "normalized_team_key": team_key,
            "normalized_actor_key": player_key,
            "actor_aliases_raw": aliases,
            "provider_actor_ids": provider_ids,
            "decision_state": state,
        }
        actor_candidates.append(candidate)
        actor_decisions[key] = candidate

    identity_bindings = []
    unresolved_atom_count = 0
    identity_bound_atom_count = 0
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        atom_id = atom.get("evidence_atom_id")
        team_key = _norm(atom.get("team_raw"))
        player_key = _norm(atom.get("player_raw"))
        team_candidate = team_decisions.get(team_key)
        actor_candidate = actor_decisions.get((team_key, player_key))

        if not team_key:
            state = "TEAM_IDENTITY_MISSING"
        elif team_candidate and team_candidate["decision_state"] != "TEAM_IDENTITY_BOUND":
            state = team_candidate["decision_state"]
        elif not player_key:
            state = "TEAM_IDENTITY_BOUND"
        elif actor_candidate and actor_candidate["decision_state"] == "ACTOR_IDENTITY_BOUND":
            state = "ACTOR_IDENTITY_BOUND"
        elif actor_candidate:
            state = actor_candidate["decision_state"]
        else:
            state = "ROSTER_BINDING_MISSING"

        bound = state in {"TEAM_IDENTITY_BOUND", "ACTOR_IDENTITY_BOUND"}
        identity_bound_atom_count += int(bound)
        unresolved_atom_count += int(not bound)
        identity_bindings.append({
            "evidence_atom_id": atom_id,
            "match_binding_id": atom.get("match_binding_id") or match_binding_id,
            "team_identity_id": team_candidate.get("team_identity_id") if team_candidate else None,
            "actor_identity_id": actor_candidate.get("actor_identity_id") if actor_candidate else None,
            "decision_state": state,
            "event_instance_allowed": False,
            "claim_ceiling": "MATCH_LOCAL_IDENTITY_ONLY",
        })

    review_required = any(
        binding["decision_state"] not in {"TEAM_IDENTITY_BOUND", "ACTOR_IDENTITY_BOUND"}
        for binding in identity_bindings
    )
    return {
        "module_id": MODULE_ID,
        "decision_state": "REVIEW_REQUIRED_IDENTITY_GAPS" if review_required else "PASS_MATCH_LOCAL_IDENTITY",
        "match_binding_id": match_binding_id,
        "team_identity_candidates": team_candidates,
        "actor_identity_candidates": actor_candidates,
        "identity_bindings": identity_bindings,
        "evidence_atom_count": len([atom for atom in atoms if isinstance(atom, dict)]),
        "identity_bound_atom_count": identity_bound_atom_count,
        "unresolved_atom_count": unresolved_atom_count,
        "semantic_role_counts": {},
        "action_bundle_candidate_count": 0,
        "event_instance_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(evidence_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(out_dir)
    if output_dir.name != "HPFA" or "HPFA" in output_dir.parts[:-1]:
        raise ValueError("nested_phone_output_directory_rejected")
    payload = json.loads(Path(evidence_json).read_text(encoding="utf-8"))
    result = build_match_local_identity_decoder(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / OUTPUT_TXT).write_text(
        "\n".join([
            "HPFA MATCH-LOCAL IDENTITY DECODER LITE V1",
            f"decision_state={result['decision_state']}",
            f"evidence_atom_count={result['evidence_atom_count']}",
            f"identity_bound_atom_count={result['identity_bound_atom_count']}",
            f"unresolved_atom_count={result['unresolved_atom_count']}",
            "event_instance_count=0",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]) + "\n",
        encoding="utf-8",
    )
    return result
