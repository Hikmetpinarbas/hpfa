from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_local_actor_team_identity_decoder_lite_v1"
OUTPUT_JSON = "match_local_actor_team_identity_decoder_lite_v1.json"
OUTPUT_TXT = "match_local_actor_team_identity_decoder_lite_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _stable_id(prefix: str, *parts: str) -> str:
    seed = "|".join(parts)
    return f"{prefix}_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def _source_ref(atom: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_atom_id": atom.get("evidence_atom_id"),
        "source_file": atom.get("source_file"),
        "source_format": atom.get("source_format"),
        "source_role": atom.get("source_role"),
        "source_row_index": atom.get("source_row_index"),
    }


def build_identity_decoder(evidence_payload: dict[str, Any]) -> dict[str, Any]:
    atoms = [item for item in (evidence_payload.get("evidence_atoms") or []) if isinstance(item, dict)]
    match_binding_id = _clean(evidence_payload.get("match_binding_id")) or "active_single_match_current"

    team_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actor_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    actor_team_memberships: dict[str, set[str]] = defaultdict(set)
    unresolved: list[dict[str, Any]] = []
    atom_bindings: list[dict[str, Any]] = []

    for atom in atoms:
        atom_id = _clean(atom.get("evidence_atom_id"))
        team_raw = _clean(atom.get("team_raw"))
        player_raw = _clean(atom.get("player_raw"))
        team_key = _key(team_raw)
        actor_key = _key(player_raw)

        if team_key:
            team_groups[team_key].append(atom)
        if actor_key and team_key:
            actor_groups[(team_key, actor_key)].append(atom)
            actor_team_memberships[actor_key].add(team_key)
        elif actor_key and not team_key:
            unresolved.append({
                "evidence_atom_id": atom_id,
                "reason": "actor_present_team_missing",
                "player_raw": player_raw,
                "source": _source_ref(atom),
            })
        elif atom.get("atom_class") == "EXPLANATORY_EVIDENCE_ATOM" and not team_key:
            unresolved.append({
                "evidence_atom_id": atom_id,
                "reason": "explanatory_atom_identity_surface_missing",
                "source": _source_ref(atom),
            })

    ambiguous_actor_keys = {key for key, teams in actor_team_memberships.items() if len(teams) > 1}

    team_candidates: list[dict[str, Any]] = []
    team_id_by_key: dict[str, str] = {}
    for team_key, group in sorted(team_groups.items()):
        raw_names = sorted({_clean(item.get("team_raw")) for item in group if _clean(item.get("team_raw"))})
        source_formats = sorted({_clean(item.get("source_format")).lower() for item in group if _clean(item.get("source_format"))})
        team_id = _stable_id("team", match_binding_id, team_key)
        team_id_by_key[team_key] = team_id
        team_candidates.append({
            "team_identity_candidate_id": team_id,
            "match_binding_id": match_binding_id,
            "normalized_team_key": team_key,
            "raw_name_variants": raw_names,
            "supporting_atom_count": len(group),
            "source_formats": source_formats,
            "binding_method": "MATCH_LOCAL_NORMALIZED_EXACT_SURFACE",
            "validation_status": "PROVISIONAL_MATCH_LOCAL_IDENTITY",
            "global_identity_claim_allowed": False,
            "source_refs": [_source_ref(item) for item in group[:100]],
        })

    actor_candidates: list[dict[str, Any]] = []
    actor_id_by_pair: dict[tuple[str, str], str] = {}
    for (team_key, actor_key), group in sorted(actor_groups.items()):
        raw_names = sorted({_clean(item.get("player_raw")) for item in group if _clean(item.get("player_raw"))})
        source_formats = sorted({_clean(item.get("source_format")).lower() for item in group if _clean(item.get("source_format"))})
        ambiguous = actor_key in ambiguous_actor_keys
        actor_id = _stable_id("actor", match_binding_id, team_key, actor_key)
        actor_id_by_pair[(team_key, actor_key)] = actor_id
        actor_candidates.append({
            "actor_identity_candidate_id": actor_id,
            "team_identity_candidate_id": team_id_by_key.get(team_key),
            "match_binding_id": match_binding_id,
            "normalized_actor_key": actor_key,
            "normalized_team_key": team_key,
            "raw_name_variants": raw_names,
            "supporting_atom_count": len(group),
            "source_formats": source_formats,
            "cross_surface_support": len(source_formats) > 1,
            "binding_method": "MATCH_LOCAL_TEAM_SCOPED_NORMALIZED_EXACT_SURFACE",
            "validation_status": "REVIEW_REQUIRED_CROSS_TEAM_NAME_COLLISION" if ambiguous else "PROVISIONAL_MATCH_LOCAL_IDENTITY",
            "global_identity_claim_allowed": False,
            "source_refs": [_source_ref(item) for item in group[:100]],
        })

    identity_bound_atom_count = 0
    for atom in atoms:
        atom_id = _clean(atom.get("evidence_atom_id"))
        team_key = _key(atom.get("team_raw"))
        actor_key = _key(atom.get("player_raw"))
        team_id = team_id_by_key.get(team_key)
        actor_id = actor_id_by_pair.get((team_key, actor_key)) if actor_key else None
        if actor_id or team_id:
            identity_bound_atom_count += 1
        atom_bindings.append({
            "evidence_atom_id": atom_id,
            "team_identity_candidate_id": team_id,
            "actor_identity_candidate_id": actor_id,
            "binding_status": (
                "PROVISIONAL_ACTOR_TEAM_BOUND" if actor_id and actor_key not in ambiguous_actor_keys
                else "REVIEW_REQUIRED_ACTOR_TEAM_COLLISION" if actor_id
                else "PROVISIONAL_TEAM_ONLY_BOUND" if team_id
                else "UNRESOLVED_IDENTITY"
            ),
        })

    status_counts = Counter(item["binding_status"] for item in atom_bindings)
    decision_state = "PASS_MATCH_LOCAL_IDENTITY_CANDIDATES"
    if not atoms:
        decision_state = "FAIL_CLOSED_NO_EVIDENCE_ATOMS"
    elif ambiguous_actor_keys or unresolved:
        decision_state = "REVIEW_REQUIRED_MATCH_LOCAL_IDENTITY_GAPS"

    return {
        "module_id": MODULE_ID,
        "decision_state": decision_state,
        "match_binding_id": match_binding_id,
        "team_identity_candidates": team_candidates,
        "actor_identity_candidates": actor_candidates,
        "atom_identity_bindings": atom_bindings,
        "team_identity_candidate_count": len(team_candidates),
        "actor_identity_candidate_count": len(actor_candidates),
        "identity_bound_atom_count": identity_bound_atom_count,
        "identity_unresolved_atom_count": status_counts.get("UNRESOLVED_IDENTITY", 0),
        "binding_status_counts": dict(sorted(status_counts.items())),
        "cross_team_actor_name_collision_count": len(ambiguous_actor_keys),
        "cross_team_actor_name_collision_keys": sorted(ambiguous_actor_keys),
        "unresolved_identity_surfaces": unresolved[:500],
        "identity_scope": "MATCH_LOCAL_ONLY",
        "identity_truth_admitted": False,
        "global_roster_identity_admitted": False,
        "base_event_admission_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(evidence_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(out_dir)
    if output_dir.name != "HPFA" or "HPFA" in output_dir.parts[:-1]:
        raise ValueError("nested_phone_output_directory_rejected")
    payload = json.loads(Path(evidence_json).read_text(encoding="utf-8"))
    result = build_identity_decoder(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "HPFA MATCH-LOCAL ACTOR AND TEAM IDENTITY DECODER LITE V1",
        f"decision_state={result['decision_state']}",
        f"team_identity_candidate_count={result['team_identity_candidate_count']}",
        f"actor_identity_candidate_count={result['actor_identity_candidate_count']}",
        f"identity_bound_atom_count={result['identity_bound_atom_count']}",
        f"identity_unresolved_atom_count={result['identity_unresolved_atom_count']}",
        f"cross_team_actor_name_collision_count={result['cross_team_actor_name_collision_count']}",
        "identity_scope=MATCH_LOCAL_ONLY",
        "identity_truth_admitted=false",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    (output_dir / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
